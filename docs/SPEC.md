# Nudge - 제품/기능 사양서

## 한 줄 정의

AI가 수백 개의 영업 전략을 스스로 생성하고, 실제 고객 시뮬레이션을 통해 **가장 전환율 높은 전략을 찾아내는 영업 최적화 시스템**

---

## 1. 문제 정의 (Problem)

### 기존 세일즈의 구조적 한계

- 영업 성과는 **개인의 감각과 경험에 의존**
- 어떤 말투/타이밍/혜택이 효과적인지 **데이터 기반 검증 어려움**
- A/B 테스트는 제한적이며 **실제 고객 대상으로 실험 비용 큼**

### 핵심 문제

> "어떤 영업 방식이 가장 잘 팔리는지"를
> 빠르게, 대량으로, 안전하게 실험할 수 없다

---

## 2. 해결 방식 (Solution)

### 핵심 컨셉

> **AI가 스스로 영업 전략을 생성하고, 고객을 시뮬레이션하며, 성과 기반으로 최적화한다**

### 접근 방법

Nudge는 200개의 가상 고객 페르소나와 반복적으로 대화하면서 RALPH Loop를 통해 영업 전략을 **자동으로 생성, 실험, 평가, 학습, 최적화**한다.

```
추천을 잘하는 AI ❌
설득 전략을 스스로 학습하는 AI ✅
```

### 핵심 가치

- **자동화**: 전략 설계부터 평가까지 사람 개입 없이 동작
- **데이터 기반**: LLM-as-Judge 패턴으로 대화 품질을 정량 평가
- **비용 효율**: 대화 생성은 저비용 모델, 분석/평가는 고비용 모델로 분리
- **반복 학습**: 이전 실험의 성공/실패 패턴을 다음 전략에 반영

---

## 2. 핵심 컨셉: RALPH Loop

RALPH Loop는 Nudge의 핵심 최적화 엔진이다. 6단계의 순환 루프를 통해 영업 전략을 점진적으로 개선한다.

```
HYPOTHESIZE --> PLAN --> ACT --> EVALUATE --> REASON --> LEARN
     ^                                                    |
     +----------------------------------------------------+
```

| 단계 | 역할 | 사용 모델 |
|------|------|-----------|
| **H**ypothesize | 이전 학습 기반으로 새 영업 전략 가설 생성 | Expensive (Claude Sonnet) |
| **P**lan | 실험할 페르소나 선택 및 실행 계획 수립 | 규칙 기반 (LLM 미사용) |
| **A**ct | Sales Agent와 Customer Agent 간 대화 배치 실행 | Cheap (Gemini Flash) |
| **E**valuate | 5차원 지표로 대화 평가 (샘플 30개) | Expensive (Claude Sonnet) |
| **R**eason | 상위/하위 대화 비교, 성공/실패 패턴 분석 | Expensive (Claude Sonnet) |
| **L**earn | 재사용 가능한 학습 포인트 추출 | Expensive (Claude Sonnet) |

### 반복 과정

1. 첫 번째 반복: 기본 전략 가설 생성 (사전 학습 없음)
2. 두 번째 반복부터: 이전 결과와 축적된 학습을 참고하여 개선된 전략 생성
3. 수렴 감지: 점수 변화가 5% 미만인 상태가 2회 연속 발생하면 탐색 전략 주입 또는 조기 종료

---

## 3. 판매 제품

### VitaForest 올인원 데일리 멀티비타민

| 항목 | 내용 |
|------|------|
| 제품명 | VitaForest 올인원 데일리 멀티비타민 |
| 가격 | 49,900원 (정가 65,000원, 30일분) |
| 주요 성분 | 22종 비타민+미네랄, 프로바이오틱스, 루테인, 오메가3 |
| 인증 | GMP 인증, 식약처 기능성 인증 |
| 리뷰 | 4.7/5.0 (1,200+ 리뷰) |
| 프로모션 | 첫 구매 15% 쿠폰, 무료배송, 앱 결제 시 5% 추가 적립, 3+1 정기배송 할인 |
| 경쟁 제품 | 센트룸, 종근당, 솔가 |

> 제품 정보는 Sales Agent의 시스템 프롬프트에 주입되어, 대화 중 자연스럽게 소개된다.

---

## 4. 페르소나 시스템

### 개요

200개의 고객 페르소나가 `config/personas.yaml`에 정의되어 있다. 각 페르소나는 6가지 속성으로 구성되며, 이 속성 조합에 따라 대화 반응이 결정된다.

