"""기준선 매출 계산 (DB 실데이터 기반)"""

from src.csms.connection import get_csms_connection
from src.csms.queries import DATA_START_DATE, DATA_END_DATE, MONTHS_ELAPSED


def calculate_baseline_revenue() -> dict:
    """쿠폰 없는 현재 상태의 월평균 매출을 계산합니다."""
    conn = get_csms_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT CUT_ID) as active_users,
                SUM(FNL_PAY_SUM) as total_revenue,
                ROUND(SUM(FNL_PAY_SUM) / {MONTHS_ELAPSED}, 0) as monthly_revenue
            FROM TB_RCRC001
            WHERE CH_ST_DT >= '{DATA_START_DATE}'
                AND CH_ST_DT < '{DATA_END_DATE}'
                AND CUT_ID IS NOT NULL
                AND FNL_PAY_SUM > 0
        """)
        return cursor.fetchone()
    finally:
        conn.close()


def calculate_baseline_per_type() -> dict[str, dict]:
    """25유형별 기준선 매출을 계산합니다."""
    conn = get_csms_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                CONCAT(age_group, '_', freq_group) as type_key,
                user_count,
                avg_charge_amount,
                monthly_revenue
            FROM (
                SELECT
                    age_group, freq_group,
                    COUNT(*) as user_count,
                    ROUND(AVG(avg_pay), 0) as avg_charge_amount,
                    ROUND(SUM(total_pay) / {MONTHS_ELAPSED}, 0) as monthly_revenue
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
                        avg_pay,
                        total_pay
                    FROM (
                        SELECT CUT_ID, COUNT(*) as cnt,
                            AVG(FNL_PAY_SUM) as avg_pay,
                            SUM(FNL_PAY_SUM) as total_pay
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
            ) summary
            ORDER BY type_key
        """)
        rows = cursor.fetchall()
        return {
            row["type_key"]: {
                "user_count": row["user_count"],
                "avg_charge_amount": float(row["avg_charge_amount"]),
                "monthly_revenue": float(row["monthly_revenue"]),
            }
            for row in rows
        }
    finally:
        conn.close()
