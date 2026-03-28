from enum import Enum
from pydantic import BaseModel, Field


class AgeGroup(str, Enum):
    TWENTIES = "20대"
    THIRTIES = "30대"
    FORTIES = "40대"
    FIFTIES = "50대"
    SIXTIES_PLUS = "60대+"


class ChargingFrequency(str, Enum):
    LESS_THAN_1 = "월1회미만"
    ONE_TO_TWO = "월1~2회"
    THREE_TO_FOUR = "월3~4회"
    FIVE_TO_NINE = "월5~9회"
    TEN_PLUS = "월10회+"


class EVPersona(BaseModel):
    """전기차 충전 유저 페르소나"""

    id: str = Field(..., description="고유 식별자 (CUT_ID)")
    age_group: AgeGroup
    charging_frequency: ChargingFrequency
    type_key: str = Field(..., description="유형 키 (예: 30대_월3~4회)")
    avg_charge_amount: float = Field(..., description="평균 1회 충전금액 (원)")
    avg_monthly_sessions: float = Field(..., description="월평균 충전 횟수")
    car_name: str = Field("", description="차량명")
    gender: str = Field("", description="성별 (M/F)")

    @property
    def summary(self) -> str:
        return (
            f"{self.type_key} | "
            f"평균 ₩{self.avg_charge_amount:,.0f}/회 | "
            f"월 {self.avg_monthly_sessions:.1f}회 | "
            f"{self.car_name or '차종미상'}"
        )
