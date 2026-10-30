import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from mitro.db import Base, CodeChangeProposal

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
(DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
load_dotenv(ROOT / ".env")
DB_URL = os.getenv("MITRO_DATABASE_URL", f"sqlite:///{(DATA_DIR / 'mitro.db').as_posix()}")
opts = {"connect_args": {"check_same_thread": False}} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, **opts)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)
# Small additive SQLite migrations keep existing local demo databases usable.
if engine.dialect.name == "sqlite" and inspect(engine).has_table(CodeChangeProposal.__tablename__):
    existing_columns = {c["name"] for c in inspect(engine).get_columns(CodeChangeProposal.__tablename__)}
    with engine.begin() as conn:
        for column in CodeChangeProposal.__table__.columns:
            if column.name in existing_columns:
                continue
            sql_type = column.type.compile(dialect=engine.dialect)
            default = " DEFAULT ''" if column.name in {"source_citation", "source_identifier", "source_url", "source_sha256"} else ""
            conn.exec_driver_sql(f"ALTER TABLE {CodeChangeProposal.__tablename__} ADD COLUMN {column.name} {sql_type}{default}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



