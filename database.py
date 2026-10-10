"""Local SQLite database for Game Bug Tester System.

Stores user accounts (Tester / Developer) with secure password hashing.
Uses only Python built-in modules: sqlite3, hashlib, os, datetime.

Database file: game_tracker.db
Table: users (id, username, password_hash, full_name, email, role, created_at)
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_NAME = "game_tracker.db"
LEGACY_DB = "game.tracker.db"  # old file with plaintext passwords, kept as backup source

VALID_ROLES = ("Tester", "Developer")


# ---------- Password hashing (secure, no extra dependencies) ----------

def hash_password(password):
    """Create a salted hash: 'salt_hex$hash_hex' using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + "$" + pwd_hash.hex()


def verify_password(stored_hash, password):
    """Check a plaintext password against a stored 'salt$hash' value."""
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return check.hex() == hash_hex
    except (ValueError, AttributeError):
        return False


# ---------- Connection ----------

def get_connection():
    """Open a connection to the local database file."""
    conn = sqlite3.connect(DB_NAME)
    return conn


# ---------- Init (auto-create, preserve records) ----------

def init_database():
    """Create game_tracker.db and users table if they do not exist.

    Safe to call on every startup: uses IF NOT EXISTS and
    INSERT OR IGNORE so existing records are never deleted.
    Also migrates Tester1 / dev1 from the old game.tracker.db once.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            email TEXT UNIQUE,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Keep bugs table available so the new file can fully replace the old one later.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tester TEXT,
            title TEXT,
            severity TEXT,
            description TEXT,
            screenshot TEXT,
            status TEXT
        )
    """)
    conn.commit()

    _migrate_legacy_users(conn)

    conn.commit()
    conn.close()


def _migrate_legacy_users(conn):
    """Copy existing accounts from game.tracker.db (plaintext) into the new table.

    Runs only for usernames that do not exist yet, so restarts never duplicate.
    Old plaintext passwords are hashed during migration.
    """
    if not os.path.exists(LEGACY_DB):
        return

    try:
        old_conn = sqlite3.connect(LEGACY_DB)
        old_cur = old_conn.cursor()
        rows = old_cur.execute("SELECT username, password, role FROM users").fetchall()
        old_conn.close()
    except sqlite3.Error:
        return  # old file missing table, etc. -> skip migration

    cursor = conn.cursor()
    for username, password, role in rows:
        if role not in VALID_ROLES:
            continue
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone() is None:
            cursor.execute(
                """INSERT OR IGNORE INTO users (username, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?)""",
                (username, hash_password(password),
                 role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )


# Backwards-friendly alias
init_db = init_database


# ---------- Validation ----------

def _validate_inputs(username, password, role, email=""):
    """Return an error message string if invalid, else None."""
    username = (username or "").strip()
    email = (email or "").strip()

    if not username or not password:
        return "Username and password are required."
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if len(password) < 4:
        return "Password must be at least 4 characters."
    if role not in VALID_ROLES:
        return "Role must be 'Tester' or 'Developer'."
    if email and ("@" not in email or "." not in email):
        return "Invalid email address."
    return None


# ---------- Register / retrieve / login ----------

def register_user(username, password, role, full_name="", email=""):
    """Save a new user permanently. Returns (True/False, message).

    Uses parameterized queries and UNIQUE constraints on username/email.
    """
    username = (username or "").strip()
    full_name = (full_name or "").strip()
    email = (email or "").strip() or None  # store empty email as NULL

    error = _validate_inputs(username, password, role, email or "")
    if error:
        return False, error

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, hash_password(password), full_name, email,
             role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        return True, "User registered successfully."
    except sqlite3.IntegrityError:
        return False, "Username or email already exists."
    finally:
        conn.close()


def get_user_by_username(username):
    """Retrieve one account as a dict, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, username, password_hash, full_name, email, role, created_at
           FROM users WHERE username = ?""",
        ((username or "").strip(),),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "full_name": row[3],
        "email": row[4],
        "role": row[5],
        "created_at": row[6],
    }


def get_all_users():
    """Retrieve all accounts (without password hashes) for admin/listing use."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, full_name, email, role, created_at FROM users ORDER BY id"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "username": r[1], "full_name": r[2],
         "email": r[3], "role": r[4], "created_at": r[5]}
        for r in rows
    ]


def validate_login(username, password):
    """Check credentials. Returns (username, role) on success, (None, None) on failure.

    Same return shape as the old login() so existing code keeps working.
    Role tells the system whether the user is a Tester or a Developer.
    """
    user = get_user_by_username(username)
    if user and verify_password(user["password_hash"], password or ""):
        return user["username"], user["role"]
    return None, None


# Aliases so existing code can switch over with a one-line import change
login = validate_login
get_user = get_user_by_username


if __name__ == "__main__":
    init_database()
    print("Database ready:", DB_NAME)
    for u in get_all_users():
        print(u["username"], "-", u["role"])
