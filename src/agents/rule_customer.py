"""규칙 기반 고객 에이전트 — LLM 호출 없이 페르소나 특성에 따라 응답을 생성합니다."""

import random
from src.conversation.turn import Turn
from src.personas.schema import Persona


# === 응답 템플릿 풀 ===

GREETINGS_POSITIVE = [
    "네 안녕하세요~",
    "안녕하세요 ㅎㅎ",
    "네! 좀 둘러보는 중이에요.",
]
GREETINGS_NEUTRAL = [
    "네...",
    "그냥 보는 중이에요.",
    "아 네.",
]
GREETINGS_NEGATIVE = [
    "...",
    "그냥 보는 거예요.",
    "네. 괜찮아요.",
]

INTEREST_QUESTIONS = [
    "오 그래요? 좀 더 설명해주세요.",
    "후기는 어때요?",
    "하루에 몇 포 먹어야 돼요?",
    "어떤 성분이 들어가 있어요?",
    "효과 체감하려면 얼마나 먹어야 해요?",
    "부작용 같은 건 없어요?",
    "실제 먹어본 사람 후기가 궁금해요.",
    "GMP 인증은 어디서 받은 거예요?",
    "다른 영양제랑 같이 먹어도 돼요?",
]

PRICE_REACTIONS_POSITIVE = [
    "오 그 가격이면 괜찮네요!",
    "할인까지 하면 꽤 괜찮은데요?",
    "가성비 좋네요!",
    "약국 영양제보다 저렴하면서 성분은 더 좋네요.",
]
PRICE_REACTIONS_NEUTRAL = [
    "음... 좀 고민되네요.",
    "가격이 조금 부담되긴 하는데...",
    "약국에서 파는 거랑 비교하면 어때요?",
    "할인이나 쿠폰 있어요?",
]
PRICE_REACTIONS_NEGATIVE = [
    "너무 비싸네요.",
    "이 가격은 좀...",
    "쿠팡에 더 싼 거 많던데.",
    "5만원은 좀 많다...",
]

REVIEW_REACTIONS = [
    "후기가 좋네요!",
    "리뷰 보니까 괜찮아 보이네요.",
    "평점이 꽤 높네요.",
    "오 4.7점이면 좋은 거네.",
]

OBJECTION_BRAND = [
    "센트룸 먹고 있는데 굳이 바꿀 필요가 있을까요?",
    "종근당이 더 믿을 만하지 않아요?",
    "브랜드가 좀 생소한데...",
]
OBJECTION_NEED = [
    "지금 먹는 것도 괜찮은데...",
    "꼭 필요한 건 아닌 것 같아요.",
    "좀 더 생각해볼게요.",
]

PURCHASE_POSITIVE = [
    "좋아요, 장바구니 담을게요!",
    "이걸로 결제할게요!",
    "네 이걸로 할게요. 바로 결제할게요!",
    "오케이, 살게요!",
    "장바구니 담고 바로 결제할게요.",
]
PURCHASE_HESITANT = [
    "일단 찜해둘게요.",
    "좀 더 생각해볼게요.",
    "나중에 다시 올게요.",
    "위시리스트에 담아둘게요.",
]
EXIT_LINES = [
    "됐어요. 필요 없어요.",
    "아 괜찮아요. 나갈게요.",
    "안 살게요.",
    "다른 데 좀 더 볼게요.",
]

COUPON_REACTIONS = [
    "오 쿠폰이요? 얼마나 할인돼요?",
    "쿠폰 적용하면 얼마예요?",
    "할인 쿠폰 좋네요!",
]

SHIPPING_REACTIONS = [
    "내일 도착이요? 빠르네요!",
    "무료배송이면 좋죠~",
    "오 배송 빠르네요.",
]


