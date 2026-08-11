from app.core.config import get_settings
from app.db.init_db import seed_demo_client
from app.db.session import SessionLocal


def seed() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        seed_demo_client(db, settings)


if __name__ == "__main__":
    seed()
