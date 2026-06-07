import sqlite3
import time

DB_PATH = "bot_data.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                guild_id TEXT,
                user_id TEXT,
                username TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS voice_sessions (
                guild_id TEXT,
                user_id TEXT,
                username TEXT,
                join_time REAL,
                total_seconds REAL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        conn.commit()


def increment_messages(guild_id, user_id, username):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO messages (guild_id, user_id, username, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                count = count + 1,
                username = excluded.username
        """,
            (str(guild_id), str(user_id), username),
        )
        conn.commit()


def record_voice_join(guild_id, user_id, username):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO voice_sessions (guild_id, user_id, username, join_time, total_seconds)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                join_time = excluded.join_time,
                username = excluded.username
        """,
            (str(guild_id), str(user_id), username, time.time()),
        )
        conn.commit()


def record_voice_leave(guild_id, user_id):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT join_time, total_seconds FROM voice_sessions
            WHERE guild_id = ? AND user_id = ?
        """,
            (str(guild_id), str(user_id)),
        ).fetchone()
        if row and row[0] is not None:
            elapsed = time.time() - row[0]
            conn.execute(
                """
                UPDATE voice_sessions
                SET total_seconds = total_seconds + ?, join_time = NULL
                WHERE guild_id = ? AND user_id = ?
            """,
                (elapsed, str(guild_id), str(user_id)),
            )
            conn.commit()


def get_top_messages(guild_id, limit=5):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT username, count FROM messages
            WHERE guild_id = ?
            ORDER BY count DESC
            LIMIT ?
        """,
            (str(guild_id), limit),
        ).fetchall()


def get_top_voice(guild_id, limit=5):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT username, total_seconds FROM voice_sessions
            WHERE guild_id = ?
            ORDER BY total_seconds DESC
            LIMIT ?
        """,
            (str(guild_id), limit),
        ).fetchall()
