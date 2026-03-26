"""FastAPI 서버 — RALPH Loop 실행 및 결과 조회 API"""

import asyncio
import json
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config.settings import get_settings
from src.llm import create_client
from src.personas.schema import (
    Generation, InitialMood, InterestCategory, Persona,
    PriceSensitivity, PurchaseTendency, ReactionPattern,
)
from src.agents.rule_customer import RuleCustomerAgent
from src.agents.sales_agent import SalesAgent
from src.conversation.engine import ConversationEngine
from src.conversation.rules import check_termination
from src.conversation.turn import Turn
from src.evaluation.evaluator import Evaluator
from src.ralph.loop import RALPHLoop


# === State ===
loop_state = {
    "running": False,
    "results": [],
    "current_iteration": 0,
    "total_iterations": 0,
    "events": [],  # SSE events queue
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Nudge API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Persona mapping (frontend -> backend) ===
GEN_MAP = {
    "10대": Generation.TEEN, "20대": Generation.TWENTIES,
    "30대": Generation.THIRTIES, "40대": Generation.FORTIES,
    "50대": Generation.FIFTIES, "60대+": Generation.SIXTIES_PLUS,
}
CAT_MAP = {
    "패션": InterestCategory.FASHION, "전자기기": InterestCategory.ELECTRONICS,
    "뷰티": InterestCategory.FASHION, "식품": InterestCategory.FOOD,
    "건강": InterestCategory.HEALTH, "리빙": InterestCategory.HOME,
    "스포츠": InterestCategory.HOBBY, "도서": InterestCategory.HOBBY,
    "키즈": InterestCategory.HOME, "반려동물": InterestCategory.HOME,
}
TENDENCY_MAP = {
    "충동구매": PurchaseTendency.IMPULSE, "신중구매": PurchaseTendency.DELIBERATE,
    "브랜드충성": PurchaseTendency.BRAND_LOYAL, "할인추구": PurchaseTendency.BARGAIN_HUNTER,
    "필요기반": PurchaseTendency.NEEDS_BASED, "트렌드추구": PurchaseTendency.IMPULSE,
}
SENSITIVITY_MAP = {
    "높음": PriceSensitivity.HIGH, "중간": PriceSensitivity.MEDIUM, "낮음": PriceSensitivity.LOW,
}
REACTION_MAP = {
    "호기심": ReactionPattern.CURIOUS, "호의적": ReactionPattern.FRIENDLY,
    "회의적": ReactionPattern.SKEPTICAL, "급한성격": ReactionPattern.IMPATIENT,
    "방어적": ReactionPattern.DEFENSIVE,
}
MOOD_MAP = {
    "긍정": InitialMood.POSITIVE, "중립": InitialMood.NEUTRAL, "부정": InitialMood.NEGATIVE,
}


def frontend_persona_to_backend(p: dict) -> Persona:
    """프론트엔드 페르소나 dict를 백엔드 Persona 모델로 변환합니다."""
    return Persona(
        id=p["id"],
        name=p["name"],
        generation=GEN_MAP.get(p["gen"], Generation.THIRTIES),
        interest_category=CAT_MAP.get(p["cat"], InterestCategory.ELECTRONICS),
        purchase_tendency=TENDENCY_MAP.get(p["tendency"], PurchaseTendency.DELIBERATE),
        price_sensitivity=SENSITIVITY_MAP.get(p["sensitivity"], PriceSensitivity.MEDIUM),
        reaction_pattern=REACTION_MAP.get(p["reaction"], ReactionPattern.FRIENDLY),
        initial_mood=MOOD_MAP.get(p["mood"], InitialMood.NEUTRAL),
        background=p.get("desc", ""),
        speech_style="자연스러운 한국어",
    )


# === API Models ===
class SimRequest(BaseModel):
    persona: dict


class LoopRequest(BaseModel):
    personas: list[dict]
    n_iterations: int = 5


class LoopStatus(BaseModel):
    running: bool
    current_iteration: int
    total_iterations: int
    results: list[dict]


# === Endpoints ===

@app.get("/api/status")
async def get_status():
    return {
        "running": loop_state["running"],
        "current_iteration": loop_state["current_iteration"],
        "total_iterations": loop_state["total_iterations"],
        "results": loop_state["results"],
    }


@app.post("/api/sim/start")
async def start_sim(req: SimRequest):
    """단일 대화 시뮬레이션 — SSE로 턴마다 실시간 스트리밍"""
    settings = get_settings()
    client = create_client(settings.openrouter_api_key)
    persona = frontend_persona_to_backend(req.persona)

    async def event_generator():
        sales = SalesAgent(
            client=client,
            model=settings.model_cheap,
            product_name="VitaForest 올인원 데일리 멀티비타민",
            product_description="22종 비타민+미네랄, 프로바이오틱스, 루테인, 오메가3, GMP 인증, 하루 1포, 4.7점 리뷰",
            product_price="₩49,900 (정가 ₩65,000, 30일분)",
        )
        customer = RuleCustomerAgent(persona=persona)
        turns: list[Turn] = []
        termination_reason = "max_turns"
        max_turns = settings.max_turns

        for turn_num in range(max_turns):
            if turn_num % 2 == 0:
                speaker = "sales"
                response = await sales.respond(turns)
            else:
                speaker = "customer"
                response = await customer.respond(turns)

            turn = Turn(speaker=speaker, content=response, turn_number=turn_num + 1)
            turns.append(turn)

            yield f"data: {json.dumps({'type': 'turn', 'speaker': speaker, 'content': response, 'turn_number': turn_num + 1}, ensure_ascii=False)}\n\n"

            if speaker == "customer":
                term = check_termination(response)
                if term is not None:
                    termination_reason = term
                    break

        # 대화 끝 — 평가 시작
        yield f"data: {json.dumps({'type': 'eval_start'}, ensure_ascii=False)}\n\n"

        try:
            from src.conversation.turn import ConversationSession
            import uuid
            session = ConversationSession(
                session_id=str(uuid.uuid4()),
                persona_id=persona.id,
                product_name="SoundForest SF-Pro Max",
                turns=turns,
                termination_reason=termination_reason,
            )
            evaluator = Evaluator(client=client, model=settings.model_expensive)
            result = await evaluator.evaluate(session)
            yield f"data: {json.dumps({'type': 'eval_result', 'termination_reason': termination_reason, 'interest_level': {'score': result.interest_level.score, 'reasoning': result.interest_level.reasoning}, 'conversation_continuation': {'score': result.conversation_continuation.score, 'reasoning': result.conversation_continuation.reasoning}, 'emotional_change': {'score': result.emotional_change.score, 'reasoning': result.emotional_change.reasoning}, 'purchase_intent': {'score': result.purchase_intent.score, 'reasoning': result.purchase_intent.reasoning}, 'final_outcome': {'score': result.final_outcome.score, 'reasoning': result.final_outcome.reasoning}, 'weighted_score': result.weighted_score, 'overall_summary': result.overall_summary}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'eval_error', 'message': str(e), 'termination_reason': termination_reason}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/loop/start")
