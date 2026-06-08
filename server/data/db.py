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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            total_games INTEGER DEFAULT 0,
            total_wins INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
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


def get_random_questions(count: int = 3) -> list[Question]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
    conn.close()
    return [
        Question(
            id=row["id"], term=row["term"], real_definition=row["real_definition"],
            category=row["category"], source=row["source"], contributor_id=row["contributor_id"],
        )
        for row in rows
    ]


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


def create_user(username: str, password_hash: str) -> dict | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        uid = cursor.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def create_session(user_id: int, token: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO user_sessions (user_id, token) VALUES (?, ?)",
        (user_id, token),
    )
    conn.commit()
    conn.close()


def delete_session(token: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_user_by_token(token: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT u.* FROM users u JOIN user_sessions s ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def update_user_stats(user_id: int, score: int, is_winner: bool) -> None:
    conn = get_connection()
    if is_winner:
        conn.execute(
            "UPDATE users SET total_games = total_games + 1, total_score = total_score + ?, total_wins = total_wins + 1 WHERE id = ?",
            (score, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET total_games = total_games + 1, total_score = total_score + ? WHERE id = ?",
            (score, user_id),
        )
    conn.commit()
    conn.close()
