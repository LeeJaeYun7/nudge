from enum import Enum
from pydantic import BaseModel, Field


class Generation(str, Enum):
    TEEN = "teen"
    TWENTIES = "20s"
    THIRTIES = "30s"
    FORTIES = "40s"
    FIFTIES = "50s"
    SIXTIES_PLUS = "60plus"


class InterestCategory(str, Enum):
    FASHION = "fashion"
    ELECTRONICS = "electronics"
    FOOD = "food"
    HEALTH = "health"
    HOBBY = "hobby"
    HOME = "home"


class PurchaseTendency(str, Enum):
    IMPULSE = "impulse"
    DELIBERATE = "deliberate"
    BARGAIN_HUNTER = "bargain_hunter"
    BRAND_LOYAL = "brand_loyal"
    NEEDS_BASED = "needs_based"


class PriceSensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReactionPattern(str, Enum):
    FRIENDLY = "friendly"
    SKEPTICAL = "skeptical"
    IMPATIENT = "impatient"
    CURIOUS = "curious"
    DEFENSIVE = "defensive"


class InitialMood(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Persona(BaseModel):
    """고객 페르소나 정의"""

    id: str = Field(..., description="고유 식별자 (예: P001)")
    name: str = Field(..., description="페르소나 이름")
    generation: Generation
    interest_category: InterestCategory
    purchase_tendency: PurchaseTendency
    price_sensitivity: PriceSensitivity
    reaction_pattern: ReactionPattern
    initial_mood: InitialMood
    background: str = Field("", description="페르소나 배경 설명")
    speech_style: str = Field("", description="말투 특성 (예: 반말, 존댓말, 짧은 문장)")

    @property
    def summary(self) -> str:
        return (
            f"{self.name} ({self.generation.value}, {self.interest_category.value}) - "
            f"{self.purchase_tendency.value}, 가격민감도:{self.price_sensitivity.value}, "
            f"{self.reaction_pattern.value}, 기분:{self.initial_mood.value}"
        )
