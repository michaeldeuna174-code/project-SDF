import os
import shutil
import hashlib
import hmac
import secrets
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
from database import _validate_inputs, hash_password, verify_password
from bug_report_form import BugReportForm
from bug_report_list import BugReportList
from developer_bug_inbox import DeveloperBugInbox
from prototype_submission import PrototypeSubmission
from tester_dashboard import build_tester_dashboard


DB_FILE = "game.tracker.db"
APP_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = APP_DIR / "uploads" / "bug_screenshots"


BG_NAVY = "#0B1120"
BG_HEADER = "#111C30"
BG_PANEL = "#17263D"
BG_CARD = "#1B2D47"
ACCENT_BLUE = "#3B82F6"
ACCENT_BLUE_HOVER = "#2563EB"
ACCENT_TEAL = "#14B8A6"
ACCENT_TEAL_HOVER = "#0F9F92"
ACCENT_CYAN = "#22D3EE"
TEXT_WHITE = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
BG_INPUT = "#0D1728"
BG_BORDER = "#2A3C56"
BG_BUTTON_SECONDARY = "#263750"
BG_BUTTON_SECONDARY_HOVER = "#344966"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    existing_user_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()
    }
    if "recovery_code_hash" not in existing_user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN recovery_code_hash TEXT")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_recovery_code_hash "
        "ON users(recovery_code_hash)"
    )

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            version TEXT NOT NULL,
            genre TEXT NOT NULL,
            build_path TEXT NOT NULL,
            instructions TEXT NOT NULL,
            testing_status TEXT NOT NULL DEFAULT 'Draft',
            submission_date TEXT NOT NULL,
            thumbnail_path TEXT,
            FOREIGN KEY (owner) REFERENCES users(username)
        )
    """)

    existing_bug_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(bugs)").fetchall()
    }
    bug_columns = {
        "game_id": "INTEGER",
        "developer": "TEXT",
        "steps_to_reproduce": "TEXT",
        "expected_result": "TEXT",
        "actual_result": "TEXT",
        "submitted_at": "TEXT",
    }
    for column, definition in bug_columns.items():
        if column not in existing_bug_columns:
            cursor.execute(f"ALTER TABLE bugs ADD COLUMN {column} {definition}")

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_games_testing_status ON games(testing_status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bugs_tester_submitted ON bugs(tester, submitted_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bugs_developer_submitted ON bugs(developer, submitted_at)"
    )

    try:
        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES ('Tester1', '1234', 'Tester')
        """)

        cursor.execute("""
            INSERT INTO users (username, password, role)
            VALUES ('dev1', '4321', 'Developer')
        """)

    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()


current_user = ""
current_role = ""
selected_file_path = ""

def login(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username, role, password FROM users WHERE username = ?",
        (username,)
    )

    user = cursor.fetchone()
    conn.close()

    if user and (
        verify_password(user[2], password or "")
        or user[2] == password
    ):
        return user[0], user[1]

    return None, None


def register_user(username, password, role):
    username = (username or "").strip()

    if not username or not password:
        return False, "Please fill in all fields."

    if role not in ("Tester", "Developer"):
        return False, "Please select a role (Tester or Developer)."

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("BEGIN IMMEDIATE")
    cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    )

    if cursor.fetchone() is not None:
        conn.close()
        return False, "Username already exists. Please choose another one.", None

    try:
        while True:
            recovery_code = secrets.token_urlsafe(24)
            recovery_code_hash = hashlib.sha256(
                recovery_code.encode("utf-8")
            ).hexdigest()
            cursor.execute(
                "SELECT 1 FROM users WHERE recovery_code_hash = ?",
                (recovery_code_hash,),
            )
            if cursor.fetchone() is None:
                break

        cursor.execute(
            "INSERT INTO users (username, password, role, recovery_code_hash) "
            "VALUES (?, ?, ?, ?)",
            (username, password, role, recovery_code_hash)
        )
        conn.commit()
        return True, "Account created successfully!", recovery_code
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose another one.", None
    finally:
        conn.close()


def _recovery_code_hash(recovery_code):
    return hashlib.sha256(recovery_code.encode("utf-8")).hexdigest()


def verify_recovery_code(username, recovery_code):
    conn = sqlite3.connect(DB_FILE)
    try:
        row = conn.execute(
            "SELECT recovery_code_hash FROM users WHERE username = ?",
            ((username or "").strip(),),
        ).fetchone()
        if row is None or not row[0] or not recovery_code:
            return False
        return hmac.compare_digest(
            _recovery_code_hash(recovery_code.strip()), row[0]
        )
    finally:
        conn.close()


