# Nudge - Full Product Specification

> 이 문서만으로 전체 프로젝트를 재현할 수 있도록 작성된 상세 스펙 문서입니다.

## 1. 프로젝트 개요

**Nudge**는 AI 영업 에이전트가 200개 고객 페르소나와 반복 대화하면서, 어떤 설득 전략이 가장 효과적인지 스스로 실험하고 최적화하는 시스템입니다.

```
추천을 잘하는 AI ❌
설득 전략을 스스로 학습하는 AI ✅
```

### 핵심 메커니즘: RALPH Loop

```
┌─────────────────────────────────────────────────┐
│                  RALPH LOOP                      │
│                                                  │
│  HYPOTHESIZE ──→ PLAN ──→ ACT ──→ EVALUATE      │
│       ↑                              │           │
│       └──── LEARN ←── REASON ←───────┘           │
└─────────────────────────────────────────────────┘
```

매 반복마다:
1. **HYPOTHESIZE** — 이전 학습 기반으로 새 영업 전략 가설 생성 (Sonnet)
2. **PLAN** — 실험할 페르소나 200명 선택
3. **ACT** — Sales Agent ↔ Customer Agent 200개 대화 병렬 실행 (Gemini Flash)
4. **EVALUATE** — 30개 샘플을 5차원 평가 (Sonnet, LLM-as-Judge)
5. **REASON** — 성공/실패 패턴 분석 (Sonnet)
6. **LEARN** — 재사용 가능한 학습 포인트 추출 (Sonnet)

학습 결과가 다음 반복의 HYPOTHESIZE에 피드백되어 전략이 진화합니다.

### 판매 제품

**VitaForest 올인원 데일리 멀티비타민** (₩49,900)
- 22종 비타민+미네랄, 프로바이오틱스, 루테인, 오메가3
- GMP 인증, 식약처 기능성 인증
- 프로모션: 첫 구매 15% 쿠폰, 무료배송, 3+1 정기배송 할인
- 리뷰 평점: 4.7/5.0 (1,200+ 리뷰)
- 경쟁: 센트룸(₩38,000), 종근당(₩55,000), 솔가(₩72,000)

---

## 2. 기술 스택

| 분류 | 기술 |
|------|------|
| LLM | OpenRouter (Gemini Flash + Claude Sonnet) |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | Vanilla JS, SSE 실시간 스트리밍, 단일 HTML |
| Data | Pydantic, SQLModel, SQLite |
| 통계 | scipy, numpy (t-test, chi-square, 신뢰구간) |

### 모델 분리 (비용 최적화)

| 용도 | 모델 | 가격 |
|------|------|------|
| 대화 생성 (ACT) | `google/gemini-2.0-flash-001` | $0.1/M input, $0.4/M output |
| 평가/전략/분석 | `anthropic/claude-sonnet-4` | $3/M input, $15/M output |
| 고객 응답 (RuleCustomer) | 규칙 기반 | **$0 (LLM 미사용)** |

---

## 3. 프로젝트 구조

