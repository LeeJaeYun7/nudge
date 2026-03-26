from sqlmodel import SQLModel, create_engine, Session


def get_engine(database_url: str = "sqlite:///data/db/nudge.db"):
    return create_engine(database_url, echo=False)


def init_db(database_url: str = "sqlite:///data/db/nudge.db"):
    """데이터베이스 테이블을 생성합니다."""
    engine = get_engine(database_url)
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    return Session(engine)
