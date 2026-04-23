from sqlalchemy import text

from app.database import SessionLocal


def test_database_session_can_execute_simple_query() -> None:
    with SessionLocal() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1
