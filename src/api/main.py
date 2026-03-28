"""FastAPI 서버 — EV 충전 쿠폰 넛지 시뮬레이터"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import select

from config.settings import get_settings
from src.csms.revenue import calculate_baseline_revenue, calculate_baseline_per_type
from src.llm import create_client
from src.personas.loader import generate_personas_from_db
from src.personas.schema import EVPersona
from src.ralph.loop import RALPHLoop
from src.storage.database import init_db, get_session
from src.storage.models import CouponLoopRun, CouponIterationResult


# === State ===
loop_state = {
    "running": False,
    "results": [],
    "current_iteration": 0,
    "total_iterations": 0,
    "events": [],
    "personas": [],
    "baseline": {},
    "run_id": 0,
    "db_run_id": None,
}

# DB 엔진
db_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_engine
    db_engine = init_db()
    yield


app = FastAPI(title="EV Charging Coupon Nudge API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# === API Models ===
class LoopRequest(BaseModel):
    n_iterations: int = 3
    personas_count: int = 2000


# === Endpoints ===

@app.get("/api/baseline")
async def get_baseline():
    """DB 기준선 매출 + 25유형 분포"""
    try:
        revenue = calculate_baseline_revenue()
        per_type = calculate_baseline_per_type()
        return {
            "active_users": revenue["active_users"],
            "total_revenue": float(revenue["total_revenue"]),
            "monthly_revenue": float(revenue["monthly_revenue"]),
            "per_type": per_type,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/status")
async def get_status():
    return {
        "running": loop_state["running"],
        "current_iteration": loop_state["current_iteration"],
        "total_iterations": loop_state["total_iterations"],
        "results": loop_state["results"],
    }


@app.get("/api/loop/history")
async def get_loop_history():
    """DB에서 이전 루프 실행 히스토리를 조회합니다."""
    session = get_session(db_engine)
    try:
        runs = list(session.exec(
            select(CouponLoopRun).order_by(CouponLoopRun.id)
        ).all())
        result = []
        for run in runs:
            iterations = list(session.exec(
                select(CouponIterationResult)
                .where(CouponIterationResult.run_id == run.id)
                .order_by(CouponIterationResult.iteration)
            ).all())
            result.append({
                "run_id": run.id,
                "n_iterations": run.n_iterations,
                "personas_count": run.personas_count,
                "baseline_revenue": run.baseline_revenue,
                "started_at": run.started_at.isoformat(),
                "iterations": [
                    {
                        "iteration": it.iteration,
                        "strategy_id": it.strategy_id,
                        "strategy_rationale": it.strategy_rationale,
                        "conditions": json.loads(it.conditions_json) if it.conditions_json else [],
                        "coupon_users": it.coupon_users,
                        "coupon_usage_rate": it.coupon_usage_rate,
                        "gross_revenue": it.gross_revenue,
                        "discount_cost": it.discount_cost,
                        "net_revenue": it.net_revenue,
                        "baseline_revenue": it.baseline_revenue,
                        "per_type_results": json.loads(it.per_type_results_json) if it.per_type_results_json else [],
                        "learnings": json.loads(it.learnings_json) if it.learnings_json else [],
                    }
                    for it in iterations
                ],
            })
        return result
    finally:
        session.close()


@app.post("/api/loop/start")
async def start_loop(req: LoopRequest):
    if loop_state["running"]:
        return {"error": "Loop already running"}

    # DB에 새 루프 레코드 생성
    session = get_session(db_engine)
    try:
        run = CouponLoopRun(
            n_iterations=req.n_iterations,
            personas_count=req.personas_count,
            baseline_revenue=0,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        db_run_id = run.id
    finally:
        session.close()

    # 상태 리셋
    loop_state["run_id"] = db_run_id
    loop_state["db_run_id"] = db_run_id
    loop_state["running"] = True
    loop_state["results"] = []
    loop_state["current_iteration"] = 0
    loop_state["total_iterations"] = req.n_iterations
    loop_state["events"] = []

    asyncio.create_task(_run_loop(req.n_iterations, req.personas_count))

    return {"status": "started", "run_id": db_run_id, "iterations": req.n_iterations, "personas": req.personas_count}


@app.get("/api/loop/stream")
async def stream_events():
    """SSE 스트림으로 루프 진행 상황을 실시간 전달합니다."""

    async def event_generator():
        last_idx = 0
        while True:
            events = loop_state["events"]
            while last_idx < len(events):
                yield f"data: {json.dumps(events[last_idx], ensure_ascii=False)}\n\n"
                last_idx += 1

            if not loop_state["running"] and last_idx >= len(events):
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/loop/stop")
async def stop_loop():
    loop_state["running"] = False
    return {"status": "stopped"}


# === Background Loop Runner ===

async def _run_loop(n_iterations: int, personas_count: int):
    try:
        settings = get_settings()
        client = create_client(settings.openrouter_api_key)

        # 페르소나 생성
        _push_event({"type": "status", "message": "DB에서 페르소나 생성 중..."})
        personas = generate_personas_from_db(personas_count)
        loop_state["personas"] = personas
        _push_event({
            "type": "personas_loaded",
            "count": len(personas),
        })

        # 기준선 매출 (페르소나 기반)
        baseline_monthly = sum(
            p.avg_charge_amount * p.avg_monthly_sessions for p in personas
        )
        loop_state["baseline_revenue"] = baseline_monthly
        _push_event({
            "type": "baseline",
            "monthly_revenue": baseline_monthly,
            "persona_count": len(personas),
        })

        # DB에 baseline 업데이트
        session = get_session(db_engine)
        try:
            run = session.get(CouponLoopRun, loop_state["db_run_id"])
            if run:
                run.baseline_revenue = baseline_monthly
                session.add(run)
                session.commit()
        finally:
            session.close()

        ralph = RALPHLoop(
            client=client,
            model_cheap=settings.model_cheap,
            model_expensive=settings.model_expensive,
            baseline_revenue=baseline_monthly,
            concurrency=settings.concurrent_calls,
        )

        # 콜백
        async def on_iter_start(iteration, total):
            loop_state["current_iteration"] = iteration
            _push_event({"type": "iteration_start", "iteration": iteration, "total": total})

        async def on_iter_end(result, strategy, analysis=None):
            result_data = {
                "iteration": result.iteration,
                "strategy_id": strategy.id,
                "strategy_rationale": strategy.rationale,
                "conditions": [
                    {"type_key": c.type_key, "discount_rate": c.discount_rate, "validity_days": c.validity_days}
                    for c in strategy.conditions
                ],
                "coupon_users": result.coupon_users,
                "coupon_usage_rate": result.coupon_usage_rate,
                "gross_revenue": result.gross_revenue,
                "discount_cost": result.discount_cost,
                "net_revenue": result.net_revenue,
                "baseline_revenue": result.baseline_revenue,
                "total_with_coupon": result.baseline_revenue + result.net_revenue,
                "per_type_results": [
                    {
                        "type_key": tr.type_key,
                        "total": tr.total,
                        "coupon_users": tr.coupon_users,
                        "usage_rate": tr.usage_rate,
                        "discount_rate": tr.discount_rate,
                        "validity_days": tr.validity_days,
                        "net_revenue": tr.net_revenue,
                    }
                    for tr in result.per_type_results
                ],
                "learnings": result.key_insights,
                "analysis": analysis or {},
            }
            loop_state["results"].append(result_data)
            _push_event({"type": "iteration_end", **result_data})

            # DB에 이터레이션 결과 저장
            session = get_session(db_engine)
            try:
                record = CouponIterationResult(
                    run_id=loop_state["db_run_id"],
                    iteration=result.iteration,
                    strategy_id=strategy.id,
                    strategy_rationale=strategy.rationale,
                    conditions_json=json.dumps(result_data["conditions"], ensure_ascii=False),
                    coupon_users=result.coupon_users,
                    coupon_usage_rate=result.coupon_usage_rate,
                    gross_revenue=result.gross_revenue,
                    discount_cost=result.discount_cost,
                    net_revenue=result.net_revenue,
                    baseline_revenue=result.baseline_revenue,
                    per_type_results_json=json.dumps(result_data["per_type_results"], ensure_ascii=False),
                    learnings_json=json.dumps(result.key_insights, ensure_ascii=False),
                    analysis_json=json.dumps(analysis or {}, ensure_ascii=False),
                )
                session.add(record)
                session.commit()
            finally:
                session.close()

        ralph.on_iteration_start = on_iter_start
        ralph.on_iteration_end = on_iter_end

        await ralph.run(personas=personas, n_iterations=n_iterations)

    except Exception as e:
        _push_event({"type": "error", "message": str(e)})
    finally:
        loop_state["running"] = False
        _push_event({"type": "done"})
        # DB에 종료 시간 기록
        if loop_state["db_run_id"]:
            session = get_session(db_engine)
            try:
                run = session.get(CouponLoopRun, loop_state["db_run_id"])
                if run:
                    run.ended_at = datetime.now()
                    session.add(run)
                    session.commit()
            finally:
                session.close()


def _push_event(event: dict):
    event["run_id"] = loop_state["run_id"]
    loop_state["events"].append(event)


# === Frontend serving ===
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")