```
nudge/
├── config/
│   ├── settings.py         # 환경 설정 (Pydantic Settings)
│   ├── default.yaml        # 기본 설정값 (대화, 평가 가중치)
│   └── personas.yaml       # 고객 페르소나 200개
│
├── src/
│   ├── llm.py              # OpenRouter 클라이언트 + chat() 공통 함수
│   │
│   ├── agents/
│   │   ├── base.py         # BaseAgent (추상 클래스)
│   │   ├── sales_agent.py  # Sales Agent (LLM 기반)
│   │   ├── customer_agent.py  # Customer Agent (LLM 기반, 디버그용)
│   │   ├── rule_customer.py   # Customer Agent (규칙 기반, 비용 0)
│   │   └── prompts/
│   │       ├── sales_system.py    # Sales 시스템 프롬프트 빌더
│   │       └── customer_system.py # Customer 시스템 프롬프트 빌더
│   │
│   ├── personas/
│   │   ├── schema.py       # Persona 모델 + Enum 정의
│   │   ├── loader.py       # YAML 로더
│   │   └── selector.py     # AI 기반 페르소나 자동 선택
│   │
│   ├── conversation/
│   │   ├── turn.py         # Turn, ConversationSession 모델
│   │   ├── engine.py       # 턴 기반 대화 오케스트레이션
│   │   └── rules.py        # 종료 키워드 감지
│   │
│   ├── evaluation/
│   │   ├── schema.py       # DimensionScore, EvaluationResult 모델
│   │   ├── dimensions.py   # 5차원 평가 루브릭 + 프롬프트
│   │   ├── evaluator.py    # LLM-as-Judge 평가기
│   │   ├── aggregator.py   # 결과 통계 집계
│   │   └── statistics.py   # t-test, chi-square, 수렴 감지
│   │
│   ├── ralph/
│   │   ├── strategy.py     # Strategy, StrategyResult 모델
│   │   ├── loop.py         # RALPHLoop (핵심 루프)
│   │   ├── hypothesize.py  # 전략 가설 생성
│   │   ├── plan.py         # 페르소나 선택
│   │   ├── act.py          # 전략 실행 (대화 배치)
│   │   ├── reason.py       # 패턴 분석
│   │   ├── learn.py        # 학습 포인트 추출
│   │   └── persistent_loop.py # DB 저장 + 수렴 감지 확장
│   │
│   ├── storage/
│   │   ├── database.py     # SQLite 엔진 + 테이블 생성
│   │   ├── models.py       # DB 테이블 정의 (SQLModel)
│   │   └── repository.py   # CRUD 레이어
│   │
│   └── api/
│       └── main.py         # FastAPI 서버 + SSE 스트리밍
│
├── frontend/
│   └── index.html          # 웹 대시보드 (단일 대화 + RALPH Loop)
│
├── scripts/
│   ├── run_server.py       # UTF-8 서버 시작
│   ├── run_simulation.py   # RALPH Loop CLI 실행
│   └── run_single_conversation.py  # 단일 대화 디버그
│
├── .env.example            # 환경변수 템플릿
├── pyproject.toml          # 의존성
└── README.md
```

---

## 4. 설정 (Configuration)

### 4.1 환경변수 (.env)

```
OPENROUTER_API_KEY=sk-or-...
MODEL_CHEAP=google/gemini-2.0-flash-001
MODEL_EXPENSIVE=anthropic/claude-sonnet-4
DATABASE_URL=sqlite+aiosqlite:///data/db/nudge.db
```

### 4.2 Settings 클래스 (`config/settings.py`)

```python
class Settings(BaseSettings):
    openrouter_api_key: str
    model_cheap: str = "google/gemini-2.0-flash-001"
    model_expensive: str = "anthropic/claude-sonnet-4"
    database_url: str = "sqlite+aiosqlite:///data/db/nudge.db"
    max_turns: int = 16
    conversation_timeout_sec: int = 120
    ralph_iterations: int = 5
    personas_per_iteration: int = 200
    concurrent_conversations: int = 50
```

### 4.3 시뮬레이션 기본값

| 항목 | 값 |
|------|-----|
| 페르소나 풀 | 200개 |
| 루프당 대화 수 | 200명 |
| 반복 횟수 | 5회 |
| 동시 실행 수 | 10 |
| 최대 턴/대화 | 16턴 |
| 평가 샘플/루프 | 30개 |
| 수렴 임계값 | 5% |
| 수렴 인내값 | 2회 연속 |

---

## 5. 페르소나 시스템

### 5.1 페르소나 스키마 (`src/personas/schema.py`)

각 페르소나는 7개 차원으로 정의됩니다:

| 필드 | 타입 | 값 |
|------|------|-----|
| `generation` | Enum | teen, 20s, 30s, 40s, 50s, 60plus |
| `interest_category` | Enum | fashion, electronics, food, health, hobby, home |
| `purchase_tendency` | Enum | impulse, deliberate, bargain_hunter, brand_loyal, needs_based |
| `price_sensitivity` | Enum | low, medium, high |
| `reaction_pattern` | Enum | friendly, skeptical, impatient, curious, defensive |
| `initial_mood` | Enum | positive, neutral, negative |
| `speech_style` | str | "반말 위주, 줄임말 사용" 등 |

