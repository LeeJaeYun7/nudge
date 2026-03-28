"""CSMS 정보계 DB 연결"""

import pymysql
from config.settings import get_settings


def get_csms_connection() -> pymysql.connections.Connection:
    settings = get_settings()
    return pymysql.connect(
        host=settings.csms_db_host,
        port=settings.csms_db_port,
        user=settings.csms_db_user,
        password=settings.csms_db_password,
        database=settings.csms_db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