### 6가지 속성

| 속성 | 값 | 설명 |
|------|-----|------|
| **generation** (세대) | teen, 20s, 30s, 40s, 50s, 60plus | 연령대 |
| **interest_category** (관심 분야) | fashion, electronics, food, health, hobby, home | 주 관심 카테고리 |
| **purchase_tendency** (구매 성향) | impulse, deliberate, bargain_hunter, brand_loyal, needs_based | 구매 결정 패턴 |
| **price_sensitivity** (가격 민감도) | low, medium, high | 가격에 대한 반응 정도 |
| **reaction_pattern** (반응 패턴) | friendly, skeptical, impatient, curious, defensive | 대화 시 기본 태도 |
| **initial_mood** (초기 기분) | positive, neutral, negative | 대화 시작 시 감정 상태 |

추가로 각 페르소나는 `background` (배경 설명)과 `speech_style` (말투 특성)을 가진다.

### 자동 선별 로직 (`personas/selector.py`)

상품에 맞는 최적의 페르소나 조합을 자동으로 선별한다.

**선별 비율:**
- **60% 주요 매칭**: 상품 카테고리와 관심 분야가 일치하거나 관련된 페르소나
- **20% 도전자**: 회의적(skeptical), 방어적(defensive), 가격 민감도 높은 페르소나 (전략 스트레스 테스트용)
- **20% 다양성 확보**: 세대 다양성을 보장하는 라운드 로빈 방식 랜덤 선택

**카테고리 매칭:**
- 직접 매칭: 상품 카테고리 키워드 -> InterestCategory 매핑 (예: "비타민" -> HEALTH)
- 관련 카테고리: HEALTH와 관련된 FOOD, HOBBY 등도 2차 매칭 대상
- 가격/설명 기반 추론: 가격대와 설명 키워드로 적합한 purchase_tendency 추론

### RALPH Loop 내 페르소나 선택 (`ralph/plan.py`)

RALPH Loop 실행 시에는 더 단순한 로직을 사용한다:
- 전략의 `target_personas` 유형을 우선 포함
- 나머지는 랜덤으로 채움
- 전략이 특정 유형에 약하다면, 해당 유형을 집중 테스트할 수 있음

---

## 5. 에이전트 시스템

### 5.1 Sales Agent (LLM 기반)

**역할**: 온라인 쇼핑몰의 AI 채팅 상담원으로서 고객과 대화하며 제품 구매를 유도한다.

**구현**: `SalesAgent` 클래스는 `BaseAgent`를 상속하며, LLM을 통해 응답을 생성한다.

#### 소비자 구매 퍼널 기반 설계

Sales Agent는 소비자가 물건을 구매할 때 거치는 **의사결정 퍼널(AISAS)**을 따른다. 각 단계에서 Sales Agent의 역할이 다르다:

```
Attention(인지) → Interest(관심) → Search(탐색) → Action(행동) → Share(공유)
```

| 퍼널 단계 | 소비자 상태 | Sales Agent 역할 |
|-----------|------------|-----------------|
| **Attention** | 상품 페이지 방문, 아직 관심 없음 | 눈에 띄는 오프닝으로 주의 끌기 |
| **Interest** | 제품에 관심을 보이기 시작 | 핵심 혜택/차별점 제시, 공감 형성 |
| **Search** | 가격/리뷰/경쟁사 비교 중 | 구체적 정보 제공, 비교 우위 강조, 반론 대응 |
| **Action** | 구매 결정 직전 | 쿠폰/무료배송 제안, 리스크 제거 (무료 체험, 환불 보장) |
| **Share** | 구매 완료 | 만족도 확인, 후기 유도 |

이 퍼널 모델은 Sales Agent의 전략 설계에 반영된다:
- **Hypothesize 단계**에서 전략을 생성할 때, 각 퍼널 단계에 적합한 설득 기법을 배치
- **Evaluate 단계**에서 "어느 퍼널 단계에서 이탈했는가"를 분석

#### 카테고리별 전략 구사

20개 페르소나 카테고리(세대 × 반응 패턴)가 존재하며, **같은 카테고리의 고객에게는 동일한 전략을 적용**한다:

