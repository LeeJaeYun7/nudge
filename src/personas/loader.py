"""CSMS DB에서 실 유저 데이터 기반으로 페르소나를 생성합니다."""

import math

from src.csms.queries import get_type_distribution, get_user_samples
from src.personas.schema import AgeGroup, ChargingFrequency, EVPersona

AGE_GROUP_MAP = {
    "20대": AgeGroup.TWENTIES,
    "30대": AgeGroup.THIRTIES,
    "40대": AgeGroup.FORTIES,
    "50대": AgeGroup.FIFTIES,
    "60대+": AgeGroup.SIXTIES_PLUS,
}

FREQ_MAP = {
    "월1회미만": ChargingFrequency.LESS_THAN_1,
    "월1~2회": ChargingFrequency.ONE_TO_TWO,
    "월3~4회": ChargingFrequency.THREE_TO_FOUR,
    "월5~9회": ChargingFrequency.FIVE_TO_NINE,
    "월10회+": ChargingFrequency.TEN_PLUS,
}

MIN_PER_TYPE = 10


def generate_personas_from_db(target_count: int = 2000) -> list[EVPersona]:
    """DB 실 분포 비율대로 페르소나를 생성합니다.

    1. 25유형별 실 유저 수 조회
    2. 비율대로 target_count명 배분 (유형당 최소 MIN_PER_TYPE명)
    3. 각 유형에서 실 유저 레코드를 랜덤 샘플링
    """
    distribution = get_type_distribution()
    total_users = sum(row["user_count"] for row in distribution)

    # 비율 배분 (최소 보장)
    allocations = {}
    for row in distribution:
        type_key = f"{row['age_group']}_{row['freq_group']}"
        ratio = row["user_count"] / total_users
        alloc = max(MIN_PER_TYPE, math.floor(ratio * target_count))
        allocations[type_key] = {
            "count": alloc,
            "age_group": row["age_group"],
            "freq_group": row["freq_group"],
            "avg_charge_amount": float(row["avg_charge_amount"]),
            "avg_monthly_sessions": float(row["avg_monthly_sessions"]),
        }

    # 초과분 조정 (총합이 target_count에 맞도록)
    current_total = sum(a["count"] for a in allocations.values())
    if current_total > target_count:
        # 가장 많은 유형부터 줄임
        sorted_types = sorted(allocations, key=lambda k: allocations[k]["count"], reverse=True)
        for tk in sorted_types:
            if current_total <= target_count:
                break
            reduce = min(allocations[tk]["count"] - MIN_PER_TYPE, current_total - target_count)
            if reduce > 0:
                allocations[tk]["count"] -= reduce
                current_total -= reduce

    # DB에서 샘플링하여 페르소나 생성
    personas: list[EVPersona] = []
    for type_key, info in allocations.items():
        samples = get_user_samples(
            age_group=info["age_group"],
            freq_group=info["freq_group"],
            limit=info["count"],
        )
        for sample in samples:
            persona = EVPersona(
                id=sample["cut_id"],
                age_group=AGE_GROUP_MAP[info["age_group"]],
                charging_frequency=FREQ_MAP[info["freq_group"]],
                type_key=type_key,
                avg_charge_amount=float(sample["avg_charge_amount"]),
                avg_monthly_sessions=float(sample["monthly_sessions"]),
                car_name=sample.get("car_name") or "",
                gender=sample.get("gender") or "",
            )
            personas.append(persona)

    return personas
