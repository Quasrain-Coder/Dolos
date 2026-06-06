import sqlite3
import json
import random
from pathlib import Path
from server.models.question import Question

DATA_DIR = Path(__file__).parent
DB_PATH = DATA_DIR / "dolos.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            real_definition TEXT NOT NULL,
            category TEXT DEFAULT '通用',
            source TEXT DEFAULT 'builtin',
            contributor_id TEXT
        )
    """)
    conn.commit()

    # Import built-in questions if table is empty
    count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    if count == 0:
        _import_builtin_questions(conn)

    conn.close()


def _import_builtin_questions(conn: sqlite3.Connection):
    json_path = DATA_DIR / "questions.json"
    if not json_path.exists():
        print(f"Warning: {json_path} not found, skipping import")
        return
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    for q in questions:
        conn.execute(
            "INSERT INTO questions (term, real_definition, category, source) VALUES (?, ?, ?, 'builtin')",
            (q["term"], q["definition"], q.get("category", "通用")),
        )
    conn.commit()
    print(f"Imported {len(questions)} built-in questions")


def get_random_question() -> Question | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    if row is None:
        return None
    return Question(
        id=row["id"],
        term=row["term"],
        real_definition=row["real_definition"],
        category=row["category"],
        source=row["source"],
        contributor_id=row["contributor_id"],
    )


def add_question(term: str, definition: str, category: str = "通用", contributor_id: str | None = None) -> Question:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO questions (term, real_definition, category, source, contributor_id) VALUES (?, ?, ?, 'player', ?)",
        (term, definition, category, contributor_id),
    )
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return Question(id=qid, term=term, real_definition=definition, category=category, source="player", contributor_id=contributor_id)


def get_question_by_id(qid: int) -> Question | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    conn.close()
    if row is None:
        return None
    return Question(
        id=row["id"], term=row["term"], real_definition=row["real_definition"],
        category=row["category"], source=row["source"], contributor_id=row["contributor_id"],
    )


def get_question_count() -> int:
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    conn.close()
    return count