추가 필드: `id` (P001~P200), `name`, `background`

### 5.2 페르소나 예시 (personas.yaml)

```yaml
- id: P001
  name: "김하은"
  generation: teen
  interest_category: fashion
  purchase_tendency: impulse
  price_sensitivity: high
  reaction_pattern: curious
  initial_mood: positive
  background: "고등학생, SNS 트렌드에 민감, 용돈으로 쇼핑"
  speech_style: "반말 위주, 줄임말 사용, 리액션 큼"
```

200개 페르소나가 6개 세대에 걸쳐 균등 분포됩니다.

### 5.3 AI 페르소나 선택기 (`src/personas/selector.py`)

상품 카테고리에 따라 관련 페르소나를 자동 선택합니다:

- **60% 매칭**: 상품 카테고리와 일치하는 `interest_category`
- **20% 챌린저**: skeptical, defensive, impatient + 가격 민감도 높은 페르소나
- **20% 다양성**: 세대별 라운드로빈으로 채움

```python
# 사용 예
selected = recommend_personas_for_product(
    personas, product_name="VitaForest", product_category="건강", product_price=49900
)
# → health 60% + challenger 20% + diverse 20%
```

키워드 매핑: "비타민"→HEALTH, "전자기기"→ELECTRONICS, "패션"→FASHION 등

---

## 6. 에이전트 시스템

### 6.1 LLM 클라이언트 (`src/llm.py`)

```python
def create_client(api_key: str) -> AsyncOpenAI:
    """OpenRouter 호환 클라이언트 생성"""
    return AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

async def chat(client, model, messages, max_tokens=1024, system=None) -> str:
    """공통 LLM 호출. system prompt를 messages에 주입."""
```

### 6.2 BaseAgent (`src/agents/base.py`)

```python
class BaseAgent(ABC):
    def __init__(self, client: AsyncOpenAI, model: str, system_prompt: str = "")

    @abstractmethod
    def build_system_prompt(self) -> str: ...

    async def respond(self, conversation_history: list[Turn]) -> str:
        """대화 이력 기반 응답 생성. chat() 호출."""

    def _build_messages(self, history: list[Turn]) -> list[dict]:
        """Turn → OpenAI 메시지 포맷 변환. 자신=assistant, 상대=user"""

    @property
    @abstractmethod
    def role(self) -> str: ...  # "sales" | "customer"
```

### 6.3 SalesAgent (`src/agents/sales_agent.py`)

```python
class SalesAgent(BaseAgent):
    def __init__(self, client, model, product_name, product_description, product_price, strategy=None)
    role = "sales"
```

시스템 프롬프트에 전략이 주입됩니다:

```
당신은 온라인 쇼핑몰의 AI 채팅 상담원입니다.

## 판매 제품 정보
- 제품명: {product_name}
- 설명: {product_description}
- 가격: {product_price}
- 프로모션: 첫 구매 15% 쿠폰, 무료배송, ...
- 인증: GMP 인증, 식약처 기능성 인증
- 리뷰 평점: 4.7/5.0

## 현재 적용할 영업 전략    ← RALPH가 생성한 전략
- 전략명: {strategy.name}
- 접근 방식: {strategy.approach}
- 오프닝 스타일: {strategy.opening_style}
- 설득 기법: {strategy.persuasion_tactics}
- 반론 대응 방식: {strategy.objection_handling}

## 행동 지침
1. 친근하고 전문적인 톤
2. 고객 반응에 맞게 대응
3. 한 번에 2-3문장 이내
...
```

### 6.4 RuleCustomerAgent (`src/agents/rule_customer.py`)

**LLM 미사용, 비용 $0의 규칙 기반 고객 에이전트.**

내부 상태 머신:

```python
class RuleCustomerAgent:
    interest: float  # 0~10, 초기값: reaction_pattern 기반
    mood: float      # -5~+5, 초기값: initial_mood 기반
    turn_count: int
    heard_price, heard_review, heard_coupon, heard_shipping: bool  # 중복 방지 플래그
```

**초기값 테이블:**

| reaction_pattern | 초기 interest |
|-----------------|---------------|
| curious | 5 |
| friendly | 4 |
| skeptical | 3 |
| impatient | 3 |
| defensive | 2 |

| initial_mood | 초기 mood |
|-------------|-----------|
| positive | +2 |
| neutral | 0 |
| negative | -2 |

**구매 임계값** (`purchase_tendency` + `price_sensitivity`):

| purchase_tendency | 기본 임계값 | high 가격민감 | low 가격민감 |
|------------------|------------|--------------|-------------|
| impulse | 6.0 | 7.0 | 5.0 |
| deliberate | 8.0 | 9.0 | 7.0 |
| bargain_hunter | 7.0 | 8.0 | 6.0 |
| brand_loyal | 8.5 | 9.5 | 7.5 |
| needs_based | 7.5 | 8.5 | 6.5 |

**키워드 분석** (`_analyze_sales_message`):

| 분석 항목 | 감지 키워드 |
|----------|-----------|
| mentions_price | 원, 할인, 가격, 쿠폰, 세일, 프로모션 |
| mentions_review | 리뷰, 후기, 평점, 별점, 평가 |
| mentions_spec | 비타민, 미네랄, 프로바이오틱스, 루테인, 오메가, GMP, 성분, 함량 |
| mentions_benefit | 무료배송, 증정, 적립, 혜택, 이벤트, 면역, 피로, 에너지, 활력 |
| mentions_coupon | 쿠폰, 할인코드, 첫 구매 |
| mentions_shipping | 배송, 도착, 출발, 당일, 내일 |
| mentions_compare | 센트룸, 종근당, 솔가, 약국, 비교 |
| is_empathetic | 그렇죠, 맞아요, 이해, 공감, 고민 |
| is_pushy | 지금 바로, 서두르, 놓치, 마지막 |

**상태 업데이트 규칙** (`_update_state`):

| 트리거 | interest 변화 | mood 변화 |
|--------|-------------|-----------|
| 스펙 언급 | +0.3~0.8 | - |
| 리뷰 언급 (최초) | +0.5~1.2 | - |
| 쿠폰 언급 (최초) | +0.5~1.0 | - |
| 배송 언급 (최초) | +0.2~0.5 | - |
| 비교 언급 | +0.2~0.6 | - |
| 공감 표현 | +0.1~0.3 | +0.3~0.8 |
| 강압적 표현 | - | -0.3~1.0 |
| 강압 + defensive | -0.5~1.5 | -0.3~1.0 |
| 가격 + high민감 (최초) | -0.3~0.8 | - |
| 가격 + low민감 (최초) | +0.1~0.5 | - |
| 턴 > 6 | -0~0.3 (자연감소) | - |

**응답 결정 흐름:**

```
1. 첫 턴 → mood 기반 인사 (positive/neutral/negative)
2. defensive + interest<3 + turn>=3 → EXIT
3. impatient + interest<4 + turn>=4 → EXIT
4. 쿠폰 감지 → 쿠폰 반응
5. 배송 감지 + interest>5 → 배송 반응
6. 리뷰 감지 + interest>4 → 리뷰 반응
7. 가격 감지 → 가격민감도별 반응
8. interest >= 임계값 + turn>=4 → 구매/보류
9. interest>4 + 질문형 → 관심 질문
10. brand_loyal + turn<=4 → 브랜드 비교 질문
11. needs_based + interest<6 → 필요성 의문
12. turn>=7 → 구매 압박 (임계값-1 이상이면 구매)
13. interest별 일반 반응 (>5: 질문, >3: 고민, <=3: 이탈)
```

**응답 템플릿 풀** (각 3~9개):