- 카테고리 예: `20대-호기심형`, `40대-회의적형`, `60대-방어적형` 등
- RALPH Loop의 Hypothesize에서 생성된 전략은 `target_personas`로 특정 카테고리를 지정
- 동일 카테고리 내 페르소나들은 같은 전략 하에서 대화를 수행
- 카테고리별 성과를 비교하여 "어떤 유형의 고객에게 어떤 전략이 효과적인지" 학습

**시스템 프롬프트 구성:**
- 판매 제품 정보 (제품명, 설명, 가격, 프로모션, 인증, 리뷰)
- 현재 적용할 영업 전략 (RALPH Loop에서 생성된 전략 주입)
  - 전략명, 접근 방식, 오프닝 스타일, 설득 기법, 반론 대응 방식
- 퍼널 단계별 행동 지침
- 행동 지침 (친근하고 전문적인 톤, 강압적이지 않게, 2-3문장 이내)

**전략 주입 메커니즘**: RALPH Loop의 Hypothesize 단계에서 생성된 `Strategy` 객체가 Sales Agent의 시스템 프롬프트에 포함된다. 전략에는 다음 요소가 포함된다:
- `name`: 전략명
- `approach`: 전반적 접근 방식
- `opening_style`: 첫 인사/오프닝 스타일
- `persuasion_tactics`: 설득 기법 목록
- `objection_handling`: 반론 대응 방식
- `target_personas`: 효과적일 페르소나 유형 (카테고리 단위)

### 5.2 Customer Agent

두 가지 구현이 존재한다:

#### 규칙 기반 고객 에이전트 (`RuleCustomerAgent`) - 기본 사용

**특징:**
- LLM 호출 없이 동작 (비용 0, 지연 시간 거의 없음)
- 페르소나 속성 기반 상태 머신
- 한국어 응답 템플릿 풀에서 상황에 맞는 응답을 선택

**내부 상태:**
- `interest` (관심도, 0~10): 페르소나의 `reaction_pattern`에 따라 초기값 설정
- `mood` (감정, -5~+5): 페르소나의 `initial_mood`에 따라 초기값 설정
- `turn_count`: 현재 턴 수
- 플래그: `heard_price`, `heard_review`, `heard_coupon`, `heard_shipping`

**상태 업데이트 로직:**
- 판매 메시지의 키워드를 분석 (가격, 리뷰, 성분, 혜택, 쿠폰, 배송, 비교, 공감, 압박 등)
- 키워드에 따라 관심도와 감정 값을 조정
- 공감 표현은 관심도/감정 상승, 압박 표현은 감정 하락 (특히 defensive 유형)
- 6턴 이후부터 자연적 관심 감소

**구매 결정 임계값:**
- `impulse`: 6.0, `deliberate`: 8.0, `bargain_hunter`: 7.0, `brand_loyal`: 8.5, `needs_based`: 7.5
- 가격 민감도 `high`이면 임계값 +1.0, `low`이면 -1.0

**응답 결정 흐름:**
1. 첫 턴: 감정에 따른 인사 반응
2. 방어적 고객 + 낮은 관심 (3턴 이상): 빠른 이탈
3. 급한 성격 + 낮은 관심 (4턴 이상): 빠른 이탈
4. 쿠폰/배송/리뷰 관련 반응
5. 가격 반응 (가격 민감도에 따라 긍정/중립/부정)
6. 구매 결정 (관심도 >= 임계값, 4턴 이상)
7. 질문 (관심도 > 4)
8. 브랜드 충성/필요 기반 반론
9. 7턴 이상: 최종 결정 압박
10. 관심도에 따른 일반 반응

#### LLM 기반 고객 에이전트 (`CustomerAgent`) - 옵션

**특징:**
- LLM을 사용하여 더 자연스러운 응답 생성
- 페르소나의 전체 프로필을 시스템 프롬프트에 주입
- 비용이 발생하므로 기본적으로 사용하지 않음

### 5.3 모델 분리 전략 (비용 최적화)

| 용도 | 모델 | 기본값 | 이유 |
|------|------|--------|------|
| 대화 생성 (ACT) | MODEL_CHEAP | Gemini 2.0 Flash | 대량 대화를 저비용으로 생성 |
| 전략 생성 (HYPOTHESIZE) | MODEL_EXPENSIVE | Claude Sonnet | 복잡한 전략 설계에 높은 추론 능력 필요 |
| 대화 평가 (EVALUATE) | MODEL_EXPENSIVE | Claude Sonnet | 정확한 다차원 평가 필요 |
| 패턴 분석 (REASON) | MODEL_EXPENSIVE | Claude Sonnet | 성공/실패 패턴 심층 분석 |
| 학습 추출 (LEARN) | MODEL_EXPENSIVE | Claude Sonnet | 재사용 가능한 인사이트 추출 |

