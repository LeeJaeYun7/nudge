"""쿠폰 사용 여부 판단 프롬프트 — 실증 연구 데이터 기반"""


EMPIRICAL_DATA = """
## 실증 연구 기반 참고 데이터 (반드시 판단에 반영하세요)

### EV 충전 동적 할인 인센티브 연구 (ScienceDirect 2025 — 슈퍼마켓 충전소 실증)
출처: "Dynamic incentives for electric vehicles charging at supermarket stations:
Causal insights on demand flexibility" — bilevel 최적화 + 인과적 머신러닝(DML) 결합

핵심 결과:
- **할인 1%p 증가 시 충전 수요 1.16kW 한계 증가** (인과적으로 입증)
- 사용자 반응은 시간대/요일에 따라 이질적 (treatment effect heterogeneity)
  → 동일 할인이라도 시간대별 효과가 다름
- 금전적 인센티브만이 수요 측 유연성(demand-side flexibility)을 실질적으로 유도
  → 단순 넛지(메시지, 알림)는 행동 변화를 일으키지 못함
- bilevel 모델로 최적 할인 수준을 결정하고, DML로 인과적 효과를 분리 측정
  → 할인 외 다른 요인(날씨, 시간대 등)의 영향을 제거한 순수 인센티브 효과

시사점: 할인 쿠폰은 실제로 충전 행동을 변화시키지만,
그 효과는 사용자 유형과 상황에 따라 다르므로 유형별 차별화가 필요

### 유효기간별 효과
- 24~48시간 긴급 쿠폰: 일반 대비 사용률 3~5% 높음
- 1주일 이내가 골든 타임 (82%가 1주 내 사용)
- 2주 이상: 잊어버리거나 무관심으로 미사용 가능성 급증

### LLM 기반 EV 사용자 디지털 트윈 연구 (IEEE/arXiv 2025)
- LLM을 활용한 EV 사용자 행동 시뮬레이션이 실제 파일럿에서 유효함을 입증
- 다차원 사용자 프로파일(충전 빈도, 차량 유형, 시간대 선호)이 정확도에 핵심
"""


def build_coupon_judge_prompt(
    age_group: str,
    charging_frequency: str,
    avg_charge_amount: float,
    avg_monthly_sessions: float,
    car_name: str,
    discount_rate: float,
    validity_days: int,
) -> str:
    discount_pct = int(discount_rate * 100)
    discount_amount = int(avg_charge_amount * discount_rate)

    # 충전 주기 계산 (일)
    if avg_monthly_sessions > 0:
        avg_interval_days = round(30 / avg_monthly_sessions, 1)
    else:
        avg_interval_days = 60  # 월 1회 미만

    return f"""당신은 전기차 충전 서비스 사용자 행동 분석 전문가입니다.
아래 실증 연구 데이터를 참고하여, 이 사용자가 쿠폰을 실제로 사용할지 판단하세요.
{EMPIRICAL_DATA}

## 이 사용자 정보
- 연령대: {age_group}
- 충전 빈도: {charging_frequency} (월평균 {avg_monthly_sessions:.1f}회, 약 {avg_interval_days}일 간격)
- 평균 1회 충전 금액: {avg_charge_amount:,.0f}원
- 차량: {car_name or '정보 없음'}

## 이 쿠폰 정보
- 할인율: {discount_pct}% (약 {discount_amount:,}원 할인)
- 유효기간: {validity_days}일
- 적용 조건: 다음 충전 시 앱에서 자동 적용

## 핵심 판단 로직
1. **충전 주기 vs 유효기간**: 평균 {avg_interval_days}일 간격으로 충전하는데 유효기간이 {validity_days}일
   → 유효기간 내 자연 충전 확률을 먼저 계산하세요
2. **할인 임계값**: {discount_pct}%는 연구 기준 10% 임계값 대비 어떤가?
   {discount_amount:,}원 할인은 충분한 동기가 되는가?
3. **추가 충전 여부**: 쿠폰이 없어도 유효기간 내에 어차피 충전했을 사용자는 false
   쿠폰 때문에 "추가로" 또는 "더 일찍" 충전하러 올 경우만 true
4. **연령대 요인**: {age_group}의 디지털 쿠폰 앱 활용 숙련도

## 응답 (JSON만 출력)
{{"will_use": true/false, "reasoning": "한 줄 판단 근거"}}"""
