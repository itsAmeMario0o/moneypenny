"""SQLite storage for Moneypenny.

Four tables:
  theses       one row per trading idea; each pipeline step fills in one JSON column
  runs         one row per TradingAgents run (its settings, verdict and reports)
  run_events   what each agent said during a run, in order (drives the live view)
  token_usage  one row per Claude call (or per model for a TradingAgents run)
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = os.environ.get("DESK_DB", "/data/moneypenny.db")

# These columns hold JSON text. We convert them to and from Python objects.
THESIS_JSON_COLUMNS = ["news", "analysis", "research", "strategy", "chart"]
RUN_JSON_COLUMNS = ["settings", "reports"]

# Only one thread may write at a time. Fine for a single user.
write_lock = threading.Lock()


def now_text():
    """Current UTC time as text, e.g. 2026-11-19T21:58:21+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row  # lets us read columns by name
    return connection


def run_write(sql, params=()):
    """Run an INSERT/UPDATE/DELETE and return the new row id (for INSERTs)."""
    with write_lock:
        connection = connect()
        cursor = connection.execute(sql, params)
        connection.commit()
        new_id = cursor.lastrowid
        connection.close()
    return new_id


def run_read(sql, params=()):
    """Run a SELECT and return a list of plain dictionaries."""
    connection = connect()
    rows = connection.execute(sql, params).fetchall()
    connection.close()
    result = []
    for row in rows:
        result.append(dict(row))
    return result


def create_tables():
    run_write("PRAGMA journal_mode=WAL")
    run_write("""
        CREATE TABLE IF NOT EXISTS theses (
            id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL,
            created TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            news TEXT, analysis TEXT, research TEXT, strategy TEXT, chart TEXT
        )""")
    run_write("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY,
            created TEXT NOT NULL,
            thesis_id INTEGER,
            run_id INTEGER,
            step TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL
        )""")


    run_write("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY,
            thesis_id INTEGER,
            ticker TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            created TEXT NOT NULL,
            finished TEXT,
            status TEXT NOT NULL,
            error TEXT,
            signal TEXT,
            settings TEXT, reports TEXT
        )""")
    run_write("""
        CREATE TABLE IF NOT EXISTS run_events (
            id INTEGER PRIMARY KEY,
            run_id INTEGER NOT NULL,
            created TEXT NOT NULL,
            agent TEXT NOT NULL,
            text TEXT NOT NULL
        )""")


def update_row(table, json_columns, row_id, fields):
    """Set the given columns on one row. Values for JSON columns are converted to text."""
    assignments = []
    values = []
    for column, value in fields.items():
        if column in json_columns:
            value = json.dumps(value)
        assignments.append(column + " = ?")
        values.append(value)
    values.append(row_id)
    run_write("UPDATE " + table + " SET " + ", ".join(assignments) + " WHERE id = ?", values)


def decode_row(row, json_columns):
    """Turn the JSON text columns back into Python objects."""
    for column in json_columns:
        if row[column]:
            row[column] = json.loads(row[column])
    return row


# ---------- theses ----------

def insert_thesis(ticker):
    return run_write(
        "INSERT INTO theses (ticker, created, status) VALUES (?, ?, ?)",
        (ticker, now_text(), "new"),
    )


def update_thesis(thesis_id, **fields):
    """Example: update_thesis(3, status="thesis", analysis={...})"""
    update_row("theses", THESIS_JSON_COLUMNS, thesis_id, fields)


def get_thesis(thesis_id):
    """Return one thesis as a dictionary, or None if it doesn't exist."""
    rows = run_read("SELECT * FROM theses WHERE id = ?", (thesis_id,))
    if len(rows) == 0:
        return None
    return decode_row(rows[0], THESIS_JSON_COLUMNS)


def list_theses():
    rows = run_read("SELECT * FROM theses ORDER BY id DESC")
    result = []
    for row in rows:
        result.append(decode_row(row, THESIS_JSON_COLUMNS))
    return result


# ---------- TradingAgents runs ----------

def insert_run(ticker, trade_date, settings, thesis_id):
    return run_write(
        "INSERT INTO runs (ticker, trade_date, created, status, settings, thesis_id) VALUES (?, ?, ?, ?, ?, ?)",
        (ticker, trade_date, now_text(), "running", json.dumps(settings), thesis_id),
    )


def update_run(run_id, **fields):
    update_row("runs", RUN_JSON_COLUMNS, run_id, fields)


def get_run(run_id):
    """Return one run as a dictionary, or None if it doesn't exist."""
    rows = run_read("SELECT * FROM runs WHERE id = ?", (run_id,))
    if len(rows) == 0:
        return None
    return decode_row(rows[0], RUN_JSON_COLUMNS)


def list_runs():
    rows = run_read("SELECT * FROM runs ORDER BY id DESC")
    result = []
    for row in rows:
        result.append(decode_row(row, RUN_JSON_COLUMNS))
    return result


def latest_run_id_for_thesis(thesis_id):
    rows = run_read("SELECT id FROM runs WHERE thesis_id = ? ORDER BY id DESC LIMIT 1", (thesis_id,))
    if len(rows) == 0:
        return None
    return rows[0]["id"]


def insert_run_event(run_id, agent, text):
    run_write(
        "INSERT INTO run_events (run_id, created, agent, text) VALUES (?, ?, ?, ?)",
        (run_id, now_text(), agent, text),
    )


def list_run_events(run_id):
    return run_read("SELECT * FROM run_events WHERE run_id = ? ORDER BY id", (run_id,))


def fail_interrupted_work():
    """A restart kills any running research. Mark those rows so the UI doesn't wait forever."""
    message = "Interrupted by a restart. Run it again."
    run_write("UPDATE runs SET status = 'error', error = ? WHERE status = 'running'", (message,))
    run_write("UPDATE theses SET status = 'error', error = ? WHERE status = 'researching'", (message,))


# ---------- token usage ----------

def record_usage(thesis_id, step, model, input_tokens, output_tokens, run_id=None):
    run_write(
        "INSERT INTO token_usage (created, thesis_id, run_id, step, model, input_tokens, output_tokens)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (now_text(), thesis_id, run_id, step, model, input_tokens, output_tokens),
    )


def list_usage():
    return run_read("SELECT * FROM token_usage ORDER BY id")