모든 LLM 호출은 OpenRouter API를 통해 이루어진다 (`AsyncOpenAI` 클라이언트, base_url: `https://openrouter.ai/api/v1`).

---

## 6. 대화 엔진

### 턴 기반 오케스트레이션

`ConversationEngine` 클래스가 Sales Agent와 Customer Agent 간의 대화를 관리한다.

**대화 흐름:**
1. Sales Agent가 먼저 발화 (짝수 턴: 0, 2, 4, ...)
2. Customer Agent가 응답 (홀수 턴: 1, 3, 5, ...)
3. 고객 발화 후 종료 조건 확인
4. 종료 조건 충족 또는 최대 턴 도달 시 대화 종료

**데이터 모델:**
- `Turn`: 발화 한 건 (speaker, content, turn_number, timestamp)
- `ConversationSession`: 완료된 대화 세션 (session_id, persona_id, strategy_id, turns, termination_reason 등)

### 종료 조건

고객 발화에 특정 키워드가 포함되면 대화가 종료된다:

| 종료 유형 | 키워드 예시 |
|-----------|------------|
| **purchase** (구매) | "결제할게요", "구매할게요", "살게요", "장바구니 담을게요" |
| **customer_exit** (거절/이탈) | "안 살게요", "됐어요", "필요 없어요", "나갈게요" |
| **wishlist** (보류/찜) | "찜해둘게요", "위시리스트", "다시 올게요", "생각해볼게요" |
| **max_turns** (최대 턴 도달) | 기본 16턴 |

---

## 7. 5차원 평가 시스템

### LLM-as-Judge 패턴

대화 품질을 정량화하기 위해 LLM(Claude Sonnet)이 평가자 역할을 수행한다. 완료된 대화 전문(transcript)을 입력으로 받아 5개 차원에서 1~10점을 매긴다.

### 5가지 평가 차원

| 차원 | 설명 | 가중치 | 1-2점 | 5-6점 | 9-10점 |
|------|------|--------|-------|-------|--------|
| **관심도** (interest_level) | 고객이 제품에 관심을 보인 정도 | 20% | 전혀 관심 없음 | 보통 수준, 일부 질문 | 매우 높은 관심, 비교 질문 |
| **대화 지속도** (conversation_continuation) | 고객이 대화에 참여하고 지속한 정도 | 15% | 1-2턴 내 종료, 단답 | 적당한 길이, 일부 능동적 | 매우 활발, 새 토픽 제시 |
| **감정 변화** (emotional_change) | 대화 중 감정이 긍정적으로 변화한 정도 | 20% | 감정 악화, 짜증 | 중립 유지, 미세 변화 | 큰 감정 전환, 매우 즐거움 |
| **구매 의향** (purchase_intent) | 구매 의향을 표현한 정도 | 25% | 명확한 거절 | 고민 중 | 구매 결정/거의 확정 |
| **최종 행동 결과** (final_outcome) | 대화의 최종 결과 | 20% | 즉시 이탈 | 거절이나 정보 교환 | 구매 완료/즉석 결제 |

### 가중 종합 점수

```
weighted_score = interest_level * 0.20
              + conversation_continuation * 0.15
              + emotional_change * 0.20
              + purchase_intent * 0.25
              + final_outcome * 0.20
```

구매 의향(purchase_intent)이 가장 높은 가중치(25%)를 가진다.

### 평가 프로세스

1. 대화 전문(transcript)을 평가 프롬프트에 삽입
2. 각 차원별 루브릭(rubric)을 프롬프트에 포함
3. LLM이 JSON 형식으로 5차원 점수와 근거(reasoning), 종합 평가 요약을 반환
4. 비용 절감을 위해 전체 대화가 아닌 **샘플 30개만** 평가

### 집계

`Aggregator` 클래스가 여러 대화의 평가 결과를 집계한다:
- 각 차원별 평균(mean), 표준편차(stdev), 최소/최대값
- 가중 종합 점수의 통계

---

## 8. 통계 분석

### 이터레이션별 통계 (`IterationStats`)

각 RALPH Loop 이터레이션에 대해 다음을 계산한다:
- 평균 가중 점수 (avg_weighted_score)
- 구매율 (purchase_rate)
- 각 차원별 평균 (관심도, 지속도, 감정, 의향, 결과)
- 대화 수, 평가된 대화 수