| 카테고리 | 예시 |
|---------|------|
| GREETINGS_POSITIVE | "네 안녕하세요~", "안녕하세요 ㅎㅎ" |
| INTEREST_QUESTIONS | "하루에 몇 포 먹어야 돼요?", "부작용 같은 건 없어요?" |
| PRICE_REACTIONS_NEGATIVE | "너무 비싸네요.", "5만원은 좀 많다..." |
| PURCHASE_POSITIVE | "좋아요, 장바구니 담을게요!", "바로 결제할게요!" |
| OBJECTION_BRAND | "센트룸 먹고 있는데 굳이 바꿀 필요가 있을까요?" |
| EXIT_LINES | "됐어요. 필요 없어요.", "안 살게요." |

---

## 7. 대화 엔진

### 7.1 데이터 모델 (`src/conversation/turn.py`)

```python
class Turn(BaseModel):
    speaker: str       # "sales" | "customer"
    content: str       # 발화 내용
    turn_number: int
    timestamp: datetime

class ConversationSession(BaseModel):
    session_id: str                    # UUID
    persona_id: str
    strategy_id: str = ""
    product_name: str
    turns: list[Turn]
    started_at: datetime
    ended_at: datetime | None
    termination_reason: str            # "max_turns" | "customer_exit" | "purchase" | "wishlist"

    @property
    def total_turns(self) -> int

    @property
    def transcript(self) -> str        # "[판매원] ...\n[고객] ..."
```

### 7.2 대화 오케스트레이션 (`src/conversation/engine.py`)

```python
class ConversationEngine:
    def __init__(self, max_turns: int = 16)

    async def run(self, sales_agent, customer_agent, ...) -> ConversationSession:
        for turn_num in range(max_turns):
            if turn_num % 2 == 0:  # 짝수 = Sales
                response = await sales_agent.respond(turns)
            else:                   # 홀수 = Customer
                response = await customer_agent.respond(turns)

            turns.append(Turn(speaker, response, turn_num+1))

            if speaker == "customer":
                term = check_termination(response)
                if term is not None:
                    break
```

### 7.3 종료 규칙 (`src/conversation/rules.py`)

| 결과 | 키워드 |
|------|--------|
| **purchase** | 결제할게요, 구매할게요, 살게요, 장바구니 담을게요, 바로 결제 |
| **customer_exit** | 안 살게요, 됐어요, 필요 없어요, 나갈게요, 그만하세요 |
| **wishlist** | 찜해둘게요, 위시리스트, 다시 올게요, 나중에, 생각해볼게요 |

---

## 8. 평가 시스템

### 8.1 5차원 평가 지표

| 차원 | 가중치 | 1-2점 | 5-6점 | 9-10점 |
|------|--------|-------|-------|--------|
| **관심도** | 20% | 무관심 | 보통 관심 | 구체적 사용 시나리오까지 상상 |
| **대화 지속도** | 15% | 1-2턴 이탈 | 보통 참여 | 매우 적극적, 주제 주도 |
| **감정 변화** | 20% | 악화 | 중립/소폭 개선 | 큰 폭 긍정 전환 |
| **구매 의향** | 25% | 명확한 거절 | 고민 중 | 구매 결정/확정 |
| **최종 결과** | 20% | 즉시 이탈 | 거절 but 정보 교환 | 구매 완료 |

### 8.2 평가기 (`src/evaluation/evaluator.py`)

```python
class Evaluator:
    def __init__(self, client: AsyncOpenAI, model: str = "anthropic/claude-sonnet-4")

    async def evaluate(self, session: ConversationSession) -> EvaluationResult:
        prompt = get_evaluation_prompt(session.transcript)
        raw = await chat(self.client, self.model, [{"role": "user", "content": prompt}])
        # JSON 파싱 → EvaluationResult (5차원 점수 + 종합)
```

종합 점수: `weighted_score = interest*0.2 + continuation*0.15 + emotion*0.2 + intent*0.25 + outcome*0.2`

### 8.3 통계 분석 (`src/evaluation/statistics.py`)

루프 완료 후 통계적 유의성을 검증합니다:

