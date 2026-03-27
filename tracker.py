import argparse
import sqlite3
from datetime import datetime

DB_PATH = "tracker.db"


def init_db():
    """Initialize the tracker database and create the requests table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            broker_name     TEXT NOT NULL UNIQUE,
            removal_type    TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            submitted_at    TEXT,
            completed_at    TEXT,
            notes           TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_broker(broker_name: str, removal_type: str):
    """Insert a broker row if it doesn't exist yet."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO requests (broker_name, removal_type)
            VALUES (?, ?)
        """, (broker_name, removal_type))


def set_status(broker_name: str, status: str, notes: str = None):
    """Update the status of a broker request."""
    now = datetime.utcnow().isoformat()
    if status == "sent":
        with get_connection() as conn:
            conn.execute("""
                UPDATE requests
                SET status = ?, submitted_at = ?, notes = COALESCE(?, notes)
                WHERE broker_name = ?
            """, (status, now, notes, broker_name))
    elif status == "done":
        with get_connection() as conn:
            conn.execute("""
                UPDATE requests
                SET status = ?, completed_at = ?, notes = COALESCE(?, notes)
                WHERE broker_name = ?
            """, (status, now, notes, broker_name))
    else:
        with get_connection() as conn:
            conn.execute("""
                UPDATE requests
                SET status = ?, notes = COALESCE(?, notes)
                WHERE broker_name = ?
            """, (status, notes, broker_name))


def get_all():
    """Return all broker requests."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM requests ORDER BY broker_name").fetchall()
    return [dict(row) for row in rows]


def get_pending():
    """Return brokers that have not yet been contacted (status = pending)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM requests WHERE status = 'pending' ORDER BY broker_name"
        ).fetchall()
    return [dict(row) for row in rows]


def print_summary():
    """Print a summary table of all request statuses."""
    rows = get_all()
    if not rows:
        print("No brokers tracked yet.")
        return

    print(f"\n{'Broker':<25} {'Type':<8} {'Status':<10} {'Submitted':<22} {'Completed'}")
    print("-" * 85)
    for r in rows:
        print(
            f"{r['broker_name']:<25} "
            f"{r['removal_type']:<8} "
            f"{r['status']:<10} "
            f"{(r['submitted_at'] or '-'):<22} "
            f"{r['completed_at'] or '-'}"
        )
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually update broker request statuses.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true", help="Print status of all brokers")
    group.add_argument("--mark-done", metavar="BROKER", help="Mark a broker as done")
    group.add_argument("--mark-failed", metavar="BROKER", help="Mark a broker as failed")
    group.add_argument("--mark-action", metavar="BROKER", help="Mark a broker as needs_action")
    parser.add_argument("note", nargs="?", default=None, help="Optional note to attach")
    args = parser.parse_args()

    if args.summary:
        print_summary()
    elif args.mark_done:
        set_status(args.mark_done, "done", args.note)
        print(f"Marked '{args.mark_done}' as done.")
    elif args.mark_failed:
        set_status(args.mark_failed, "failed", args.note)
        print(f"Marked '{args.mark_failed}' as failed.")
    elif args.mark_action:
        set_status(args.mark_action, "needs_action", args.note)
        print(f"Marked '{args.mark_action}' as needs_action.")
