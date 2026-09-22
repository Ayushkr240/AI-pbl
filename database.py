import sqlite3

conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations(
    thread_id TEXT PRIMARY KEY,
    title TEXT NOT NULL
)
""")

conn.commit()


def create_thread(thread_id, title="New Chat"):
    cursor.execute(
        """
        INSERT OR IGNORE INTO conversations(thread_id, title)
        VALUES(?, ?)
        """,
        (thread_id, title),
    )
    conn.commit()


def get_all_threads():
    cursor.execute(
        """
        SELECT thread_id, title
        FROM conversations
        ORDER BY rowid DESC
        """
    )

    rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
        }
        for row in rows
    ]


def rename_thread(thread_id, title):
    cursor.execute(
        """
        UPDATE conversations
        SET title=?
        WHERE thread_id=?
        """,
        (title, thread_id),
    )
    conn.commit()


def delete_thread(thread_id):
    cursor.execute(
        """
        DELETE FROM conversations
        WHERE thread_id=?
        """,
        (thread_id,),
    )
    conn.commit()