```python
class RalphAnalysis(BaseModel):
    iterations: list[IterationStats]           # 반복별 통계
    comparison: StatisticalComparison          # 초반 vs 후반 비교
    per_persona: list[PerPersonaStats]         # 페르소나별 성과
    moving_average_scores: list[float]         # 이동평균
    convergence_detected: bool                 # 수렴 감지 여부
    convergence_iteration: int | None          # 수렴 시점
```

**StatisticalComparison:**
- t-test: 초반 2회 vs 후반 2회 평균 점수 차이 검정
- chi-square: 초반 vs 후반 구매율 차이 검정
- 95% 신뢰구간 (Wald CI)
- `is_significant`: p < 0.05

---

## 9. RALPH Loop 상세

### 9.1 전략 모델 (`src/ralph/strategy.py`)

```python
class Strategy(BaseModel):
    id: str                        # "S001", "S002", ...
    name: str                      # "신뢰 구축 중심 전략"
    approach: str                  # 전반적 접근 방식
    opening_style: str             # 첫 인사 스타일
    persuasion_tactics: list[str]  # ["리뷰 강조", "가격 비교", ...]
    objection_handling: str        # 반론 대응 방식
    target_personas: list[str]     # 타겟 페르소나 유형
    iteration: int                 # RALPH 반복 회차

class StrategyResult(BaseModel):
    strategy_id: str
    iteration: int
    avg_weighted_score: float
    conversation_count: int
    purchase_count, wishlist_count, exit_count: int
    purchase_rate: float
    total_revenue: float
    best_persona_types: list[str]
    key_insights: list[str]
```

### 9.2 HYPOTHESIZE (`src/ralph/hypothesize.py`)

```python
async def generate_hypothesis(client, model, iteration, prior_results=None, learnings=None) -> Strategy
```

**프롬프트 구조:**
```
당신은 온라인 쇼핑몰 세일즈 전략 설계 전문가입니다.

이번은 {iteration}번째 반복입니다.

## 이전 전략 결과 (최근 5개)
- 전략 S001: 평균 6.2점, 구매율: 35%, 매출: ₩3,493,000
  인사이트: ["리뷰 강조가 효과적", "가격 민감 고객 대응 부족"]

## 축적된 학습 내용 (최근 10개)
- 50대 이상은 GMP 인증 언급 시 신뢰도가 크게 올라감
- 가격 민감 고객에게 쿠폰 먼저 안내하면 이탈률 감소
...

## 응답 형식 (JSON)
{"name": "전략명", "approach": "...", "opening_style": "...",
 "persuasion_tactics": [...], "objection_handling": "...", "target_personas": [...]}
```

### 9.3 PLAN (`src/ralph/plan.py`)

```python
def select_personas(all_personas, count=20, focus_types=None) -> list[Persona]
```

`focus_types`는 `strategy.target_personas`에서 옵니다. 매칭되는 페르소나 우선 선택, 나머지 랜덤 채움.

### 9.4 ACT (`src/ralph/act.py`)

```python
async def execute_strategy(client, model, strategy, personas, ..., concurrency=50) -> list[ConversationSession]
```

- `asyncio.Semaphore(concurrency)`로 동시 실행 제어
- Sales Agent에 전략 주입
- Customer는 **RuleCustomerAgent** (비용 0)
- `asyncio.gather()`로 병렬 실행

### 9.5 EVALUATE (loop.py 내부)

```python
# 비용 절감: 200개 대화 중 30개만 샘플링
sample_size = min(30, len(sessions))
sample_sessions = random.sample(sessions, sample_size)

for session in sample_sessions:
    ev = await self.evaluator.evaluate(session)  # Sonnet 호출
```

나머지 170개는 구매/이탈 결과만 집계합니다.

### 9.6 REASON (`src/ralph/reason.py`)

```python
async def analyze_results(client, model, sessions, evaluations) -> dict
```

상위 3개 + 하위 3개 대화 전문을 LLM에 전달하여 패턴 분석:

