from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine


def _ensure_db_directory(database_url: str) -> None:
    """Ensure the database directory exists for SQLite file-based DBs."""
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "", 1)
        parent_dir = Path(db_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)


def get_engine(database_url: str = "sqlite:///data/db/nudge.db"):
    _ensure_db_directory(database_url)
    return create_engine(database_url, echo=False)


def init_db(database_url: str = "sqlite:///data/db/nudge.db"):
    """데이터베이스 테이블을 생성합니다."""
    _ensure_db_directory(database_url)
    engine = get_engine(database_url)
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    return Session(engine)