### 초기 vs 후기 비교 (`StatisticalComparison`)

초기 이터레이션과 후기 이터레이션을 통계적으로 비교한다:

- **Welch's t-test**: 평균 가중 점수의 유의미한 차이 검증 (p < 0.05)
- **Chi-square test**: 구매율 차이의 통계적 유의미성 검증 (2x2 분할표)
- **95% Wald 신뢰구간**: 구매율 차이의 신뢰구간

### 페르소나별 분석 (`PerPersonaStats`)

각 페르소나에 대해 전체 이터레이션에 걸친 통계를 계산한다:
- 평균 점수, 구매율
- 이터레이션별 점수 트렌드 (score_trend)
- 세대, 반응 패턴 정보 포함

### 수렴 감지

이동 평균(window=2)을 계산하고, 연속된 이터레이션 간 점수 변화가 임계값(0.1) 미만인 상태가 patience(2)회 이상 지속되면 수렴으로 판단한다.

### 전체 분석 결과 (`RalphAnalysis`)

- 이터레이션별 통계 리스트
- 초기 vs 후기 통계 비교
- 페르소나별 통계 리스트
- 이동 평균 점수
- 수렴 감지 여부 및 수렴 이터레이션

---

## 9. 데이터 저장

### SQLite + SQLModel

Nudge는 SQLModel(SQLAlchemy 기반)을 사용하여 SQLite 데이터베이스에 실험 데이터를 저장한다.

기본 DB 경로: `data/db/nudge.db`

### 5테이블 구조

| 테이블 | 설명 | 주요 컬럼 |
|--------|------|-----------|
| **experiments** | 실험 메타데이터 | experiment_id, product_name, total_iterations, config_snapshot, started_at, ended_at |
| **conversations** | 대화 기록 | session_id, experiment_id, iteration, strategy_id, persona_id, total_turns, termination_reason, transcript |
| **evaluations** | 대화 평가 결과 | session_id, experiment_id, 5차원 점수, weighted_score, overall_summary |
| **strategies** | 전략 기록 | strategy_id, experiment_id, iteration, name, approach, opening_style, persuasion_tactics, objection_handling, avg_score |
| **learnings** | 학습 기록 | experiment_id, iteration, content |

### 저장 시점

`PersistentRALPHLoop`에서 각 이터레이션이 끝날 때마다:
1. 전략 저장
2. 평가 결과 저장 (샘플)
3. 학습 포인트 저장
4. 대화 기록 저장 (샘플)
5. 실험 종료 시 종료 시각 업데이트

---

## 10. API 엔드포인트

### 서버 구성

- **프레임워크**: FastAPI
- **실행**: `uvicorn src.api.main:app --reload`
- **기본 포트**: 8000
- **CORS**: 모든 오리진 허용

### 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 프론트엔드 HTML 서빙 |
| `GET` | `/api/status` | RALPH Loop 실행 상태 조회 |
| `POST` | `/api/sim/start` | 단일 대화 시뮬레이션 시작 (SSE 스트리밍) |
| `POST` | `/api/loop/start` | RALPH Loop 시작 (백그라운드 실행) |
| `GET` | `/api/loop/stream` | RALPH Loop 진행 상황 SSE 스트리밍 |
| `POST` | `/api/loop/stop` | RALPH Loop 중지 |
| `GET` | `/api/loop/analysis` | 최근 완료된 Loop의 통계 분석 결과 조회 |

### 요청/응답 형식

#### POST `/api/sim/start`

**요청:**
```json
{
  "persona": {
    "id": "P001",
    "name": "김지원",
    "gen": "20대",
    "cat": "건강",
    "tendency": "충동구매",
    "sensitivity": "중간",
    "reaction": "호기심",
    "mood": "긍정",
    "desc": "건강에 관심 많은 대학생"
  }
}
```

**응답 (SSE 스트림):**
```
data: {"type": "turn", "speaker": "sales", "content": "안녕하세요!", "turn_number": 1}
data: {"type": "turn", "speaker": "customer", "content": "네 안녕하세요~", "turn_number": 2}
...
data: {"type": "eval_start"}
data: {"type": "eval_result", "termination_reason": "purchase", "interest_level": {"score": 8, "reasoning": "..."}, ...}
data: {"type": "done"}
```

#### POST `/api/loop/start`

