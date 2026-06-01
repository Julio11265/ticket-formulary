import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DATABASE_PATH = os.environ.get("DATABASE_PATH", "tickets.db")

STATUS_OPTIONS = [
    "Investigation to continue",
    "Awaiting business response",
    "Pending approval",
    "Other",
]

LOCATION_OPTIONS = [
    "Bogota",
    "Iași",
]


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn, table_name, column_name):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def init_db():
    conn = get_db_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            ticket TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    if not column_exists(conn, "entries", "completed"):
        conn.execute(
            """
            ALTER TABLE entries
            ADD COLUMN completed INTEGER NOT NULL DEFAULT 0
            """
        )

    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        date = request.form.get("date")
        name = request.form.get("name")
        location = request.form.get("location")
        ticket = request.form.get("ticket")
        priority = request.form.get("priority")
        status = request.form.get("status")
        notes = request.form.get("notes")

        if location not in LOCATION_OPTIONS:
            location = "Bogota"

        if status not in STATUS_OPTIONS:
            status = "Other"

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO entries (
                date,
                name,
                location,
                ticket,
                priority,
                status,
                notes,
                completed,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                name,
                location,
                ticket,
                priority,
                status,
                notes,
                0,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    conn = get_db_connection()
    entries = conn.execute(
        """
        SELECT *
        FROM entries
        ORDER BY datetime(created_at) DESC
        """
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        entries=entries,
        status_options=STATUS_OPTIONS,
        location_options=LOCATION_OPTIONS,
    )


@app.route("/complete/<int:entry_id>", methods=["POST"])
def complete_entry(entry_id):
    conn = get_db_connection()
    conn.execute(
        """
        UPDATE entries
        SET completed = 1
        WHERE id = ?
        """,
        (entry_id,),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete_entry(entry_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)


init_db()