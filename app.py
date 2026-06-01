import os
import sqlite3
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

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


def using_postgres():
    return bool(DATABASE_URL)


def get_db_connection():
    if using_postgres():
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            sslmode="require",
        )

    conn = sqlite3.connect("tickets.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    if using_postgres():
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id SERIAL PRIMARY KEY,
                date TEXT NOT NULL,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                ticket TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        cur.execute(
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

        columns = cur.execute("PRAGMA table_info(entries)").fetchall()
        column_names = [column["name"] for column in columns]

        if "completed" not in column_names:
            cur.execute(
                """
                ALTER TABLE entries
                ADD COLUMN completed INTEGER NOT NULL DEFAULT 0
                """
            )

    conn.commit()
    cur.close()
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
        cur = conn.cursor()

        if using_postgres():
            cur.execute(
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    datetime.utcnow(),
                ),
            )
        else:
            cur.execute(
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
        cur.close()
        conn.close()

        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor()

    if using_postgres():
        cur.execute(
            """
            SELECT *
            FROM entries
            ORDER BY created_at DESC
            """
        )
    else:
        cur.execute(
            """
            SELECT *
            FROM entries
            ORDER BY datetime(created_at) DESC
            """
        )

    entries = cur.fetchall()

    cur.close()
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
    cur = conn.cursor()

    if using_postgres():
        cur.execute(
            """
            UPDATE entries
            SET completed = 1
            WHERE id = %s
            """,
            (entry_id,),
        )
    else:
        cur.execute(
            """
            UPDATE entries
            SET completed = 1
            WHERE id = ?
            """,
            (entry_id,),
        )

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("index"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete_entry(entry_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if using_postgres():
        cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
    else:
        cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)


init_db()