**요청:**
```json
{
  "personas": [],
  "product_name": "VitaForest 올인원 데일리 멀티비타민",
  "product_category": "건강",
  "product_price": 49900,
  "product_description": "22종 비타민+미네랄...",
  "n_iterations": 5,
  "personas_count": 20
}
```

**응답:**
```json
{
  "status": "started",
  "total_personas": 20,
  "iterations": 5
}
```

#### GET `/api/loop/stream` (SSE)

```
data: {"type": "iteration_start", "iteration": 1, "total": 5}
data: {"type": "iteration_end", "iteration": 1, "strategy_name": "...", "avg_score": 5.2, "purchase_rate": 0.25, ...}
...
data: {"type": "done"}
```

#### GET `/api/loop/analysis`

`RalphAnalysis` 모델의 전체 JSON을 반환한다. 이터레이션별 통계, 초기/후기 비교, 페르소나별 분석, 수렴 정보 등을 포함한다.

---

## 11. 프론트엔드

### 구성

단일 HTML 파일 (`frontend/index.html`)로 구성된 경량 웹 대시보드이다. vanilla JavaScript와 SSE를 사용한다.

### 기능

#### 쇼핑 시뮬레이션
- 페르소나를 선택/생성하여 단일 대화를 실시간으로 시뮬레이션
- SSE를 통해 턴마다 실시간 채팅 인터페이스 업데이트
- 대화 종료 후 5차원 평가 결과 표시

#### RALPH Loop 대시보드
- 상품 정보와 페르소나를 설정하여 RALPH Loop 실행
- SSE를 통해 이터레이션별 진행 상황 실시간 표시
- 각 이터레이션의 전략, 구매율, 매출, 학습 내용 표시
- Loop 완료 후 통계 분석 결과 표시

### 서빙 방식

FastAPI의 `FileResponse`로 `frontend/index.html`을 `/` 경로에서 서빙한다.

---

## 12. 비용 구조

### 모델별 비용 (OpenRouter 기준 추정)

| 시나리오 | 비용 |
|----------|------|
| 단일 대화 테스트 | ~50원 |
| RALPH Loop 1회 (100명) | ~450원 |
| RALPH Loop 5회 (100명/회) | ~2,200원 |

### 비용 절감 전략

1. **모델 분리**: 대화 생성(대량)은 저비용 Gemini Flash, 분석/평가는 고비용 Claude Sonnet
2. **규칙 기반 고객**: Customer Agent를 LLM 대신 규칙 기반으로 동작시켜 비용 절반 절감
3. **샘플 평가**: 전체 대화가 아닌 이터레이션당 30개 샘플만 평가
4. **이터레이션당 비용 구조**:
   - ACT (대화 생성): Sales Agent만 LLM 호출 * 대화 수 * 턴 수
   - EVALUATE: 샘플 30개 * 평가 프롬프트 1회
   - HYPOTHESIZE + REASON + LEARN: 각 1회 LLM 호출

---

## 13. 향후 계획

### Customer Agent LLM 하이브리드화

현재 규칙 기반 고객 에이전트는 비용 효율적이지만, 응답의 자연스러움에 한계가 있다. 향후에는:
- 규칙 기반으로 응답 방향을 결정하되, LLM으로 자연스러운 문장을 생성하는 하이브리드 방식
- 핵심 페르소나(상위/하위 10%)에 대해서만 LLM 고객을 사용하는 선택적 활용

### 실제 고객 데이터 활용

- 실제 쇼핑몰 채팅 로그를 학습 데이터로 활용
- 실제 구매 전환 데이터와 RALPH Loop 평가 점수 간 상관관계 검증
- 페르소나를 실제 고객 세그먼트 기반으로 재설계

### 추가 개선 방향

- **다중 상품 지원**: 현재 VitaForest 하드코딩된 부분을 상품 설정 파일로 분리
- **A/B 테스트 프레임워크**: 동일 페르소나에 두 전략을 동시 실행하여 직접 비교
- **멀티턴 전략**: 단일 대화 내 전략 전환 (예: 초반 공감 -> 중반 정보 제공 -> 후반 클로징)
- **평가 차원 확장**: 브랜드 인식 변화, 재방문 의향 등 추가 차원
- **DB 분석 대시보드**: 실험 간 비교, 장기 트렌드 분석 기능
- **수렴 이후 탐색 고도화**: 현재 단순 contrarian 학습 주입에서 더 체계적인 exploration-exploitation 전략으로
