"""CSMS DB에서 유저/충전 데이터를 조회하는 쿼리"""

from src.csms.connection import get_csms_connection

# 2026.01.01 기준, 경과 일수로 월평균 산출
DATA_START_DATE = "2026-01-01"
DATA_END_DATE = "2026-03-10"
MONTHS_ELAPSED = 68 / 30.0  # 약 2.27개월


def get_type_distribution() -> list[dict]:
    """25유형(연령대 x 충전빈도)별 유저 수, 평균 충전금액, 월평균 충전횟수를 조회합니다."""
    conn = get_csms_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT age_group, freq_group,
                COUNT(*) as user_count,
                ROUND(AVG(avg_pay), 0) as avg_charge_amount,
                ROUND(AVG(monthly_avg), 1) as avg_monthly_sessions
            FROM (
                SELECT
                    r.CUT_ID,
                    CASE
                        WHEN LEFT(u.BIRTHDAY, 4) >= '2000' THEN '20대'
                        WHEN LEFT(u.BIRTHDAY, 4) >= '1990' THEN '30대'
                        WHEN LEFT(u.BIRTHDAY, 4) >= '1980' THEN '40대'
                        WHEN LEFT(u.BIRTHDAY, 4) >= '1970' THEN '50대'
                        ELSE '60대+'
                    END as age_group,
                    CASE
                        WHEN cnt / {MONTHS_ELAPSED} < 1 THEN '월1회미만'
                        WHEN cnt / {MONTHS_ELAPSED} < 3 THEN '월1~2회'
                        WHEN cnt / {MONTHS_ELAPSED} < 5 THEN '월3~4회'
                        WHEN cnt / {MONTHS_ELAPSED} < 10 THEN '월5~9회'
                        ELSE '월10회+'
                    END as freq_group,
                    cnt / {MONTHS_ELAPSED} as monthly_avg,
                    avg_pay
                FROM (
                    SELECT CUT_ID, COUNT(*) as cnt, AVG(FNL_PAY_SUM) as avg_pay
                    FROM TB_RCRC001
                    WHERE CH_ST_DT >= '{DATA_START_DATE}'
                        AND CH_ST_DT < '{DATA_END_DATE}'
                        AND CUT_ID IS NOT NULL
                        AND FNL_PAY_SUM > 0
                    GROUP BY CUT_ID
                ) r
                JOIN TB_CUCU001 u ON r.CUT_ID = u.CUT_ID
                WHERE u.BIRTHDAY IS NOT NULL AND u.BIRTHDAY != ''
            ) t
            GROUP BY age_group, freq_group
            ORDER BY age_group, freq_group
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def get_user_samples(age_group: str, freq_group: str, limit: int) -> list[dict]:
    """특정 유형의 실제 유저 레코드를 샘플링합니다."""
    age_conditions = {
        "20대": "LEFT(u.BIRTHDAY, 4) >= '2000'",
        "30대": "LEFT(u.BIRTHDAY, 4) >= '1990' AND LEFT(u.BIRTHDAY, 4) < '2000'",
        "40대": "LEFT(u.BIRTHDAY, 4) >= '1980' AND LEFT(u.BIRTHDAY, 4) < '1990'",
        "50대": "LEFT(u.BIRTHDAY, 4) >= '1970' AND LEFT(u.BIRTHDAY, 4) < '1980'",
        "60대+": "LEFT(u.BIRTHDAY, 4) < '1970'",
    }
    freq_conditions = {
        "월1회미만": f"cnt / {MONTHS_ELAPSED} < 1",
        "월1~2회": f"cnt / {MONTHS_ELAPSED} >= 1 AND cnt / {MONTHS_ELAPSED} < 3",
        "월3~4회": f"cnt / {MONTHS_ELAPSED} >= 3 AND cnt / {MONTHS_ELAPSED} < 5",
        "월5~9회": f"cnt / {MONTHS_ELAPSED} >= 5 AND cnt / {MONTHS_ELAPSED} < 10",
        "월10회+": f"cnt / {MONTHS_ELAPSED} >= 10",
    }

    age_cond = age_conditions[age_group]
    freq_cond = freq_conditions[freq_group]

    conn = get_csms_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                r.CUT_ID as cut_id,
                u.GND as gender,
                u.CAR_NM as car_name,
                r.avg_pay as avg_charge_amount,
                r.cnt / {MONTHS_ELAPSED} as monthly_sessions
            FROM (
                SELECT CUT_ID, COUNT(*) as cnt, AVG(FNL_PAY_SUM) as avg_pay
                FROM TB_RCRC001
                WHERE CH_ST_DT >= '{DATA_START_DATE}'
                    AND CH_ST_DT < '{DATA_END_DATE}'
                    AND CUT_ID IS NOT NULL
                    AND FNL_PAY_SUM > 0
                GROUP BY CUT_ID
            ) r
            JOIN TB_CUCU001 u ON r.CUT_ID = u.CUT_ID
            WHERE u.BIRTHDAY IS NOT NULL AND u.BIRTHDAY != ''
                AND {age_cond}
                AND {freq_cond}
            ORDER BY RAND()
            LIMIT {limit}
        """)
        return cursor.fetchall()
    finally:
        conn.close()
