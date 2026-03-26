import json

import anthropic

from src.conversation.turn import ConversationSession
from src.evaluation.schema import EvaluationResult


async def analyze_results(
    client: anthropic.AsyncAnthropic,
    model: str,
    sessions: list[ConversationSession],
    evaluations: list[EvaluationResult],
) -> dict:
    """대화 결과와 평가를 분석하여 패턴을 발견합니다."""

    # 상위/하위 대화 선별
    sorted_evals = sorted(evaluations, key=lambda e: e.weighted_score, reverse=True)
    top_3 = sorted_evals[:3]
    bottom_3 = sorted_evals[-3:]

    session_map = {s.session_id: s for s in sessions}

    top_transcripts = ""
    for ev in top_3:
        s = session_map.get(ev.session_id)
        if s:
            top_transcripts += f"\n### 점수: {ev.weighted_score} (페르소나: {s.persona_id})\n{s.transcript}\n"

    bottom_transcripts = ""
    for ev in bottom_3:
        s = session_map.get(ev.session_id)
        if s:
            bottom_transcripts += f"\n### 점수: {ev.weighted_score} (페르소나: {s.persona_id})\n{s.transcript}\n"

    prompt = f"""당신은 온라인 쇼핑몰 세일즈 대화 분석 전문가입니다.
아래 대화 결과를 분석하고 패턴을 발견하세요.

## 성과가 좋은 대화 (상위 3개)
{top_transcripts}

## 성과가 낮은 대화 (하위 3개)
{bottom_transcripts}

## 전체 통계
- 총 대화 수: {len(evaluations)}
- 평균 종합 점수: {sum(e.weighted_score for e in evaluations) / len(evaluations):.2f}
- 최고 점수: {sorted_evals[0].weighted_score}
- 최저 점수: {sorted_evals[-1].weighted_score}

## 분석 요청
다음을 JSON 형식으로 응답하세요:
{{
  "success_patterns": ["성공 대화에서 발견된 패턴들"],
  "failure_patterns": ["실패 대화에서 발견된 패턴들"],
  "persona_insights": ["특정 페르소나 유형에 대한 인사이트"],
  "tactical_observations": ["전술적 관찰사항"],
  "improvement_suggestions": ["개선 제안"]
}}
"""

    response = await client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
