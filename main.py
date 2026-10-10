import sqlite3
import tkinter as tk
from tkinter import messagebox


# Color palette
BG_NAVY = "#0B1628"
BG_CARD = "#13233F"
ACCENT_BLUE = "#2563EB"
ACCENT_BLUE_HOVER = "#1D4ED8"
ACCENT_TEAL = "#14B8A6"
ACCENT_TEAL_HOVER = "#0D9488"
ACCENT_CYAN = "#06B6D4"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#9FB3C8"


def init_db():
    conn = sqlite3.connect("game.tracker.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

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
    conn = sqlite3.connect("game.tracker.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username, role FROM users WHERE username = ? AND password = ?",
        (username, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:
        return user[0], user[1]

    return None, None


def register_user(username, password, role):
    username = (username or "").strip()

    if not username or not password:
        return False, "Please fill in all fields."

    if role not in ("Tester", "Developer"):
        return False, "Please select a role (Tester or Developer)."

    conn = sqlite3.connect("game.tracker.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    )

    if cursor.fetchone() is not None:
        conn.close()
        return False, "Username already exists. Please choose another one."

    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role)
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose another one."
    finally:
        conn.close()


def get_bug_counts(tester=None):
    try:
        conn = sqlite3.connect("game.tracker.db")
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
    button.bind("<Enter>", lambda e: button.config(bg=hover_color))
    button.bind("<Leave>", lambda e: button.config(bg=normal_color))


def center_window(window, width, height):
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def show_welcome():
    clear_screen()
    root.configure(bg=BG_NAVY)

    # Top bar
    top_bar = tk.Frame(root, bg=BG_CARD, height=60)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = tk.Frame(top_bar, bg=BG_CARD)
    top_inner.pack(expand=True, fill="both", padx=24)

    left = tk.Frame(top_inner, bg=BG_CARD)
    left.pack(side="left", fill="y")

    tk.Label(
        left, text="\U0001F3AE", font=("Segoe UI", 20),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(side="left", padx=(0, 10))

    tk.Label(
        left, text="Game Development Asset and Bug Tracking Hub",
        font=("Segoe UI", 11, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(side="left")

    tk.Label(
        top_inner, text="v1.0  •  Stage 1",
        font=("Segoe UI", 9),
        bg=BG_CARD, fg=TEXT_MUTED
    ).pack(side="right")

    # Center content
    center = tk.Frame(root, bg=BG_NAVY)
    center.pack(side="top", expand=True, fill="both", padx=40, pady=10)

    tk.Label(
        center, text="\U0001F3AE", font=("Segoe UI", 64),
        bg=BG_NAVY, fg=ACCENT_CYAN
    ).pack(pady=(10, 0))

    tk.Label(
        center, text="GAME DEVELOPMENT",
        font=("Segoe UI", 34, "bold"),
        bg=BG_NAVY, fg=TEXT_WHITE
    ).pack(pady=(8, 0))

    tk.Label(
        center, text="Asset and Bug Tracking Hub",
        font=("Segoe UI", 18),
        bg=BG_NAVY, fg=ACCENT_CYAN
    ).pack(pady=(0, 8))

    tk.Label(
        center,
        text="Manage your game assets, track bugs, and keep your development process organized.",
        font=("Segoe UI", 11),
        bg=BG_NAVY, fg=TEXT_MUTED,
        wraplength=650, justify="center"
    ).pack(pady=(0, 18))

    # Small decoration cards
    cards = tk.Frame(center, bg=BG_NAVY)
    cards.pack(pady=(0, 10))

    features = [
        ("\U0001F41E  Bug Tracking", "Report and track bugs"),
        ("\U0001F4C1  Game Assets", "Organize project files"),
        ("\U0001F4BB  Dev Builds", "Milestones and fixes"),
    ]

    for icon_title, desc in features:
        card = tk.Frame(cards, bg=BG_CARD, padx=20, pady=12)
        card.pack(side="left", padx=10)
        tk.Label(
            card, text=icon_title, font=("Segoe UI", 10, "bold"),
            bg=BG_CARD, fg=TEXT_WHITE
        ).pack()
        tk.Label(
            card, text=desc, font=("Segoe UI", 9),
            bg=BG_CARD, fg=TEXT_MUTED
        ).pack()

    # Bottom buttons
    bottom = tk.Frame(root, bg=BG_NAVY)
    bottom.pack(side="bottom", fill="x", pady=(0, 40))

    btn_row = tk.Frame(bottom, bg=BG_NAVY)
    btn_row.pack(anchor="center")

    login_btn = tk.Button(
        btn_row, text="Log In", command=on_login_click,
        font=("Segoe UI", 12, "bold"),
        bg=ACCENT_BLUE, fg=TEXT_WHITE,
        activebackground=ACCENT_BLUE_HOVER, activeforeground=TEXT_WHITE,
        relief="flat", bd=0, padx=10, pady=8,
        width=18, cursor="hand2"
    )
    login_btn.pack(side="left", padx=12)
    add_hover(login_btn, ACCENT_BLUE, ACCENT_BLUE_HOVER)

    register_btn = tk.Button(
        btn_row, text="Register", command=on_register_click,
        font=("Segoe UI", 12, "bold"),
        bg=ACCENT_TEAL, fg=TEXT_WHITE,
        activebackground=ACCENT_TEAL_HOVER, activeforeground=TEXT_WHITE,
        relief="flat", bd=0, padx=10, pady=8,
        width=18, cursor="hand2"
    )
    register_btn.pack(side="left", padx=12)
    add_hover(register_btn, ACCENT_TEAL, ACCENT_TEAL_HOVER)

    tk.Label(
        bottom, text="College IT Project  •  Stage 1: Welcome Screen",
        font=("Segoe UI", 9),
        bg=BG_NAVY, fg=TEXT_MUTED
    ).pack(pady=(16, 0))


def show_login():
    clear_screen()
    root.configure(bg=BG_NAVY)

    top_bar = tk.Frame(root, bg=BG_CARD, height=60)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = tk.Frame(top_bar, bg=BG_CARD)
    top_inner.pack(expand=True, fill="both", padx=24)

    tk.Label(
        top_inner, text="\U0001F3AE  Game Development Asset and Bug Tracking Hub",
        font=("Segoe UI", 11, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(side="left")

    tk.Label(
        top_inner, text="v1.0  •  Stage 2",
        font=("Segoe UI", 9),
        bg=BG_CARD, fg=TEXT_MUTED
    ).pack(side="right")

    center = tk.Frame(root, bg=BG_NAVY)
    center.pack(side="top", expand=True, fill="both")
    center.grid_columnconfigure(0, weight=1)

    panel = tk.Frame(center, bg=BG_CARD, padx=36, pady=28)
    panel.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(
        panel, text="Welcome Back",
        font=("Segoe UI", 22, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack()

    tk.Label(
        panel, text="Log in to your account to continue.",
        font=("Segoe UI", 10),
        bg=BG_CARD, fg=TEXT_MUTED
    ).pack(pady=(4, 16))

    tk.Label(
        panel, text="Username", font=("Segoe UI", 10, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(anchor="w")
    username_entry = tk.Entry(panel, font=("Segoe UI", 11), width=32)
    username_entry.pack(pady=(4, 12))
    username_entry.focus_set()

    tk.Label(
        panel, text="Password", font=("Segoe UI", 10, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(anchor="w")
    password_entry = tk.Entry(panel, font=("Segoe UI", 11), width=32, show="*")
    password_entry.pack(pady=(4, 6))

    error_label = tk.Label(
        panel, text="", font=("Segoe UI", 9),
        bg=BG_CARD, fg="#F87171", wraplength=300, justify="center"
    )
    error_label.pack(pady=(4, 8))

    def do_login():
        username = username_entry.get().strip()
        password = password_entry.get()

        if not username or not password:
            error_label.config(text="Please enter both username and password.")
            return

        user, role = login(username, password)

        if user is None:
            error_label.config(text="Invalid username or password. Please try again.")
            return

        global current_user, current_role
        current_user = user
        current_role = role
        error_label.config(text="")

        if role == "Tester":
            show_tester_dashboard()
        elif role == "Developer":
            show_developer_dashboard()
        else:
            error_label.config(text="Your account role is invalid. Please contact support.")

    login_btn = tk.Button(
        panel, text="Log In", command=do_login,
        font=("Segoe UI", 11, "bold"),
        bg=ACCENT_BLUE, fg=TEXT_WHITE,
        activebackground=ACCENT_BLUE_HOVER, activeforeground=TEXT_WHITE,
        relief="flat", bd=0, pady=8, width=28, cursor="hand2"
    )
    login_btn.pack(pady=(4, 8))
    add_hover(login_btn, ACCENT_BLUE, ACCENT_BLUE_HOVER)

    back_btn = tk.Button(
        panel, text="Back", command=show_welcome,
        font=("Segoe UI", 10),
        bg="#334155", fg=TEXT_WHITE,
        activebackground="#475569", activeforeground=TEXT_WHITE,
        relief="flat", bd=0, pady=6, width=28, cursor="hand2"
    )
    back_btn.pack()
    add_hover(back_btn, "#334155", "#475569")

    username_entry.bind("<Return>", lambda e: do_login())
    password_entry.bind("<Return>", lambda e: do_login())


def show_register():
    clear_screen()
    root.configure(bg=BG_NAVY)

    top_bar = tk.Frame(root, bg=BG_CARD, height=60)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = tk.Frame(top_bar, bg=BG_CARD)
    top_inner.pack(expand=True, fill="both", padx=24)

    tk.Label(
        top_inner, text="\U0001F3AE  Game Development Asset and Bug Tracking Hub",
        font=("Segoe UI", 11, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(side="left")

    tk.Label(
        top_inner, text="v1.0  •  Stage 3",
        font=("Segoe UI", 9),
        bg=BG_CARD, fg=TEXT_MUTED
    ).pack(side="right")

    center = tk.Frame(root, bg=BG_NAVY)
    center.pack(side="top", expand=True, fill="both")
    center.grid_columnconfigure(0, weight=1)

    panel = tk.Frame(center, bg=BG_CARD, padx=36, pady=28)
    panel.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(
        panel, text="Create Account",
        font=("Segoe UI", 22, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack()

    tk.Label(
        panel, text="Register a new Tester or Developer account.",
        font=("Segoe UI", 10),
        bg=BG_CARD, fg=ACCENT_CYAN
    ).pack(pady=(4, 16))

    tk.Label(
        panel, text="Username", font=("Segoe UI", 10, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(anchor="w")
    username_entry = tk.Entry(panel, font=("Segoe UI", 11), width=32)
    username_entry.pack(pady=(4, 12))
    username_entry.focus_set()

    tk.Label(
        panel, text="Password", font=("Segoe UI", 10, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(anchor="w")
    password_entry = tk.Entry(panel, font=("Segoe UI", 11), width=32, show="*")
    password_entry.pack(pady=(4, 12))

    tk.Label(
        panel, text="Confirm Password", font=("Segoe UI", 10, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(anchor="w")
    confirm_entry = tk.Entry(panel, font=("Segoe UI", 11), width=32, show="*")
    confirm_entry.pack(pady=(4, 12))

    tk.Label(
        panel, text="Role", font=("Segoe UI", 10, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(anchor="w")
    role_var = tk.StringVar(value="Select role")
    role_menu = tk.OptionMenu(panel, role_var, "Tester", "Developer")
    role_menu.config(
        font=("Segoe UI", 11), width=28,
        bg=TEXT_WHITE, fg=BG_NAVY,
        relief="flat", cursor="hand2"
    )
    role_menu.pack(pady=(4, 6))

    show_var = tk.BooleanVar(value=False)

    def toggle_passwords():
        char = "" if show_var.get() else "*"
        password_entry.config(show=char)
        confirm_entry.config(show=char)

    tk.Checkbutton(
        panel, text="Show password", variable=show_var,
        command=toggle_passwords,
        font=("Segoe UI", 9),
        bg=BG_CARD, fg=TEXT_MUTED,
        activebackground=BG_CARD, activeforeground=TEXT_WHITE,
        selectcolor=BG_CARD, cursor="hand2"
    ).pack(anchor="w", pady=(0, 4))

    error_label = tk.Label(
        panel, text="", font=("Segoe UI", 9),
        bg=BG_CARD, fg="#F87171", wraplength=300, justify="center"
    )
    error_label.pack(pady=(4, 8))

    def do_register():
        username = username_entry.get().strip()
        password = password_entry.get()
        confirm = confirm_entry.get()
        role = role_var.get()

        if not username or not password or not confirm:
            error_label.config(text="Please fill in all fields.")
            return

        if password != confirm:
            error_label.config(text="Passwords do not match. Please try again.")
            return

        if role not in ("Tester", "Developer"):
            error_label.config(text="Please select a role (Tester or Developer).")
            return

        ok, msg = register_user(username, password, role)

        if not ok:
            error_label.config(text=msg)
            return

        error_label.config(text="")
        messagebox.showinfo("Registration Successful", f"{msg}\nYou can now log in as {username} ({role}).")
        show_login()

    create_btn = tk.Button(
        panel, text="Create Account", command=do_register,
        font=("Segoe UI", 11, "bold"),
        bg=ACCENT_TEAL, fg=TEXT_WHITE,
        activebackground=ACCENT_TEAL_HOVER, activeforeground=TEXT_WHITE,
        relief="flat", bd=0, pady=8, width=28, cursor="hand2"
    )
    create_btn.pack(pady=(4, 8))
    add_hover(create_btn, ACCENT_TEAL, ACCENT_TEAL_HOVER)

    back_btn = tk.Button(
        panel, text="Back to Login", command=show_login,
        font=("Segoe UI", 10),
        bg="#334155", fg=TEXT_WHITE,
        activebackground="#475569", activeforeground=TEXT_WHITE,
        relief="flat", bd=0, pady=6, width=28, cursor="hand2"
    )
    back_btn.pack()
    add_hover(back_btn, "#334155", "#475569")

    username_entry.bind("<Return>", lambda e: do_register())
    password_entry.bind("<Return>", lambda e: do_register())
    confirm_entry.bind("<Return>", lambda e: do_register())


def _dashboard_header(dashboard_title):
    top_bar = tk.Frame(root, bg=BG_CARD, height=60)
    top_bar.pack(side="top", fill="x")
    top_bar.pack_propagate(False)

    top_inner = tk.Frame(top_bar, bg=BG_CARD)
    top_inner.pack(expand=True, fill="both", padx=24)

    left = tk.Frame(top_inner, bg=BG_CARD)
    left.pack(side="left", fill="y")

    tk.Label(
        left, text="\U0001F3AE", font=("Segoe UI", 20),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(side="left", padx=(0, 10))

    tk.Label(
        left, text="GameBugHub  •  " + dashboard_title,
        font=("Segoe UI", 11, "bold"),
        bg=BG_CARD, fg=TEXT_WHITE
    ).pack(side="left")

    right = tk.Frame(top_inner, bg=BG_CARD)
    right.pack(side="right", fill="y")

    tk.Label(
        right, text=f"{current_user}  •  {current_role}",
        font=("Segoe UI", 10),
        bg=BG_CARD, fg=TEXT_MUTED
    ).pack(side="left", padx=(0, 12))

    logout_btn = tk.Button(
        right, text="Logout", command=logout,
        font=("Segoe UI", 10, "bold"),
        bg="#334155", fg=TEXT_WHITE,
        activebackground="#475569", activeforeground=TEXT_WHITE,
        relief="flat", bd=0, padx=14, pady=4, cursor="hand2"
    )
    logout_btn.pack(side="left")
    add_hover(logout_btn, "#334155", "#475569")


def _summary_cards(parent, cards):
    row = tk.Frame(parent, bg=BG_NAVY)
    row.pack(pady=(0, 16))

    for icon, count, label in cards:
        card = tk.Frame(row, bg=BG_CARD, padx=28, pady=16)
        card.pack(side="left", padx=10)
        tk.Label(
            card, text=icon, font=("Segoe UI", 24),
            bg=BG_CARD, fg=ACCENT_CYAN
        ).pack()
        tk.Label(
            card, text=str(count), font=("Segoe UI", 26, "bold"),
            bg=BG_CARD, fg=TEXT_WHITE
        ).pack()
        tk.Label(
            card, text=label, font=("Segoe UI", 10),
            bg=BG_CARD, fg=TEXT_MUTED
        ).pack()


def show_tester_dashboard():
    clear_screen()
    root.configure(bg=BG_NAVY)
    _dashboard_header("Tester Dashboard")

    center = tk.Frame(root, bg=BG_NAVY)
    center.pack(side="top", expand=True, fill="both", padx=40, pady=20)

    tk.Label(
        center, text=f"Welcome back, {current_user}!",
        font=("Segoe UI", 26, "bold"),
        bg=BG_NAVY, fg=TEXT_WHITE
    ).pack(pady=(10, 4))

    tk.Label(
        center, text="Test your game, report issues, and help improve game quality.",
        font=("Segoe UI", 11),
        bg=BG_NAVY, fg=TEXT_MUTED
    ).pack(pady=(0, 20))

    total, open_bugs, resolved = get_bug_counts(tester=current_user)
    _summary_cards(center, [
        ("\U0001F41E", total, "Total Bugs Reported"),
        ("\U0001F4CB", open_bugs, "Open Bugs"),
        ("\u2705", resolved, "Resolved Bugs"),
    ])

    report_btn = tk.Button(
        center, text="Report a Bug",
        command=lambda: messagebox.showinfo(
            "Report a Bug",
            "Bug reporting will be implemented in Stage 5."
        ),
        font=("Segoe UI", 12, "bold"),
        bg=ACCENT_TEAL, fg=TEXT_WHITE,
        activebackground=ACCENT_TEAL_HOVER, activeforeground=TEXT_WHITE,
        relief="flat", bd=0, padx=10, pady=8,
        width=20, cursor="hand2"
    )
    report_btn.pack(pady=(4, 8))
    add_hover(report_btn, ACCENT_TEAL, ACCENT_TEAL_HOVER)

    tk.Label(
        center, text="Role: Tester  •  Counts refresh each time the dashboard opens.",
        font=("Segoe UI", 9),
        bg=BG_NAVY, fg=TEXT_MUTED
    ).pack(pady=(8, 0))


def show_developer_dashboard():
    clear_screen()
    root.configure(bg=BG_NAVY)
    _dashboard_header("Developer Dashboard")

    center = tk.Frame(root, bg=BG_NAVY)
    center.pack(side="top", expand=True, fill="both", padx=40, pady=20)

    tk.Label(
        center, text=f"Welcome back, {current_user}!",
        font=("Segoe UI", 26, "bold"),
        bg=BG_NAVY, fg=TEXT_WHITE
    ).pack(pady=(10, 4))

    tk.Label(
        center, text="Review reported issues, monitor progress, and prepare fixes for your game.",
        font=("Segoe UI", 11),
        bg=BG_NAVY, fg=TEXT_MUTED
    ).pack(pady=(0, 20))

    total, open_bugs, resolved = get_bug_counts()
    _summary_cards(center, [
        ("\U0001F41E", total, "Total Bugs"),
        ("\U0001F4CB", open_bugs, "Open Bugs"),
        ("\u2705", resolved, "Resolved Bugs"),
    ])

    view_btn = tk.Button(
        center, text="View Bug Reports",
        command=lambda: messagebox.showinfo(
            "View Bug Reports",
            "Bug report management will be implemented in Stage 5."
        ),
        font=("Segoe UI", 12, "bold"),
        bg=ACCENT_BLUE, fg=TEXT_WHITE,
        activebackground=ACCENT_BLUE_HOVER, activeforeground=TEXT_WHITE,
        relief="flat", bd=0, padx=10, pady=8,
        width=20, cursor="hand2"
    )
    view_btn.pack(pady=(4, 8))
    add_hover(view_btn, ACCENT_BLUE, ACCENT_BLUE_HOVER)

    tk.Label(
        center, text="Role: Developer  •  Counts refresh each time the dashboard opens.",
        font=("Segoe UI", 9),
        bg=BG_NAVY, fg=TEXT_MUTED
    ).pack(pady=(8, 0))


init_db()

print("Database initialized successfully!")


root = tk.Tk()
root.title("Game Development Asset and Bug Tracking Hub")
center_window(root, 1100, 700)
root.minsize(900, 600)
root.configure(bg=BG_NAVY)

show_welcome()

root.mainloop()