```json
{
  "success_patterns": ["리뷰 기반 신뢰 구축이 효과적"],
  "failure_patterns": ["가격 먼저 안내 시 이탈 증가"],
  "persona_insights": ["50대: GMP 인증에 민감"],
  "tactical_observations": ["쿠폰 타이밍이 중요"],
  "improvement_suggestions": ["가격 민감 고객에 맞춤 오프닝 필요"]
}
```

### 9.7 LEARN (`src/ralph/learn.py`)

```python
async def extract_learnings(client, model, analysis, prior_learnings=None) -> list[str]
```

분석 결과에서 5~10개 학습 포인트를 추출합니다. 기존 학습과 중복되지 않는 새로운 인사이트를 우선합니다.

### 9.8 Persistent Loop (`src/ralph/persistent_loop.py`)

RALPHLoop을 상속하여 DB 저장 + 수렴 감지를 추가합니다:

```python
class PersistentRALPHLoop(RALPHLoop):
    # 수렴 감지: score 변화 < 5%가 2회 연속 → 수렴
    CONVERGENCE_THRESHOLD = 0.05
    CONVERGENCE_PATIENCE = 2

    # 수렴 시 탐색 주입: 반대 방향 학습 추가
    def _inject_exploration(self): ...
```

---

## 10. 데이터 저장소

### 10.1 DB 테이블 (`src/storage/models.py`)

| 테이블 | 주요 필드 |
|--------|----------|
| **ExperimentRecord** | experiment_id, product_name, total_iterations, config_snapshot |
| **ConversationRecord** | session_id, experiment_id, iteration, persona_id, transcript, termination_reason |
| **EvaluationRecord** | session_id, experiment_id, 5차원 점수, weighted_score, overall_summary |
| **StrategyRecord** | strategy_id, experiment_id, iteration, name, approach, persuasion_tactics(JSON) |
| **LearningRecord** | experiment_id, iteration, content |

### 10.2 Repository (`src/storage/repository.py`)

```python
class Repository:
    def save_experiment(experiment) -> None
    def save_conversation(session, experiment_id, iteration) -> None
    def save_evaluation(ev, experiment_id) -> None
    def save_strategy(strategy, experiment_id, avg_score) -> None
    def save_learnings(learnings, experiment_id, iteration) -> None
    def get_evaluations_by_experiment(experiment_id) -> list
    def get_strategies_by_experiment(experiment_id) -> list
```

---

## 11. API 엔드포인트

### 11.1 라우트 목록

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 프론트엔드 HTML 서빙 |
| GET | `/api/status` | 루프 실행 상태 |
| POST | `/api/sim/start` | 단일 대화 시뮬레이션 (SSE) |
| POST | `/api/loop/start` | RALPH Loop 시작 |
| GET | `/api/loop/stream` | 루프 진행 SSE 스트리밍 |
| POST | `/api/loop/stop` | 루프 중지 |
| GET | `/api/loop/analysis` | 통계 분석 결과 |

### 11.2 단일 대화 API (`POST /api/sim/start`)

**Request:**
```json
{"persona": {"id": "P001", "name": "손예나", "gen": "50대", "cat": "전자기기", ...}}
```

**SSE Events:**
```
data: {"type": "turn", "speaker": "sales", "content": "안녕하세요!", "turn_number": 1}
data: {"type": "turn", "speaker": "customer", "content": "네...", "turn_number": 2}
...
data: {"type": "eval_start"}
data: {"type": "eval_result", "interest_level": {"score": 7.5, "reasoning": "..."}, ..., "weighted_score": 6.8}
data: {"type": "done"}
```

### 11.3 RALPH Loop API (`POST /api/loop/start`)

**Request:**
```json
{
  "product_name": "VitaForest 올인원 데일리 멀티비타민",
  "product_category": "건강",
  "product_price": 49900,
  "product_description": "22종 비타민+미네랄...",
  "n_iterations": 5,
  "personas_count": 200
}
```

