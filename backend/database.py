import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "real_estate.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Database URL: defaults to local SQLite file, can be overridden by env variable
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    def get_db():
        """FastAPI dependency for yielding database sessions per request."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

except ImportError:
    # Graceful fallback when sqlalchemy is not installed in current environment
    engine = None
    SessionLocal = None
    Base = None

    def get_db():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def get_connection(db_file: str = DB_PATH) -> sqlite3.Connection:
    """Returns a native SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def run_sql_schema(schema_file: str = SCHEMA_PATH, db_file: str = DB_PATH):
    """Executes a pure SQL schema file directly against SQLite database."""
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found at {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        sql_script = f.read()

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()
    print(f"✅ Successfully created database '{db_file}' from '{schema_file}'!")


if __name__ == "__main__":
    print(f"🚀 Creating database '{DB_PATH}'...")
    run_sql_schema()
