"""
db.py - SQLite persistence for BMI records (advanced tier).

Schema
    users(id, name UNIQUE, created_at)
    records(id, user_id -> users.id, weight_kg, height_m, bmi,
            category, recorded_at)

Every public function raises StorageError with a readable message when the
database cannot be read or written, so both the CLI and the GUI can show the
user something meaningful instead of a traceback.
"""

import os
import sqlite3
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmi_records.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weight_kg   REAL NOT NULL,
    height_m    REAL NOT NULL,
    bmi         REAL NOT NULL,
    category    TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_records_user_time
    ON records (user_id, recorded_at);
"""


class StorageError(RuntimeError):
    """Raised when the record store cannot be opened, read or written."""


class BMIDatabase:
    """Thin wrapper around a SQLite file holding users and their BMI history."""

    def __init__(self, path=DEFAULT_DB_PATH):
        self.path = path
        self.conn = None

    # ---------------------------------------------------------------- setup

    def connect(self):
        """Open the database and create the tables if needed."""
        try:
            self.conn = sqlite3.connect(self.path)
            self.conn.row_factory = sqlite3.Row
            # ON DELETE CASCADE needs foreign keys switched on per connection.
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        except sqlite3.Error as error:
            raise StorageError(f"Could not open the database at {self.path}: {error}") from error
        except OSError as error:
            raise StorageError(f"Could not access {self.path}: {error}") from error
        return self

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass
            self.conn = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def _require_connection(self):
        if self.conn is None:
            raise StorageError("The database is not open. Call connect() first.")

    # ---------------------------------------------------------------- users

    def add_user(self, name):
        """Insert a user and return their id; return the existing id if present."""
        self._require_connection()
        clean = (name or "").strip()
        if not clean:
            raise StorageError("A user name is required.")

        try:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO users (name, created_at) VALUES (?, ?)",
                (clean, datetime.now().isoformat(timespec="seconds")),
            )
            self.conn.commit()
            if cursor.rowcount:
                return cursor.lastrowid
            row = self.conn.execute("SELECT id FROM users WHERE name = ?", (clean,)).fetchone()
            if row is None:
                raise StorageError(f"User '{clean}' could not be created.")
            return row["id"]
        except sqlite3.Error as error:
            raise StorageError(f"Could not save the user '{clean}': {error}") from error

    def get_users(self):
        """Return every user as a list of dicts, ordered by name."""
        self._require_connection()
        try:
            rows = self.conn.execute("SELECT id, name, created_at FROM users ORDER BY name").fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise StorageError(f"Could not read the user list: {error}") from error

    def get_user_id(self, name):
        """Return the id for a name, or None when the user does not exist."""
        self._require_connection()
        try:
            row = self.conn.execute(
                "SELECT id FROM users WHERE name = ?", ((name or "").strip(),)
            ).fetchone()
            return row["id"] if row else None
        except sqlite3.Error as error:
            raise StorageError(f"Could not look up the user '{name}': {error}") from error

    def delete_user(self, name):
        """Remove a user and, via the cascade, all of their records."""
        self._require_connection()
        try:
            cursor = self.conn.execute("DELETE FROM users WHERE name = ?", ((name or "").strip(),))
            self.conn.commit()
            return cursor.rowcount
        except sqlite3.Error as error:
            raise StorageError(f"Could not delete the user '{name}': {error}") from error

    # -------------------------------------------------------------- records

    def add_record(self, user_name, weight_kg, height_m, bmi, category, when=None):
        """Store one BMI measurement for a user, creating the user if needed."""
        self._require_connection()
        user_id = self.add_user(user_name)
        timestamp = when or datetime.now().isoformat(timespec="seconds")

        try:
            sql = ("""
                INSERT INTO records
                    (user_id, weight_kg, height_m, bmi, category, recorded_at)
                VALUES (:uid, :w, :h, :bmi, :cat, :when)"""
            )
            params = {
'uid': user_id,
'w': float(weight_kg),
'h': float(height_m),
'bmi': float(bmi),
'cat': category,
'when': timestamp,
            }
            cursor = self.conn.execute(sql, params)
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as error:
            raise StorageError(f"Could not save the BMI record for '{user_name}': {error}") from error

    def get_records(self, user_name, limit=None):
        """Return a user's records oldest-first, so they are ready to plot."""
        self._require_connection()
        user_id = self.get_user_id(user_name)
        if user_id is None:
            return []

        query = """SELECT id, weight_kg, height_m, bmi, category, recorded_at
                   FROM records WHERE user_id = ? ORDER BY recorded_at ASC, id ASC"""
        if limit:
            # Newest N, then flip back into chronological order for charting.
            query = """SELECT * FROM (
                            SELECT id, weight_kg, height_m, bmi, category, recorded_at
                            FROM records WHERE user_id = ?
                            ORDER BY recorded_at DESC, id DESC LIMIT ?)
                        ORDER BY recorded_at ASC, id ASC"""

        try:
            if limit:
                rows = self.conn.execute(query, (user_id, int(limit))).fetchall()
            else:
                rows = self.conn.execute(query, (user_id,)).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise StorageError(f"Could not read records for '{user_name}': {error}") from error

    def delete_record(self, record_id):
        """Delete a single measurement by id."""
        self._require_connection()
        try:
            cursor = self.conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
            self.conn.commit()
            return cursor.rowcount
        except sqlite3.Error as error:
            raise StorageError(f"Could not delete record {record_id}: {error}") from error

    def latest_record(self, user_name):
        """Return the most recent record for a user, or None."""
        records = self.get_records(user_name, limit=1)
        return records[-1] if records else None
