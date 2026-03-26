"""5가지 평가 차원의 정의 및 평가 기준"""

DIMENSION_RUBRICS = {
    "interest_level": {
        "name": "관심도",
        "description": "고객이 제품에 관심을 보인 정도",
        "rubric": """
1-2: 고객이 전혀 관심을 보이지 않음. 제품 관련 질문 없음.
3-4: 최소한의 관심. 형식적 반응만 있음.
5-6: 보통 수준의 관심. 일부 질문을 하거나 정보에 반응함.
7-8: 높은 관심. 적극적으로 질문하고 제품 정보를 탐색함.
9-10: 매우 높은 관심. 구체적 사용 시나리오를 상상하거나 비교 질문을 함.
""",
    },
    "conversation_continuation": {
        "name": "대화 지속도",
        "description": "고객이 대화에 참여하고 지속한 정도",
        "rubric": """
1-2: 1-2턴 내 대화 종료 시도. 단답 위주.
3-4: 짧은 대화. 대부분 수동적 응답.
5-6: 적당한 대화 길이. 능동적 참여 일부.
7-8: 긴 대화. 고객이 주도적으로 질문하거나 의견 표현.
9-10: 매우 활발한 대화. 고객이 적극적으로 참여하고 새로운 토픽도 제시.
""",
    },
    "emotional_change": {
        "name": "감정 변화",
        "description": "대화 중 고객의 감정이 긍정적으로 변화한 정도",
        "rubric": """
1-2: 감정이 악화됨. 짜증, 불쾌함 표현.
3-4: 변화 없음 또는 약간 부정적.
5-6: 중립 유지 또는 미세한 긍정 변화.
7-8: 명확한 긍정 변화. 웃음, 호감, 공감 표현.
9-10: 큰 감정 전환. 부정에서 긍정으로, 또는 매우 즐거운 경험.
""",
    },
    "purchase_intent": {
        "name": "구매 의향",
        "description": "고객이 구매 의향을 표현한 정도",
        "rubric": """
1-2: 명확한 거절. 구매 의사 전무.
3-4: 관심은 있으나 구매 의향 없음.
5-6: 고민 중. "생각해 볼게요" 수준.
7-8: 높은 구매 의향. 가격/옵션 등 구체적 확인.
9-10: 구매 결정 또는 거의 확정적 의향 표현.
""",
    },
    "final_outcome": {
        "name": "최종 행동 결과",
        "description": "대화의 최종 결과",
        "rubric": """
1-2: 즉시 이탈. 관계 형성 실패.
3-4: 거절 후 이탈. 다음 방문 가능성 낮음.
5-6: 거절이나 정보 교환은 이루어짐. 재방문 가능성 있음.
7-8: 연락처 교환, 재방문 약속, 또는 보류 후 긍정적 종료.
9-10: 구매 완료 또는 즉석 결제 의사 표현.
""",
    },
}


def get_evaluation_prompt(transcript: str) -> str:
    """평가용 프롬프트를 생성합니다."""

    rubric_text = ""
    for dim_key, dim in DIMENSION_RUBRICS.items():
        rubric_text += f"\n### {dim['name']} ({dim_key})\n{dim['description']}\n{dim['rubric']}\n"

    return f"""당신은 영업 대화 평가 전문가입니다.
아래 판매원-고객 대화를 읽고, 5가지 차원에서 1~10점으로 평가하세요.

## 대화 내용
{transcript}

## 평가 기준
{rubric_text}

## 응답 형식 (반드시 이 JSON 형식으로만 응답하세요)
{{
  "interest_level": {{"score": N, "reasoning": "근거"}},
  "conversation_continuation": {{"score": N, "reasoning": "근거"}},
  "emotional_change": {{"score": N, "reasoning": "근거"}},
  "purchase_intent": {{"score": N, "reasoning": "근거"}},
  "final_outcome": {{"score": N, "reasoning": "근거"}},
  "overall_summary": "종합 평가 요약"
}}
"""