async def start_loop(req: LoopRequest):
    if loop_state["running"]:
        return {"error": "Loop already running"}

    # Convert personas
    backend_personas = [frontend_persona_to_backend(p) for p in req.personas]

    # Reset state
    loop_state["running"] = True
    loop_state["results"] = []
    loop_state["current_iteration"] = 0
    loop_state["total_iterations"] = req.n_iterations
    loop_state["events"] = []

    # Run in background
    asyncio.create_task(_run_loop(backend_personas, req.n_iterations))

    return {"status": "started", "total_personas": len(backend_personas), "iterations": req.n_iterations}


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

async def _run_loop(personas: list[Persona], n_iterations: int):
    try:
        settings = get_settings()
        client = create_client(settings.openrouter_api_key)

        ralph = RALPHLoop(
            client=client,
            model_cheap=settings.model_cheap,
            model_expensive=settings.model_expensive,
            product_name="VitaForest 올인원 데일리 멀티비타민",
            product_description="22종 비타민+미네랄, 프로바이오틱스, 루테인, 오메가3, GMP 인증, 하루 1포, 4.7점 리뷰",
            product_price="₩49,900 (정가 ₩65,000, 30일분)",
            max_turns=settings.max_turns,
            concurrency=settings.concurrent_conversations,
        )

        # 콜백 설정
        async def on_iter_start(iteration, total):
            loop_state["current_iteration"] = iteration
            _push_event({"type": "iteration_start", "iteration": iteration, "total": total})

        async def on_iter_end(result, strategy, analysis=None):
            result_data = {
                "iteration": result.iteration,
                "strategy_name": strategy.name,
                "strategy_approach": strategy.approach,
                "strategy_opening": strategy.opening_style,
                "strategy_tactics": strategy.persuasion_tactics,
                "strategy_objection": strategy.objection_handling,
                "strategy_targets": strategy.target_personas,
                "avg_score": result.avg_weighted_score,
                "purchase_count": result.purchase_count,
                "wishlist_count": result.wishlist_count,
                "exit_count": result.exit_count,
                "purchase_rate": result.purchase_rate,
                "total_revenue": result.total_revenue,
                "conversation_count": result.conversation_count,
                "learnings": result.key_insights,
                "analysis": analysis or {},
            }
            loop_state["results"].append(result_data)
            _push_event({"type": "iteration_end", **result_data})

        ralph.on_iteration_start = on_iter_start
        ralph.on_iteration_end = on_iter_end

        await ralph.run(
            personas=personas,
            n_iterations=n_iterations,
            personas_per_iteration=len(personas),
        )

    except Exception as e:
        _push_event({"type": "error", "message": str(e)})
    finally:
        loop_state["running"] = False
        _push_event({"type": "done"})


def _push_event(event: dict):
    loop_state["events"].append(event)


# === Frontend serving ===
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")
