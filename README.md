# Nudge - Voice AI Sales Agent with RALPH Loop

고객 반응을 해석하고 실제로 더 잘 팔리는 설득 전략을 학습하는 AI Sales Agent 시스템.

## 핵심 아이디어

```
추천을 잘하는 AI ❌
설득 전략을 스스로 학습하는 AI ✅
```

Sales AI Agent가 200개 고객 페르소나와 대화하며, RALPH Loop를 통해 영업 전략을 자동으로 생성·실험·최적화합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  RALPH LOOP                      │
│                                                  │
│  HYPOTHESIZE ──→ PLAN ──→ ACT ──→ EVALUATE      │
│       ↑                              │           │
│       └──── LEARN ←── REASON ←───────┘           │
└─────────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    Sales Agent   Customer Agent  Evaluator
    (전략 실행)    (페르소나 반응)   (5차원 평가)
```

### RALPH Loop

| 단계 | 역할 |
|------|------|
| **H**ypothesize | 이전 학습 기반으로 새 영업 전략 가설 생성 |
| **P**lan | 실험할 페르소나 선택 및 실행 계획 |
| **A**ct | Sales↔Customer 대화 배치 실행 |
| **Evaluate** | 5차원 지표로 대화 평가 |
| **R**eason | 성공/실패 패턴 분석 |
| **L**earn | 재사용 가능한 학습 포인트 추출 |

### 5차원 평가 지표

| 지표 | 설명 | 가중치 |
|------|------|--------|
| 관심도 | 고객이 제품에 관심을 보였는가 | 20% |
| 대화 지속도 | 고객이 대화에 계속 참여했는가 | 15% |
| 감정 변화 | 고객의 감정이 긍정적으로 변화했는가 | 20% |
| 구매 의향 | 고객이 구매 의향을 표현했는가 | 25% |
| 최종 행동 결과 | 구매, 정보교환, 거절 등 최종 결과 | 20% |

## 프로젝트 구조

```
nudge/
├── config/                 # 설정 및 페르소나 정의
│   ├── settings.py         # 환경 설정 (Pydantic Settings)
│   ├── default.yaml        # 기본 설정값
│   └── personas.yaml       # 고객 페르소나 200개
│
├── src/
│   ├── agents/             # Sales/Customer AI Agent
│   │   ├── base.py         # 기반 에이전트 클래스
│   │   ├── sales_agent.py  # 판매 에이전트
│   │   ├── customer_agent.py # 고객 에이전트
│   │   └── prompts/        # 에이전트별 시스템 프롬프트
│   │
│   ├── personas/           # 페르소나 스키마 및 로더
│   ├── conversation/       # 대화 엔진 (턴 기반 오케스트레이션)
│   ├── evaluation/         # 다차원 평가 시스템
│   ├── ralph/              # RALPH Loop (핵심 최적화 루프)
│   ├── storage/            # 데이터 저장 (SQLModel)
│   ├── voice/              # Voice 인터페이스 (TTS/STT)
│   └── api/                # FastAPI 대시보드
│
├── scripts/                # 실행 스크립트
│   ├── run_single_conversation.py  # 단일 대화 테스트
│   └── run_simulation.py           # RALPH Loop 전체 실행
│
└── tests/                  # 테스트
```

## 빠른 시작

```bash
# 1. 의존성 설치
pip install -e .

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 입력

# 3. 단일 대화 테스트
python scripts/run_single_conversation.py

# 4. RALPH Loop 시뮬레이션
python scripts/run_simulation.py
```

## 기술 스택

- **LLM**: Claude API (Anthropic)
- **Backend**: Python 3.11+, FastAPI
- **Data**: Pydantic, SQLModel, SQLite
- **Voice** (예정): OpenAI TTS, Whisper STT