def reset_password(username, recovery_code, new_password):
    username = (username or "").strip()
    recovery_code = (recovery_code or "").strip()
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, recovery_code_hash FROM users WHERE username = ?",
            (username,),
        )
        row = cursor.fetchone()
        if (
            row is None
            or not row[1]
            or not recovery_code
            or not hmac.compare_digest(_recovery_code_hash(recovery_code), row[1])
        ):
            return False, "Invalid username or recovery code."

        validation_error = _validate_inputs(username, new_password, row[0])
        if validation_error:
            return False, validation_error

        cursor.execute(
            "UPDATE users SET password = ?, recovery_code_hash = NULL "
            "WHERE username = ? AND recovery_code_hash = ?",
            (hash_password(new_password), username, row[1]),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return False, "The recovery code is no longer valid."
        conn.commit()
        return True, "Password reset successfully."
    finally:
        conn.close()


def get_bug_counts(tester=None):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        if tester:
            total = cursor.execute(
                "SELECT COUNT(*) FROM bugs WHERE tester = ?", (tester,)
            ).fetchone()[0]
            resolved = cursor.execute(
                "SELECT COUNT(*) FROM bugs WHERE tester = ? AND status = ?",
                (tester, "Resolved")
            ).fetchone()[0]
        else:
            total = cursor.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
            resolved = cursor.execute(
                "SELECT COUNT(*) FROM bugs WHERE status = ?", ("Resolved",)
            ).fetchone()[0]

        conn.close()
        return total, total - resolved, resolved
    except sqlite3.Error:
        return 0, 0, 0


def _fetch_dicts(cursor, rows):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def _user_has_role(cursor, username, role):
    row = cursor.execute(
        "SELECT role FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    return row is not None and row[0] == role


def get_open_games():
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, name, description, owner, version, genre, build_path,
                   instructions, testing_status, submission_date, thumbnail_path
            FROM games
            WHERE lower(trim(testing_status)) = ?
            ORDER BY submission_date DESC, id DESC
        """, ("open for testing",)).fetchall()
        return _fetch_dicts(cursor, rows)
    finally:
        conn.close()


def get_game_by_id(game_id):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        row = cursor.execute("""
            SELECT id, name, description, owner, version, genre, build_path,
                   instructions, testing_status, submission_date, thumbnail_path
            FROM games
            WHERE id = ?
        """, (game_id,)).fetchone()
        return _fetch_dicts(cursor, [row])[0] if row is not None else None
    finally:
        conn.close()


def submit_game_prototype(
    developer, name, description, version, genre, build_path,
    instructions, testing_status, thumbnail_path="",
):
    name = (name or "").strip()
    description = (description or "").strip()
    version = (version or "").strip()
    genre = (genre or "").strip()
    build_path = (build_path or "").strip()
    instructions = (instructions or "").strip()
    thumbnail_path = (thumbnail_path or "").strip() or None

    if not all((name, description, version, genre, build_path, instructions)):
        return False, "Complete all required prototype fields.", None
    if testing_status not in ("Draft", "Open for Testing"):
        return False, "Choose Draft or Open for Testing.", None

    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        if not _user_has_role(cursor, developer, "Developer"):
            return False, "The signed-in account is not a registered Developer.", None
        cursor.execute("""
            INSERT INTO games (
                name, description, owner, version, genre, build_path,
                instructions, testing_status, submission_date, thumbnail_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, description, developer, version, genre, build_path,
            instructions, testing_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            thumbnail_path,
        ))
        conn.commit()
        return True, "Prototype saved.", cursor.lastrowid
    except sqlite3.Error as error:
        conn.rollback()
        return False, f"Could not save prototype: {error}", None
    finally:
        conn.close()


def get_tester_bug_stats(tester):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        if not _user_has_role(cursor, tester, "Tester"):
            raise ValueError("The current account is not a registered Tester.")
        total, open_count, resolved = cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(CASE
                    WHEN lower(trim(status)) IN ('open', 'in progress', 'under review')
                    THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE
                    WHEN lower(trim(status)) = 'resolved'
                    THEN 1 ELSE 0 END), 0)
            FROM bugs
            WHERE tester = ?
        """, (tester,)).fetchone()
        return total, open_count, resolved
    finally:
        conn.close()


def get_tester_bug_reports(tester, limit=None):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        if not _user_has_role(cursor, tester, "Tester"):
            raise ValueError("The current account is not a registered Tester.")
        query = """
            SELECT b.id, b.game_id, COALESCE(g.name, 'Unlinked game') AS game_name,
                   b.tester, b.title, b.severity, b.description, b.steps_to_reproduce,
                   b.expected_result, b.actual_result, b.screenshot, b.status,
                   b.submitted_at, b.developer
            FROM bugs AS b
            LEFT JOIN games AS g ON g.id = b.game_id
            WHERE b.tester = ?
            ORDER BY b.submitted_at DESC, b.id DESC
        """
        params = [tester]
        if limit is not None:
            query += " LIMIT ?"
            params.append(max(0, int(limit)))
        rows = cursor.execute(query, params).fetchall()
        return _fetch_dicts(cursor, rows)
    finally:
        conn.close()


def get_developer_bug_reports(developer):
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        if not _user_has_role(cursor, developer, "Developer"):
            raise ValueError("The current account is not a registered Developer.")
        rows = cursor.execute("""
            SELECT b.id, b.game_id, g.name AS game_name, b.tester, b.title,
                   b.severity, b.description, b.steps_to_reproduce,
                   b.expected_result, b.actual_result, b.screenshot, b.status,
                   b.submitted_at
            FROM bugs AS b
            JOIN games AS g ON g.id = b.game_id
            WHERE b.developer = ? AND g.owner = ?
            ORDER BY b.submitted_at DESC, b.id DESC
        """, (developer, developer)).fetchall()
        return _fetch_dicts(cursor, rows)
    finally:
        conn.close()


def get_bug_report_for_user(report_id, username, role):
    if role == "Tester":
        access_filter = "b.tester = ?"
        params = (report_id, username)
    elif role == "Developer":
        access_filter = "b.developer = ? AND g.owner = ?"
        params = (report_id, username, username)
    else:
        return None

    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        query = f"""
            SELECT b.id, b.game_id, COALESCE(g.name, 'Unlinked game') AS game_name,
                   b.tester, b.developer, b.title, b.severity, b.description,
                   b.steps_to_reproduce, b.expected_result, b.actual_result,
                   b.screenshot, b.status, b.submitted_at
            FROM bugs AS b
            LEFT JOIN games AS g ON g.id = b.game_id
            WHERE b.id = ? AND {access_filter}
        """
        row = cursor.execute(query, params).fetchone()
        if row is None:
            return None
        return _fetch_dicts(cursor, [row])[0]
    finally:
        conn.close()


def submit_bug_report(
    tester, game_id, title, severity, description,
    steps_to_reproduce, expected_result, actual_result, screenshot_path="",
):
    title = (title or "").strip()
    description = (description or "").strip()
    steps_to_reproduce = (steps_to_reproduce or "").strip()
    expected_result = (expected_result or "").strip()
    actual_result = (actual_result or "").strip()
    screenshot_path = (screenshot_path or "").strip() or None

    if not all((title, description, steps_to_reproduce, expected_result, actual_result)):
        return False, "Complete all required report fields.", None
    if severity not in ("Low", "Medium", "High", "Critical"):
        return False, "Choose a valid severity.", None

    stored_screenshot = None
    conn = sqlite3.connect(DB_FILE)
    try:
        cursor = conn.cursor()
        if not _user_has_role(cursor, tester, "Tester"):
            return False, "The signed-in account is not a registered Tester.", None
        game = cursor.execute("""
            SELECT owner
            FROM games
            WHERE id = ? AND lower(trim(testing_status)) = ?
        """, (game_id, "open for testing")).fetchone()
        if game is None:
            return False, "This game is no longer open for testing.", None
        developer = game[0]
        if not _user_has_role(cursor, developer, "Developer"):
            return False, "The game's owning Developer account is unavailable.", None
        screenshot_db_path = None
        if screenshot_path:
            try:
                stored_screenshot, screenshot_db_path = _store_bug_screenshot(
                    screenshot_path
                )
            except (OSError, ValueError) as error:
                return False, f"Could not save screenshot: {error}", None
        cursor.execute("""
            INSERT INTO bugs (
                tester, title, severity, description, screenshot, status,
                game_id, developer, steps_to_reproduce, expected_result,
                actual_result, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?, ?)
        """, (
            tester, title, severity, description, screenshot_db_path, game_id,
            developer, steps_to_reproduce, expected_result, actual_result,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
        return True, "Bug report submitted.", cursor.lastrowid
    except sqlite3.Error as error:
        conn.rollback()
        if stored_screenshot is not None:
            try:
                stored_screenshot.unlink(missing_ok=True)
            except OSError as cleanup_error:
                return (
                    False,
                    f"Could not submit bug report: {error} "
                    f"(could not remove copied screenshot: {cleanup_error})",
                    None,
                )
        return False, f"Could not submit bug report: {error}", None
    finally:
        conn.close()


def _store_bug_screenshot(source_path):
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Screenshot file was not found: {source}")

    try:
        with Image.open(source) as image:
            image_format = image.format
            image.verify()
    except Image.DecompressionBombError as error:
        raise ValueError(f"Screenshot image is too large to process: {error}") from error
    except (OSError, ValueError) as error:
        raise ValueError(f"Selected file is not a valid image: {error}") from error

    suffix_by_format = {
        "BMP": ".bmp",
        "GIF": ".gif",
        "JPEG": ".jpg",
        "PNG": ".png",
        "TIFF": ".tiff",
        "WEBP": ".webp",
    }
    suffix = suffix_by_format.get(image_format)
    if suffix is None:
        raise ValueError(
            "Unsupported screenshot format. Choose PNG, JPEG, GIF, BMP, TIFF, or WebP."
        )

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    destination = SCREENSHOT_DIR / f"{uuid.uuid4().hex}{suffix}"
    try:
        shutil.copy2(source, destination)
    except OSError as error:
        try:
            destination.unlink(missing_ok=True)
        except OSError as cleanup_error:
            raise OSError(
                f"{error} (could not remove partial screenshot copy: {cleanup_error})"
            ) from error
        raise
    return destination, destination.relative_to(APP_DIR).as_posix()


def _resolve_screenshot_path(screenshot_path):
    value = (screenshot_path or "").strip()
    if not value:
        return None

    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    candidates = (Path.cwd() / path, APP_DIR / path)
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


def logout():
    global current_user, current_role
    current_user = ""
    current_role = ""
    show_welcome()


def clear_screen():
    for widget in root.winfo_children():
        widget.destroy()


def on_login_click():
    show_login()


def on_register_click():
    show_register()


def add_hover(button, normal_color, hover_color):
    button.configure(fg_color=normal_color, hover_color=hover_color)


def center_window(window, width, height):
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def show_welcome():
    clear_screen()
    root.configure(fg_color=BG_NAVY)

    top_bar = ctk.CTkFrame(root, fg_color=BG_HEADER, height=68, corner_radius=0)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
    top_inner.pack(expand=True, fill="both", padx=40)

    left = ctk.CTkFrame(top_inner, fg_color="transparent")
    left.pack(side="left", fill="y")

    ctk.CTkLabel(
        left, text="\U0001F3AE", font=("Segoe UI", 22, "bold"),
        text_color=ACCENT_CYAN
    ).pack(side="left", padx=(0, 12))

    ctk.CTkLabel(
        left, text="GameBugHub",
        font=("Segoe UI", 15, "bold"),
        text_color=TEXT_WHITE
    ).pack(side="left")

    ctk.CTkLabel(
        top_inner, text="GAME DEVELOPMENT WORKSPACE  •  v1.0",
        font=("Segoe UI", 9),
        text_color=TEXT_MUTED
    ).pack(side="right")

    center = ctk.CTkFrame(root, fg_color="transparent")
    center.pack(side="top", expand=True, fill="both", padx=40, pady=(12, 0))

    ctk.CTkLabel(
        center, text="\U0001F3AE", font=("Segoe UI", 52),
        text_color=ACCENT_CYAN
    ).pack(pady=(4, 0))

    ctk.CTkLabel(
        center, text="Game Development",
        font=("Segoe UI", 32, "bold"),
        text_color=TEXT_WHITE
    ).pack(pady=(2, 0))

    ctk.CTkLabel(
        center, text="Asset and Bug Tracking Hub",
        font=("Segoe UI", 17, "bold"),
        text_color=ACCENT_CYAN
    ).pack(pady=(1, 8))

    ctk.CTkLabel(
        center,
        text="A focused workspace to track issues, organize game assets, and keep development moving.",
        font=("Segoe UI", 11),
        text_color=TEXT_MUTED, wraplength=680, justify="center"
    ).pack(pady=(0, 20))

    cards = ctk.CTkFrame(center, fg_color="transparent")
    cards.pack(pady=(0, 8))

    features = [
        ("\U0001F41E  Bug Tracking", "Report and track bugs"),
        ("\U0001F4C1  Game Assets", "Organize project files"),
        ("\U0001F4BB  Dev Builds", "Milestones and fixes"),
    ]

    for icon_title, desc in features:
        card = ctk.CTkFrame(
            cards, fg_color=BG_CARD, width=230, height=108,
            corner_radius=16, border_width=1, border_color=BG_BORDER
        )
        card.pack(side="left", padx=9)
        card.pack_propagate(False)
        ctk.CTkLabel(
            card, text=icon_title, font=("Segoe UI", 11, "bold"),
            text_color=TEXT_WHITE
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            card, text=desc, font=("Segoe UI", 9),
            text_color=TEXT_MUTED
        ).pack()

    bottom = ctk.CTkFrame(root, fg_color="transparent")
    bottom.pack(side="bottom", fill="x", pady=(0, 24))

    btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
    btn_row.pack(anchor="center")

    login_btn = ctk.CTkButton(
        btn_row, text="Log In", command=on_login_click,
        font=("Segoe UI", 11, "bold"),
        fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
        text_color=TEXT_WHITE, corner_radius=10,
        width=190, height=44
    )
    login_btn.pack(side="left", padx=8)
    add_hover(login_btn, ACCENT_BLUE, ACCENT_BLUE_HOVER)

    register_btn = ctk.CTkButton(
        btn_row, text="Register", command=on_register_click,
        font=("Segoe UI", 11, "bold"),
        fg_color=ACCENT_TEAL, hover_color=ACCENT_TEAL_HOVER,
        text_color=TEXT_WHITE, corner_radius=10,
        width=190, height=44
    )
    register_btn.pack(side="left", padx=8)
    add_hover(register_btn, ACCENT_TEAL, ACCENT_TEAL_HOVER)

    ctk.CTkLabel(
        bottom, text="A shared hub for better game builds.",
        font=("Segoe UI", 9),
        text_color=TEXT_MUTED
    ).pack(pady=(12, 0))


def show_login():
    clear_screen()
    root.configure(fg_color=BG_NAVY)

    top_bar = ctk.CTkFrame(root, fg_color=BG_HEADER, height=64, corner_radius=0)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
    top_inner.pack(expand=True, fill="both", padx=36)

    ctk.CTkLabel(
        top_inner, text="\U0001F3AE  GameBugHub",
        font=("Segoe UI", 14, "bold"),
        text_color=TEXT_WHITE
    ).pack(side="left")

    ctk.CTkLabel(
        top_inner, text="ACCOUNT ACCESS",
        font=("Segoe UI", 9),
        text_color=TEXT_MUTED
    ).pack(side="right")

    center = ctk.CTkFrame(root, fg_color="transparent")
    center.pack(side="top", expand=True, fill="both")
    center.grid_columnconfigure(0, weight=1)

    panel = ctk.CTkFrame(
        center, fg_color=BG_PANEL, corner_radius=20,
        border_width=1, border_color=BG_BORDER
    )
    panel.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        panel, text="GAMEBUGHUB ACCOUNT",
        font=("Segoe UI", 9, "bold"),
        text_color=ACCENT_CYAN
    ).pack(padx=42, pady=(26, 5))

    ctk.CTkLabel(
        panel, text="Welcome back",
        font=("Segoe UI", 24, "bold"),
        text_color=TEXT_WHITE
    ).pack(padx=42, pady=(0, 2))

    ctk.CTkLabel(
        panel, text="Sign in to continue to your workspace.",
        font=("Segoe UI", 10),
        text_color=TEXT_MUTED
    ).pack(pady=(2, 20))

    ctk.CTkLabel(
        panel, text="Username", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(anchor="w", padx=42)
    username_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 11), width=340, height=42,
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, border_width=1, corner_radius=10
    )
    username_entry.pack(fill="x", padx=42, pady=(5, 14))
    username_entry.focus_set()

    ctk.CTkLabel(
        panel, text="Password", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(anchor="w", padx=42)
    password_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 11), width=340, height=42, show="*",
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, border_width=1, corner_radius=10
    )
    password_entry.pack(fill="x", padx=42, pady=(5, 8))

    forgot_password_label = ctk.CTkLabel(
        panel, text="Forgot Password?", font=("Segoe UI", 9),
        text_color=ACCENT_CYAN, cursor="hand2",
    )
    forgot_password_label.pack(anchor="e", padx=42, pady=(0, 4))
    forgot_password_label.bind(
        "<Button-1>", lambda _event: show_forgot_password()
    )

    error_label = ctk.CTkLabel(
        panel, text="", font=("Segoe UI", 9),
        text_color="#F87171", wraplength=340, justify="center"
    )
    error_label.pack(padx=42, pady=(2, 8))

    def do_login():
        username = username_entry.get().strip()
        password = password_entry.get()

        if not username or not password:
            error_label.configure(text="Please enter both username and password.")
            return

        user, role = login(username, password)

        if user is None:
            error_label.configure(text="Invalid username or password. Please try again.")
            return

        global current_user, current_role
        current_user = user
        current_role = role
        error_label.configure(text="")

        if role == "Tester":
            show_tester_dashboard()
        elif role == "Developer":
            show_developer_dashboard()
        else:
            error_label.configure(text="Your account role is invalid. Please contact support.")

    login_btn = ctk.CTkButton(
        panel, text="Log In", command=do_login,
        font=("Segoe UI", 11, "bold"),
        fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
        text_color=TEXT_WHITE, corner_radius=10, height=42
    )
    login_btn.pack(fill="x", padx=42, pady=(3, 9))
    add_hover(login_btn, ACCENT_BLUE, ACCENT_BLUE_HOVER)

    back_btn = ctk.CTkButton(
        panel, text="Back", command=show_welcome,
        font=("Segoe UI", 10),
        fg_color=BG_BUTTON_SECONDARY, hover_color=BG_BUTTON_SECONDARY_HOVER,
        text_color=TEXT_WHITE, corner_radius=10, height=38
    )
    back_btn.pack(fill="x", padx=42, pady=(0, 30))
    add_hover(back_btn, BG_BUTTON_SECONDARY, BG_BUTTON_SECONDARY_HOVER)

    username_entry.bind("<Return>", lambda e: do_login())
    password_entry.bind("<Return>", lambda e: do_login())


def _show_recovery_code(username, role, recovery_code):
    dialog = ctk.CTkToplevel(root)
    dialog.title("Save Your Recovery Code")
    dialog.geometry("500x270")
    dialog.resizable(False, False)
    dialog.configure(fg_color=BG_NAVY)
    dialog.transient(root)
    dialog.grab_set()

    panel = ctk.CTkFrame(
        dialog, fg_color=BG_PANEL, corner_radius=20,
        border_width=1, border_color=BG_BORDER,
    )
    panel.pack(fill="both", expand=True, padx=18, pady=18)
    ctk.CTkLabel(
        panel, text="Save Your Recovery Code",
        font=("Segoe UI", 18, "bold"), text_color=TEXT_WHITE,
    ).pack(padx=22, pady=(20, 4))
    ctk.CTkLabel(
        panel,
        text=f"Account: {username} ({role})\nSave this code securely. It is shown only once.",
        font=("Segoe UI", 10), text_color=TEXT_MUTED, justify="center",
    ).pack(padx=22, pady=(0, 12))

    code_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 12), width=350, height=38,
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, corner_radius=10,
        justify="center",
    )
    code_entry.pack(padx=22, pady=(0, 10))
    code_entry.insert(0, recovery_code)
    code_entry.configure(state="readonly")

    status_label = ctk.CTkLabel(
        panel, text="You need this code to reset your password.",
        font=("Segoe UI", 9), text_color=ACCENT_CYAN,
    )
    status_label.pack(pady=(0, 8))

    def copy_code():
        try:
            dialog.clipboard_clear()
            dialog.clipboard_append(recovery_code)
            dialog.update()
            status_label.configure(text="Recovery code copied. Store it somewhere safe.")
        except tk.TclError as error:
            status_label.configure(text=f"Could not copy recovery code: {error}")

    actions = ctk.CTkFrame(panel, fg_color="transparent")
    actions.pack(pady=(0, 14))
    ctk.CTkButton(
        actions, text="Copy", width=110,
        fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
        text_color=TEXT_WHITE, command=copy_code,
    ).pack(side="left", padx=5)
    ctk.CTkButton(
        actions, text="Continue", width=110,
        fg_color=BG_BUTTON_SECONDARY, hover_color=BG_BUTTON_SECONDARY_HOVER,
        text_color=TEXT_WHITE, command=dialog.destroy,
    ).pack(side="left", padx=5)


def show_forgot_password():
    dialog = ctk.CTkToplevel(root)
    dialog.title("Forgot Password")
    dialog.geometry("500x610")
    dialog.resizable(False, False)
    dialog.configure(fg_color=BG_NAVY)
    dialog.transient(root)
    dialog.grab_set()

    panel = ctk.CTkFrame(
        dialog, fg_color=BG_PANEL, corner_radius=20,
        border_width=1, border_color=BG_BORDER,
    )
    panel.pack(fill="both", expand=True, padx=18, pady=18)
    ctk.CTkLabel(
        panel, text="Reset Password",
        font=("Segoe UI", 20, "bold"), text_color=TEXT_WHITE,
    ).pack(padx=38, pady=(22, 4))
    ctk.CTkLabel(
        panel, text="Enter your username and recovery code to continue.",
        font=("Segoe UI", 10), text_color=TEXT_MUTED,
    ).pack(padx=30, pady=(0, 16))

    ctk.CTkLabel(
        panel, text="Username", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE,
    ).pack(anchor="w", padx=38)
    username_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 10), width=340, height=38,
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, corner_radius=10,
    )
    username_entry.pack(fill="x", padx=38, pady=(3, 9))

    ctk.CTkLabel(
        panel, text="Recovery Code", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE,
    ).pack(anchor="w", padx=38)
    recovery_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 10), width=340, height=38,
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, corner_radius=10,
    )
    recovery_entry.pack(fill="x", padx=38, pady=(3, 9))

    error_label = ctk.CTkLabel(
        panel, text="", font=("Segoe UI", 9),
        text_color="#F87171", wraplength=350, justify="center",
    )
    error_label.pack(padx=38, pady=(0, 8))

    reset_fields = ctk.CTkFrame(panel, fg_color="transparent")
    reset_fields.pack(fill="x", padx=38)

    def verify_code():
        username = username_entry.get().strip()
        recovery_code = recovery_entry.get().strip()
        if not username or not recovery_code:
            error_label.configure(text="Enter both your username and recovery code.")
            return
        if not verify_recovery_code(username, recovery_code):
            error_label.configure(text="Invalid username or recovery code.")
            return

        error_label.configure(text="Recovery code verified. Choose a new password.", text_color=ACCENT_CYAN)
        username_entry.configure(state="disabled")
        recovery_entry.configure(state="disabled")
        verify_button.configure(state="disabled")

        ctk.CTkLabel(
            reset_fields, text="New Password", font=("Segoe UI", 10, "bold"),
            text_color=TEXT_WHITE,
        ).pack(anchor="w")
        new_password_entry = ctk.CTkEntry(
            reset_fields, font=("Segoe UI", 10), width=340, height=38, show="*",
            fg_color=BG_INPUT, text_color=TEXT_WHITE,
            border_color=BG_BORDER, corner_radius=10,
        )
        new_password_entry.pack(fill="x", pady=(3, 9))
        ctk.CTkLabel(
            reset_fields, text="Confirm New Password",
            font=("Segoe UI", 10, "bold"), text_color=TEXT_WHITE,
        ).pack(anchor="w")
        confirm_password_entry = ctk.CTkEntry(
            reset_fields, font=("Segoe UI", 10), width=340, height=38, show="*",
            fg_color=BG_INPUT, text_color=TEXT_WHITE,
            border_color=BG_BORDER, corner_radius=10,
        )
        confirm_password_entry.pack(fill="x", pady=(3, 10))

        def save_password():
            new_password = new_password_entry.get()
            confirm_password = confirm_password_entry.get()
            if new_password != confirm_password:
                error_label.configure(text="Passwords do not match.")
                return
            success, message = reset_password(
                username, recovery_code, new_password
            )
            if not success:
                error_label.configure(text=message)
                return
            messagebox.showinfo(
                "Password Reset", message, parent=dialog
            )
            dialog.destroy()

        ctk.CTkButton(
            reset_fields, text="Reset Password", height=40,
            fg_color=ACCENT_TEAL, hover_color=ACCENT_TEAL_HOVER,
            text_color=TEXT_WHITE, command=save_password,
        ).pack(fill="x", pady=(2, 8))
        new_password_entry.focus_set()

    verify_button = ctk.CTkButton(
        panel, text="Verify Recovery Code", height=40,
        fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
        text_color=TEXT_WHITE, command=verify_code,
    )
    verify_button.pack(fill="x", padx=38, pady=(0, 8))
    ctk.CTkButton(
        panel, text="Cancel", height=38,
        fg_color=BG_BUTTON_SECONDARY, hover_color=BG_BUTTON_SECONDARY_HOVER,
        text_color=TEXT_WHITE, command=dialog.destroy,
    ).pack(fill="x", padx=38, pady=(0, 18))


def show_register():
    clear_screen()
    root.configure(fg_color=BG_NAVY)

    top_bar = ctk.CTkFrame(root, fg_color=BG_HEADER, height=64, corner_radius=0)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
    top_inner.pack(expand=True, fill="both", padx=36)

    ctk.CTkLabel(
        top_inner, text="\U0001F3AE  GameBugHub",
        font=("Segoe UI", 14, "bold"),
        text_color=TEXT_WHITE
    ).pack(side="left")

    ctk.CTkLabel(
        top_inner, text="CREATE YOUR ACCOUNT",
        font=("Segoe UI", 9),
        text_color=TEXT_MUTED
    ).pack(side="right")

    center = ctk.CTkFrame(root, fg_color="transparent")
    center.pack(side="top", expand=True, fill="both")
    center.grid_columnconfigure(0, weight=1)

    panel = ctk.CTkFrame(
        center, fg_color=BG_PANEL, corner_radius=20,
        border_width=1, border_color=BG_BORDER
    )
    panel.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        panel, text="Create Account",
        font=("Segoe UI", 21, "bold"),
        text_color=TEXT_WHITE
    ).pack(padx=38, pady=(18, 1))

    ctk.CTkLabel(
        panel, text="Register a new Tester or Developer account.",
        font=("Segoe UI", 10),
        text_color=TEXT_MUTED
    ).pack(pady=(2, 10))

    ctk.CTkLabel(
        panel, text="Username", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(anchor="w", padx=38)
    username_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 10), width=340, height=38,
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, border_width=1, corner_radius=10
    )
    username_entry.pack(fill="x", padx=38, pady=(3, 7))
    username_entry.focus_set()

    ctk.CTkLabel(
        panel, text="Password", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(anchor="w", padx=38)
    password_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 10), width=340, height=38, show="*",
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, border_width=1, corner_radius=10
    )
    password_entry.pack(fill="x", padx=38, pady=(3, 7))

    ctk.CTkLabel(
        panel, text="Confirm Password", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(anchor="w", padx=38)
    confirm_entry = ctk.CTkEntry(
        panel, font=("Segoe UI", 10), width=340, height=38, show="*",
        fg_color=BG_INPUT, text_color=TEXT_WHITE,
        border_color=BG_BORDER, border_width=1, corner_radius=10
    )
    confirm_entry.pack(fill="x", padx=38, pady=(3, 7))

    ctk.CTkLabel(
        panel, text="Role", font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(anchor="w", padx=38)
    role_var = tk.StringVar(value="Select role")
    role_menu = ctk.CTkOptionMenu(
        panel, variable=role_var, values=["Tester", "Developer"],
        font=("Segoe UI", 10), dropdown_font=("Segoe UI", 10),
        width=340, height=38, corner_radius=10,
        fg_color=BG_INPUT, button_color=BG_BUTTON_SECONDARY,
        button_hover_color=BG_BUTTON_SECONDARY_HOVER,
        dropdown_fg_color=BG_CARD, dropdown_hover_color=ACCENT_BLUE,
        text_color=TEXT_WHITE, dropdown_text_color=TEXT_WHITE
    )
    role_menu.pack(fill="x", padx=38, pady=(3, 4))

    show_var = tk.BooleanVar(value=False)

    def toggle_passwords():
        char = "" if show_var.get() else "*"
        password_entry.configure(show=char)
        confirm_entry.configure(show=char)

    ctk.CTkCheckBox(
        panel, text="Show password", variable=show_var,
        command=toggle_passwords,
        font=("Segoe UI", 9), text_color=TEXT_MUTED,
        fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
        border_color=BG_BORDER, checkmark_color=TEXT_WHITE,
        corner_radius=5
    ).pack(anchor="w", padx=38, pady=(1, 1))

    error_label = ctk.CTkLabel(
        panel, text="", font=("Segoe UI", 9),
        text_color="#F87171", wraplength=340, justify="center"
    )
    error_label.pack(padx=38, pady=(1, 5))

    def do_register():
        username = username_entry.get().strip()
        password = password_entry.get()
        confirm = confirm_entry.get()
        role = role_var.get()

        if not username or not password or not confirm:
            error_label.configure(text="Please fill in all fields.")
            return

        if password != confirm:
            error_label.configure(text="Passwords do not match. Please try again.")
            return

        if role not in ("Tester", "Developer"):
            error_label.configure(text="Please select a role (Tester or Developer).")
            return

        ok, msg, recovery_code = register_user(username, password, role)

        if not ok:
            error_label.configure(text=msg)
            return

        show_login()
        _show_recovery_code(username, role, recovery_code)

    create_btn = ctk.CTkButton(
        panel, text="Create Account", command=do_register,
        font=("Segoe UI", 10, "bold"),
        fg_color=ACCENT_TEAL, hover_color=ACCENT_TEAL_HOVER,
        text_color=TEXT_WHITE, corner_radius=10, height=40
    )
    create_btn.pack(fill="x", padx=38, pady=(2, 6))
    add_hover(create_btn, ACCENT_TEAL, ACCENT_TEAL_HOVER)

    back_btn = ctk.CTkButton(
        panel, text="Back to Login", command=show_login,
        font=("Segoe UI", 10),
        fg_color=BG_BUTTON_SECONDARY, hover_color=BG_BUTTON_SECONDARY_HOVER,
        text_color=TEXT_WHITE, corner_radius=10, height=38
    )
    back_btn.pack(fill="x", padx=38, pady=(0, 18))
    add_hover(back_btn, BG_BUTTON_SECONDARY, BG_BUTTON_SECONDARY_HOVER)

    username_entry.bind("<Return>", lambda e: do_register())
    password_entry.bind("<Return>", lambda e: do_register())
    confirm_entry.bind("<Return>", lambda e: do_register())


def _dashboard_header(dashboard_title):
    top_bar = ctk.CTkFrame(root, fg_color=BG_HEADER, height=68, corner_radius=0)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
    top_inner.pack(expand=True, fill="both", padx=36)

    left = ctk.CTkFrame(top_inner, fg_color="transparent")
    left.pack(side="left", fill="y")

    ctk.CTkLabel(
        left, text="\U0001F3AE", font=("Segoe UI", 19),
        text_color=ACCENT_CYAN
    ).pack(side="left", padx=(0, 12))

    ctk.CTkLabel(
        left, text="GameBugHub",
        font=("Segoe UI", 14, "bold"),
        text_color=TEXT_WHITE
    ).pack(side="left")

    ctk.CTkLabel(
        left, text="  /  " + dashboard_title,
        font=("Segoe UI", 10),
        text_color=TEXT_MUTED
    ).pack(side="left")

    right = ctk.CTkFrame(top_inner, fg_color="transparent")
    right.pack(side="right", fill="y")

    ctk.CTkLabel(
        right, text=current_user,
        font=("Segoe UI", 10, "bold"),
        text_color=TEXT_WHITE
    ).pack(side="left", padx=(0, 8))

    role_badge = ctk.CTkLabel(
        right, text=current_role.upper(),
        font=("Segoe UI", 8, "bold"),
        fg_color=BG_INPUT, text_color=ACCENT_CYAN,
        corner_radius=8
    )
    role_badge.pack(side="left", padx=(0, 14), ipadx=9, ipady=5)

    logout_btn = ctk.CTkButton(
        right, text="Logout", command=logout,
        font=("Segoe UI", 10, "bold"),
        fg_color=BG_BUTTON_SECONDARY, hover_color=BG_BUTTON_SECONDARY_HOVER,
        text_color=TEXT_WHITE, corner_radius=9, width=88, height=36
    )
    logout_btn.pack(side="left")
    add_hover(logout_btn, BG_BUTTON_SECONDARY, BG_BUTTON_SECONDARY_HOVER)


def _summary_cards(parent, cards):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(pady=(0, 22))

    for icon, count, label in cards:
        card = ctk.CTkFrame(
            row, fg_color=BG_CARD, width=230, height=172,
            corner_radius=16, border_width=1, border_color=BG_BORDER
        )
        card.pack(side="left", padx=10)
        card.pack_propagate(False)
        ctk.CTkLabel(
            card, text=icon, font=("Segoe UI", 22),
            text_color=ACCENT_CYAN
        ).pack(pady=(13, 1))
        ctk.CTkLabel(
            card, text=str(count), font=("Segoe UI", 30, "bold"),
            text_color=TEXT_WHITE
        ).pack(pady=(0, 1))
        ctk.CTkLabel(
            card, text=label, font=("Segoe UI", 9, "bold"),
            text_color=TEXT_MUTED
        ).pack()


def show_bug_report_details(report_id, username, role):
    try:
        report = get_bug_report_for_user(report_id, username, role)
    except (sqlite3.Error, ValueError) as error:
        messagebox.showerror("Could Not Load Report", str(error), parent=root)
        return
    if report is None:
        messagebox.showerror(
            "Report Unavailable",
            "This report does not exist or is not available to your account.",
            parent=root,
        )
        return

    window = ctk.CTkToplevel(root)
    window.title(f"Bug Report #{report['id']}")
    window.geometry("680x600")
    window.configure(fg_color=BG_NAVY)
    window.transient(root)
    window.grab_set()
    content = ctk.CTkScrollableFrame(
        window, fg_color=BG_PANEL, corner_radius=16,
        border_width=1, border_color=BG_BORDER,
    )
    content.pack(fill="both", expand=True, padx=18, pady=18)
    ctk.CTkLabel(
        content, text=report["title"], font=("Segoe UI", 22, "bold"),
        text_color=TEXT_WHITE, wraplength=570, justify="left",
    ).pack(anchor="w", padx=18, pady=(18, 8))
    summary = (
        f"Game: {report['game_name']}\n"
        f"Tester: {report['tester']}\n"
        f"Developer: {report['developer'] or 'Unavailable'}\n"
        f"Severity: {report['severity']}\n"
        f"Status: {report['status']}\n"
        f"Submitted: {report['submitted_at'] or 'Date unavailable'}"
    )
    ctk.CTkLabel(
        content, text=summary, font=("Segoe UI", 10), text_color=ACCENT_CYAN,
        justify="left", anchor="w",
    ).pack(anchor="w", padx=18, pady=(0, 14))
    for heading, key in (
        ("Description", "description"),
        ("Steps to Reproduce", "steps_to_reproduce"),
        ("Expected Result", "expected_result"),
        ("Actual Result", "actual_result"),
    ):
        ctk.CTkLabel(
            content, text=f"{heading}\n{report.get(key) or 'Not provided'}",
            font=("Segoe UI", 11), text_color=TEXT_MUTED,
            wraplength=570, justify="left", anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 14))

    ctk.CTkLabel(
        content, text="Screenshot", font=("Segoe UI", 11, "bold"),
        text_color=TEXT_WHITE, anchor="w",
    ).pack(anchor="w", padx=18, pady=(0, 6))
    screenshot_path = _resolve_screenshot_path(report.get("screenshot"))
    screenshot_exists = screenshot_path is not None and screenshot_path.is_file()
    preview = None
    if screenshot_path is None:
        preview = ctk.CTkLabel(
            content, text="No screenshot attached",
            font=("Segoe UI", 10), text_color=TEXT_MUTED, anchor="w",
        )
    elif not screenshot_exists:
        preview = ctk.CTkLabel(
            content, text="Screenshot file is missing; it may have been moved or deleted.",
            font=("Segoe UI", 10), text_color="#F87171", anchor="w",
        )
    else:
        try:
            with Image.open(screenshot_path) as source_image:
                thumbnail = source_image.copy()
                thumbnail.thumbnail((520, 320), Image.Resampling.LANCZOS)
                if thumbnail.mode not in ("RGB", "RGBA"):
                    thumbnail = thumbnail.convert("RGB")
            screenshot_image = ctk.CTkImage(
                light_image=thumbnail,
                dark_image=thumbnail,
                size=thumbnail.size,
            )
            preview = ctk.CTkLabel(
                content, text="", image=screenshot_image, cursor="hand2",
            )
            preview.image = screenshot_image
            preview.bind(
                "<Button-1>",
                lambda _event, path=screenshot_path: _open_screenshot(path, window),
            )
        except (OSError, ValueError, Image.DecompressionBombError):
            preview = ctk.CTkLabel(
                content, text="This file is not a supported or valid image.",
                font=("Segoe UI", 10), text_color="#F87171", anchor="w",
            )
    preview.pack(anchor="w", padx=18, pady=(0, 10))
    ctk.CTkButton(
        content, text="Open Full Screenshot",
        fg_color=BG_BUTTON_SECONDARY, hover_color=BG_BUTTON_SECONDARY_HOVER,
        text_color=TEXT_WHITE,
        command=lambda path=screenshot_path: _open_screenshot(path, window),
        state="normal" if screenshot_exists else "disabled",
    ).pack(anchor="w", padx=18, pady=(0, 14))
    ctk.CTkButton(
        content, text="Close", fg_color=BG_BUTTON_SECONDARY,
        hover_color=BG_BUTTON_SECONDARY_HOVER, text_color=TEXT_WHITE,
        command=window.destroy,
    ).pack(anchor="w", padx=18, pady=(0, 18))


def _open_screenshot(path, parent):
    if path is None or not path.is_file():
        messagebox.showerror(
            "Screenshot Unavailable",
            "The screenshot file is missing or unavailable.",
            parent=parent,
        )
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except (OSError, subprocess.SubprocessError) as error:
        messagebox.showerror(
            "Could Not Open Screenshot",
            f"The screenshot could not be opened: {error}",
            parent=parent,
        )


def show_tester_bug_reports():
    clear_screen()
    root.configure(fg_color=BG_NAVY)
    view = BugReportList(
        root, current_user, get_tester_bug_reports, show_tester_dashboard,
        lambda report_id, username, role: show_bug_report_details(
            report_id, username, role
        ),
    )
    view.pack(fill="both", expand=True)


def show_tester_bug_form(game):
    if current_role != "Tester":
        messagebox.showerror(
            "Access Denied",
            "A Tester account is required to submit a bug report.",
            parent=root,
        )
        show_welcome()
        return
    try:
        current_game = get_game_by_id(game["id"])
    except sqlite3.Error as error:
        messagebox.showerror("Could Not Load Game", str(error), parent=root)
        show_tester_dashboard()
        return
    if current_game is None or current_game["testing_status"].casefold() != "open for testing":
        messagebox.showerror(
            "Game Unavailable",
            "This prototype is no longer open for testing.",
            parent=root,
        )
        show_tester_dashboard()
        return
    clear_screen()
    root.configure(fg_color=BG_NAVY)
    view = BugReportForm(
        root, current_user, current_game, submit_bug_report,
        show_tester_dashboard, show_tester_dashboard,
    )
    view.pack(fill="both", expand=True)


def show_developer_bug_inbox():
    if current_role != "Developer":
        messagebox.showerror(
            "Access Denied",
            "A Developer account is required to open the bug inbox.",
            parent=root,
        )
        show_welcome()
        return
    clear_screen()
    root.configure(fg_color=BG_NAVY)
    view = DeveloperBugInbox(
        root, current_user, get_developer_bug_reports, show_developer_dashboard,
        lambda report_id, username, role: show_bug_report_details(
            report_id, username, role
        ),
    )
    view.pack(fill="both", expand=True)


def show_prototype_submission():
    if current_role != "Developer":
        messagebox.showerror(
            "Access Denied",
            "A Developer account is required to submit a prototype.",
            parent=root,
        )
        show_welcome()
        return
    clear_screen()
    root.configure(fg_color=BG_NAVY)
    view = PrototypeSubmission(
        root, current_user, submit_game_prototype,
        show_developer_dashboard, show_developer_dashboard,
    )
    view.pack(fill="both", expand=True)


def show_tester_dashboard():
    clear_screen()
    root.configure(fg_color=BG_NAVY)
    dashboard = build_tester_dashboard(
        root,
        current_user,
        get_tester_bug_stats,
        get_open_games,
        get_tester_bug_reports,
        logout,
        show_tester_bug_reports,
        show_tester_bug_form,
        lambda report_id: show_bug_report_details(
            report_id, current_user, "Tester"
        ),
    )
    dashboard.pack(fill="both", expand=True)


def show_developer_dashboard():
    clear_screen()
    root.configure(fg_color=BG_NAVY)
    _dashboard_header("Developer Dashboard")

    center = ctk.CTkFrame(root, fg_color="transparent")
    center.pack(side="top", expand=True, fill="both", padx=40, pady=16)

    ctk.CTkLabel(
        center, text="DEVELOPER WORKSPACE",
        font=("Segoe UI", 9, "bold"),
        text_color=ACCENT_BLUE
    ).pack(pady=(4, 4))

    ctk.CTkLabel(
        center, text=f"Welcome back, {current_user}!",
        font=("Segoe UI", 25, "bold"),
        text_color=TEXT_WHITE
    ).pack(pady=(0, 5))

    ctk.CTkLabel(
        center, text="Review reported issues, monitor progress, and prepare fixes for your game.",
        font=("Segoe UI", 11),
        text_color=TEXT_MUTED
    ).pack(pady=(0, 22))

    total, open_bugs, resolved = get_bug_counts()
    _summary_cards(center, [
        ("\U0001F41E", total, "Total Bugs"),
        ("\U0001F4CB", open_bugs, "Open Bugs"),
        ("\u2705", resolved, "Resolved Bugs"),
    ])

    view_btn = ctk.CTkButton(
        center, text="View Bug Reports",
        command=show_developer_bug_inbox,
        font=("Segoe UI", 11, "bold"),
        fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER,
        text_color=TEXT_WHITE, corner_radius=10, width=230, height=44
    )
    view_btn.pack(pady=(2, 8))
    add_hover(view_btn, ACCENT_BLUE, ACCENT_BLUE_HOVER)

    submit_btn = ctk.CTkButton(
        center, text="Submit a Prototype",
        command=show_prototype_submission,
        font=("Segoe UI", 11, "bold"),
        fg_color=ACCENT_TEAL, hover_color=ACCENT_TEAL_HOVER,
        text_color=TEXT_WHITE, corner_radius=10, width=230, height=44
    )
    submit_btn.pack(pady=(2, 8))
    add_hover(submit_btn, ACCENT_TEAL, ACCENT_TEAL_HOVER)

    ctk.CTkLabel(
        center, text="Role: Developer  •  Counts refresh each time the dashboard opens.",
        font=("Segoe UI", 9),
        text_color=TEXT_MUTED
    ).pack(pady=(10, 0))


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Game Development Asset and Bug Tracking Hub")
    center_window(root, 1100, 700)
    root.minsize(900, 600)
    root.configure(fg_color=BG_NAVY)

    show_welcome()

    root.mainloop()