**SSE Events (GET /api/loop/stream):**
```
data: {"type": "iteration_start", "iteration": 1, "total": 5}
data: {"type": "iteration_end", "iteration": 1, "strategy_name": "신뢰 우선 접근",
       "strategy_approach": "...", "strategy_opening": "...",
       "strategy_tactics": [...], "strategy_objection": "...",
       "purchase_count": 45, "conversation_count": 200, "purchase_rate": 0.225,
       "total_revenue": 2245500, "learnings": [...], "analysis": {...}}
...
data: {"type": "done"}
```

---

## 12. 프론트엔드

### 12.1 구조

단일 HTML 파일 (`frontend/index.html`), vanilla JS, CSS 변수 기반 다크 테마.

**2개 탭:**

1. **쇼핑 시뮬레이션** — 단일 대화 테스트
   - 좌측: 페르소나 목록 + 상품 정보
   - 중앙: 채팅 UI (SSE 실시간)
   - 우측: 5차원 평가 + 인사이트

2. **RALPH Loop** — 전체 시뮬레이션
   - 통계 카드 (점수, 구매율, 매출, 전략명)
   - 차트 (구매 전환 스택바 + 누적 매출)
   - 반복 히스토리 (펼침식: 전략 상세, 분석 결과, 학습 포인트)

### 12.2 API 연결

```javascript
const API_BASE = window.location.origin;  // 서버와 같은 origin

// 단일 대화
const res = await fetch(`${API_BASE}/api/sim/start`, {method:'POST', body: ...});
const reader = res.body.getReader();  // SSE 스트리밍

// RALPH Loop
await fetch(`${API_BASE}/api/loop/start`, {method:'POST', body: ...});
eventSource = new EventSource(`${API_BASE}/api/loop/stream`);
```

---

## 13. 실행 방법

### 13.1 설치

```bash
pip install -e .
cp .env.example .env
# .env에 OPENROUTER_API_KEY 설정
```

### 13.2 웹 대시보드

```bash
PYTHONUTF8=1 python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
# 또는
python scripts/run_server.py
```

http://localhost:8000 접속

### 13.3 CLI 실행

```bash
# 단일 대화 테스트
python scripts/run_single_conversation.py

# RALPH Loop (5회 x 200명)
python scripts/run_simulation.py
```

---

## 14. 비용 추정

| 시나리오 | 비용 |
|----------|------|
| 단일 대화 테스트 | ~50원 |
| RALPH Loop 1회 (200명) | ~450원 |
| RALPH Loop 5회 (200명/회) | ~2,500원 |
| RALPH Loop 10회 (200명/회) | ~5,000원 |

비용의 75%는 EVALUATE 단계(Sonnet 30회/루프)에서 발생합니다.

---

## 15. 데이터 흐름 요약

```
[시작] .env에서 API키 + 모델 설정 로드
  │
  ▼
[HYPOTHESIZE] Sonnet에게 전략 생성 요청
  │            이전 결과 + 학습 내용 컨텍스트 제공
  │            → Strategy 객체 (name, approach, tactics, ...)
  │
  ▼
[PLAN] 200개 페르소나 풀에서 선택
  │    strategy.target_personas 우선, 나머지 랜덤
  │
  ▼
[ACT] 200개 대화 병렬 실행 (concurrency=10)
  │   Sales Agent (Gemini Flash + 전략 프롬프트)
  │   ↕ 턴 교대 (최대 16턴)
  │   Rule Customer (규칙 기반, $0)
  │   → 200개 ConversationSession
  │
  ▼
[EVALUATE] 30개 샘플 추출 → Sonnet으로 5차원 평가
  │         나머지 170개는 구매/이탈 결과만 집계
  │         → 30개 EvaluationResult + 전체 구매율/매출
  │
  ▼
[REASON] 상위 3 + 하위 3 대화 → Sonnet 패턴 분석
  │       → success_patterns, failure_patterns, improvements
  │
  ▼
[LEARN] 분석 결과 → Sonnet 학습 추출 (5~10개)
  │     기존 학습과 중복 제거
  │     → all_learnings에 추가
  │
  ▼
[다음 반복] all_learnings가 HYPOTHESIZE에 피드백
           → 전략이 점진적으로 개선됨
```