class RuleCustomerAgent:
    """규칙 기반 고객 에이전트.

    페르소나 속성에 따라 상태 머신 기반으로 응답을 생성합니다.
    LLM 호출이 없어 비용 0, 지연 시간도 거의 없습니다.
    """

    def __init__(self, persona: Persona):
        self.persona = persona
        self.interest = self._initial_interest()
        self.mood = self._initial_mood_score()
        self.turn_count = 0
        self.heard_price = False
        self.heard_review = False
        self.heard_coupon = False
        self.heard_shipping = False

    @property
    def role(self) -> str:
        return "customer"

    def _initial_interest(self) -> float:
        """페르소나 기반 초기 관심도 (0~10)"""
        base = {
            "curious": 5, "friendly": 4, "skeptical": 3,
            "impatient": 3, "defensive": 2,
        }
        return float(base.get(self.persona.reaction_pattern.value, 3))

    def _initial_mood_score(self) -> float:
        """페르소나 기반 초기 감정 (-5 ~ +5)"""
        base = {"positive": 2, "neutral": 0, "negative": -2}
        return float(base.get(self.persona.initial_mood.value, 0))

    def _purchase_threshold(self) -> float:
        """구매 결정을 위한 관심도 임계값"""
        base = {
            "impulse": 6.0,
            "deliberate": 8.0,
            "bargain_hunter": 7.0,
            "brand_loyal": 8.5,
            "needs_based": 7.5,
        }
        threshold = base.get(self.persona.purchase_tendency.value, 7.0)
        # 가격 민감도에 따라 조절
        if self.persona.price_sensitivity.value == "high":
            threshold += 1.0
        elif self.persona.price_sensitivity.value == "low":
            threshold -= 1.0
        return threshold

    def _analyze_sales_message(self, msg: str) -> dict:
        """판매 메시지에서 키워드를 분석합니다."""
        return {
            "mentions_price": any(w in msg for w in ["원", "할인", "가격", "쿠폰", "세일", "프로모션"]),
            "mentions_review": any(w in msg for w in ["리뷰", "후기", "평점", "별점", "평가"]),
            "mentions_spec": any(w in msg for w in ["비타민", "미네랄", "프로바이오틱스", "루테인", "오메가", "GMP", "성분", "함량"]),
            "mentions_benefit": any(w in msg for w in ["무료배송", "증정", "적립", "혜택", "이벤트", "면역", "피로", "에너지", "활력"]),
            "mentions_coupon": any(w in msg for w in ["쿠폰", "할인코드", "첫 구매"]),
            "mentions_shipping": any(w in msg for w in ["배송", "도착", "출발", "당일", "내일"]),
            "mentions_compare": any(w in msg for w in ["센트룸", "종근당", "솔가", "약국", "비교"]),
            "is_question": "?" in msg or "요?" in msg or "세요" in msg,
            "is_empathetic": any(w in msg for w in ["그렇죠", "맞아요", "이해", "공감", "고민"]),
            "is_pushy": any(w in msg for w in ["지금 바로", "서두르", "놓치", "마지막"]),
        }

    def _update_state(self, analysis: dict):
        """판매 메시지 분석 결과에 따라 상태를 업데이트합니다."""
        # 관심도 변화
        if analysis["mentions_spec"]:
            self.interest += random.uniform(0.3, 0.8)
        if analysis["mentions_review"] and not self.heard_review:
            self.interest += random.uniform(0.5, 1.2)
            self.heard_review = True
        if analysis["mentions_coupon"] and not self.heard_coupon:
            self.interest += random.uniform(0.5, 1.0)
            self.heard_coupon = True
        if analysis["mentions_shipping"] and not self.heard_shipping:
            self.interest += random.uniform(0.2, 0.5)
            self.heard_shipping = True
        if analysis["mentions_compare"]:
            self.interest += random.uniform(0.2, 0.6)
        if analysis["is_empathetic"]:
            self.mood += random.uniform(0.3, 0.8)
            self.interest += random.uniform(0.1, 0.3)
        if analysis["is_pushy"]:
            self.mood -= random.uniform(0.3, 1.0)
            if self.persona.reaction_pattern.value == "defensive":
                self.interest -= random.uniform(0.5, 1.5)

        # 가격 언급 시
        if analysis["mentions_price"] and not self.heard_price:
            self.heard_price = True
            if self.persona.price_sensitivity.value == "high":
                self.interest -= random.uniform(0.3, 0.8)
            elif self.persona.price_sensitivity.value == "low":
                self.interest += random.uniform(0.1, 0.5)

        # 자연적 관심 감소 (턴이 길어질수록)
        if self.turn_count > 6:
            self.interest -= random.uniform(0, 0.3)

        # 범위 제한
        self.interest = max(0, min(10, self.interest))
        self.mood = max(-5, min(5, self.mood))

    async def respond(self, conversation_history: list[Turn]) -> str:
        """대화 이력 기반으로 규칙 기반 응답을 생성합니다."""
        self.turn_count += 1

        # 마지막 판매원 메시지 분석
        last_sales = ""
        for turn in reversed(conversation_history):
            if turn.speaker == "sales":
                last_sales = turn.content
                break

        analysis = self._analyze_sales_message(last_sales)
        self._update_state(analysis)

        # === 응답 결정 로직 ===

        # 첫 턴: 인사 반응
        if self.turn_count == 1:
            if self.mood > 0:
                return random.choice(GREETINGS_POSITIVE)
            elif self.mood < -1:
                return random.choice(GREETINGS_NEGATIVE)
            return random.choice(GREETINGS_NEUTRAL)

        # 방어적 고객 + 낮은 관심 = 빠른 이탈
        if self.persona.reaction_pattern.value == "defensive" and self.interest < 3 and self.turn_count >= 3:
            return random.choice(EXIT_LINES)

        # 급한 성격 + 관심 낮으면 빠른 이탈
        if self.persona.reaction_pattern.value == "impatient" and self.interest < 4 and self.turn_count >= 4:
            return random.choice(EXIT_LINES)

        # 쿠폰 반응
        if analysis["mentions_coupon"] and not self.heard_coupon:
            self.heard_coupon = True
            return random.choice(COUPON_REACTIONS)

        # 배송 반응
        if analysis["mentions_shipping"] and self.interest > 5:
            return random.choice(SHIPPING_REACTIONS)

        # 리뷰 반응
        if analysis["mentions_review"] and self.interest > 4:
            return random.choice(REVIEW_REACTIONS)

        # 가격 언급 시 반응
        if analysis["mentions_price"]:
            if self.persona.price_sensitivity.value == "high":
                return random.choice(PRICE_REACTIONS_NEGATIVE)
            elif self.persona.price_sensitivity.value == "low":
                return random.choice(PRICE_REACTIONS_POSITIVE)
            return random.choice(PRICE_REACTIONS_NEUTRAL)

        # 구매 결정 시점
        if self.interest >= self._purchase_threshold() and self.turn_count >= 4:
            if self.mood >= 0:
                return random.choice(PURCHASE_POSITIVE)
            else:
                return random.choice(PURCHASE_HESITANT)

        # 관심도가 일정 이상이면 질문
        if self.interest > 4 and analysis["is_question"]:
            return random.choice(INTEREST_QUESTIONS)

        # 브랜드 충성 고객은 비교 질문
        if self.persona.purchase_tendency.value == "brand_loyal" and self.turn_count <= 4:
            return random.choice(OBJECTION_BRAND)

        # 필요기반 고객은 필요성 의문
        if self.persona.purchase_tendency.value == "needs_based" and self.interest < 6:
            return random.choice(OBJECTION_NEED)

        # 턴이 많아지면 결정 압박
        if self.turn_count >= 7:
            if self.interest >= self._purchase_threshold() - 1:
                return random.choice(PURCHASE_POSITIVE)
            else:
                return random.choice(PURCHASE_HESITANT)

        # 관심도에 따른 일반 반응
        if self.interest > 5:
            return random.choice(INTEREST_QUESTIONS)
        elif self.interest > 3:
            pool = PRICE_REACTIONS_NEUTRAL + OBJECTION_NEED
            return random.choice(pool)
        else:
            return random.choice(EXIT_LINES)
