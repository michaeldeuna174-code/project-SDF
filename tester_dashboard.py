import sqlite3
import webbrowser
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit
from tkinter import messagebox

import customtkinter as ctk


BG_NAVY = "#0B1120"
BG_SIDEBAR = "#111C30"
BG_PANEL = "#17263D"
BG_CARD = "#1B2D47"
BG_INPUT = "#0D1728"
BG_BORDER = "#2A3C56"
ACCENT_BLUE = "#3B82F6"
ACCENT_BLUE_HOVER = "#2563EB"
ACCENT_TEAL = "#14B8A6"
ACCENT_TEAL_HOVER = "#0F9F92"
ACCENT_CYAN = "#22D3EE"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#94A3B8"

NAV_ITEMS = (
    ("dashboard", "Dashboard"),
    ("browse_games", "Browse Games"),
    ("my_bug_reports", "My Bug Reports"),
)


class TesterDashboard(ctk.CTkFrame):
    """Dashboard view that can be embedded in an existing CTk window."""

    def __init__(
        self,
        master: Any,
        username: str,
        get_bug_counts: Callable[[str], tuple[int, int, int]],
        get_open_games: Callable[[], list[dict[str, Any]]],
        get_tester_bug_reports: Callable[..., list[dict[str, Any]]],
        on_logout: Callable[[], None],
        on_open_reports: Callable[[], None] | None = None,
        on_report_bug: Callable[[dict[str, Any]], None] | None = None,
        on_view_report: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=BG_NAVY, corner_radius=0)
        self.username = username
        self.get_bug_counts = get_bug_counts
        self.get_open_games = get_open_games
        self.get_tester_bug_reports = get_tester_bug_reports
        self.on_logout = on_logout
        self.on_open_reports = on_open_reports
        self.on_report_bug = on_report_bug
        self.on_view_report = on_view_report
        self._active_page = "dashboard"
        self._games: list[dict[str, Any]] = []
        self._reports: list[dict[str, Any]] = []
        self._stats = (0, 0, 0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_content()
        self.refresh()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=224, fg_color=BG_SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            sidebar,
            text="🎮  GameBugHub",
            font=("Segoe UI", 17, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(26, 4))
        ctk.CTkLabel(
            sidebar,
            text="TESTER WORKSPACE",
            font=("Segoe UI", 9, "bold"),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 28))

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        for row, (route, label) in enumerate(NAV_ITEMS, start=2):
            button = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                height=42,
                corner_radius=10,
                font=("Segoe UI", 11, "bold"),
                fg_color=BG_PANEL if route == self._active_page else "transparent",
                hover_color=BG_PANEL,
                text_color=ACCENT_CYAN if route == self._active_page else TEXT_MUTED,
                command=lambda selected_route=route: self._open_page(selected_route),
            )
            button.grid(row=row, column=0, sticky="ew", padx=14, pady=4)
            self._nav_buttons[route] = button

        ctk.CTkFrame(sidebar, height=1, fg_color=BG_BORDER).grid(
            row=6, column=0, sticky="ew", padx=18, pady=(14, 12)
        )
        ctk.CTkButton(
            sidebar,
            text="Log out",
            anchor="w",
            height=42,
            corner_radius=10,
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color=BG_PANEL,
            text_color=TEXT_MUTED,
            command=self.on_logout,
        ).grid(row=7, column=0, sticky="ew", padx=14, pady=(0, 20))

    def _build_content(self) -> None:
        host = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        host.grid(row=0, column=1, sticky="nsew", padx=22, pady=18)
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)
        self.content = ctk.CTkScrollableFrame(
            host,
            fg_color="transparent",
            scrollbar_button_color=BG_BORDER,
            scrollbar_button_hover_color=ACCENT_BLUE,
        )
        self.content.grid(row=0, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            host, text="", font=("Segoe UI", 10), text_color=ACCENT_CYAN, anchor="w"
        )
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(10, 0))

    def _set_active(self, route: str) -> None:
        self._active_page = route
        for item, button in self._nav_buttons.items():
            active = item == route
            button.configure(
                fg_color=BG_PANEL if active else "transparent",
                text_color=ACCENT_CYAN if active else TEXT_MUTED,
            )

    def _open_page(self, route: str) -> None:
        if route == "dashboard":
            self.show_dashboard()
        elif route == "browse_games":
            self.show_browse_games()
        elif route == "my_bug_reports":
            self._set_active(route)
            if self.on_open_reports is not None:
                self.on_open_reports()
            else:
                self.show_bug_reports()

    def _clear_content(self) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()
        self.content.grid_columnconfigure(0, weight=1)

    def refresh(self) -> None:
        self.status_label.configure(text="Refreshing live game and report data...")
        self.update_idletasks()
        try:
            stats = self.get_bug_counts(self.username)
            games = self.get_open_games()
            reports = self.get_tester_bug_reports(self.username, 3)
        except (sqlite3.Error, ValueError) as error:
            self.status_label.configure(
                text=f"Could not refresh dashboard data: {error}",
                text_color="#F87171",
            )
            return
        self._stats = stats
        self._games = games
        self._reports = reports
        self.status_label.configure(
            text=f"Updated  •  {len(games)} game(s) open for testing",
            text_color=ACCENT_CYAN,
        )
        if self._active_page == "browse_games":
            self.show_browse_games()
        elif self._active_page == "my_bug_reports" and self.on_open_reports is None:
            self.show_bug_reports()
        else:
            self.show_dashboard()

    def show_dashboard(self) -> None:
        self._set_active("dashboard")
        self._clear_content()
        self._dashboard_header()

        stats_row = ctk.CTkFrame(self.content, fg_color="transparent")
        stats_row.grid(row=1, column=0, sticky="ew", pady=(0, 24))
        for column in range(4):
            stats_row.grid_columnconfigure(column, weight=1, uniform="stats")
        self._metric_card(stats_row, 0, len(self._games), "Available Games", ACCENT_CYAN)
        self._metric_card(stats_row, 1, self._stats[0], "Bugs Reported", ACCENT_BLUE)
        self._metric_card(stats_row, 2, self._stats[1], "Open / In Progress", ACCENT_BLUE)
        self._metric_card(stats_row, 3, self._stats[2], "Resolved Bugs", ACCENT_TEAL)

        self._section_header("Available Games", row=2)
        if self._games:
            for row, game in enumerate(self._games[:3], start=3):
                self._game_card(row, game)
        else:
            self._empty_state(
                row=3,
                title="No games are open for testing",
                description="Published prototypes will appear here when a Developer opens them for testing.",
            )
        reports_row = 3 + max(1, min(len(self._games), 3))
        self._section_header(
            "Recent Bug Reports",
            row=reports_row,
            command=self._open_all_reports,
        )
        recent_reports = self._reports[:3]
        if recent_reports:
            for row, report in enumerate(recent_reports, start=reports_row + 1):
                self._report_card(row, report)
        else:
            self._empty_state(
                row=reports_row + 1,
                title="No reports submitted yet",
                description="Bug reports you submit for a game will appear here.",
            )

    def _dashboard_header(self) -> None:
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 24))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=f"Welcome back, {self.username}",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Help make every build more stable. Review bug activity and find a game to test.",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(7, 0))
        ctk.CTkButton(
            header,
            text="Browse Games",
            width=116,
            height=36,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_PANEL,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=BG_BORDER,
            command=self.show_browse_games,
        ).grid(row=0, column=1, rowspan=2, padx=(12, 0))
        ctk.CTkButton(
            header,
            text="Refresh",
            width=96,
            height=36,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_PANEL,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=BG_BORDER,
            command=self.refresh,
        ).grid(row=0, column=2, rowspan=2, padx=(8, 0))

    def _metric_card(
        self, parent: ctk.CTkFrame, column: int, value: int, title: str, accent: str
    ) -> None:
        card = ctk.CTkFrame(
            parent, fg_color=BG_CARD, corner_radius=15,
            border_width=1, border_color=BG_BORDER,
        )
        card.grid(row=0, column=column, sticky="ew", padx=6)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text=title.upper(), font=("Segoe UI", 9, "bold"), text_color=TEXT_MUTED
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(14, 5))
        ctk.CTkLabel(
            card, text=str(value), font=("Segoe UI", 28, "bold"), text_color=accent
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(0, 13))

    def _section_header(
        self,
        text: str,
        row: int,
        command: Callable[[], None] | None = None,
    ) -> None:
        section = ctk.CTkFrame(self.content, fg_color="transparent")
        section.grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 9))
        section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            section, text=text, font=("Segoe UI", 17, "bold"), text_color=TEXT_MAIN
        ).grid(row=0, column=0, sticky="w")
        if command is not None:
            ctk.CTkButton(
                section,
                text="View All Reports",
                width=136,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                hover_color=BG_PANEL,
                text_color=ACCENT_CYAN,
                command=command,
            ).grid(row=0, column=1)

    def _empty_state(self, row: int, title: str, description: str) -> None:
        panel = ctk.CTkFrame(
            self.content, fg_color=BG_PANEL, corner_radius=14,
            border_width=1, border_color=BG_BORDER,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        ctk.CTkLabel(
            panel, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN
        ).pack(anchor="w", padx=17, pady=(14, 3))
        ctk.CTkLabel(
            panel, text=description, font=("Segoe UI", 10), text_color=TEXT_MUTED,
            wraplength=760, justify="left",
        ).pack(anchor="w", padx=17, pady=(0, 14))

    def show_browse_games(self) -> None:
        self._set_active("browse_games")
        self._clear_content()
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 18))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="Browse Games", font=("Segoe UI", 25, "bold"), text_color=TEXT_MAIN
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header, text="Refresh", width=100, height=36, corner_radius=9,
            fg_color=BG_CARD, hover_color=BG_PANEL, text_color=TEXT_MAIN,
            border_width=1, border_color=BG_BORDER, command=self.refresh,
        ).grid(row=0, column=1, padx=(10, 0))

        filters = ctk.CTkFrame(self.content, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 16))
        filters.grid_columnconfigure(0, weight=1)
        search = ctk.CTkEntry(
            filters,
            height=38,
            placeholder_text="Search game name or description",
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_color=BG_BORDER,
            corner_radius=9,
        )
        search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        genres = sorted({str(game.get("genre") or "") for game in self._games if game.get("genre")})
        genre_var = ctk.StringVar(value="All Genres")
        genre_filter = ctk.CTkOptionMenu(
            filters,
            values=["All Genres", *genres],
            variable=genre_var,
            width=170,
            height=38,
            corner_radius=9,
            fg_color=BG_CARD,
            button_color=BG_CARD,
            button_hover_color=BG_PANEL,
            dropdown_fg_color=BG_PANEL,
            dropdown_hover_color=ACCENT_BLUE,
            text_color=TEXT_MAIN,
            dropdown_text_color=TEXT_MAIN,
        )
        genre_filter.grid(row=0, column=1)
        self.game_results = ctk.CTkFrame(self.content, fg_color="transparent")
        self.game_results.grid(row=2, column=0, sticky="ew")
        self.game_results.grid_columnconfigure(0, weight=1)

        def apply_filters() -> None:
            for widget in self.game_results.winfo_children():
                widget.destroy()
            needle = search.get().strip().casefold()
            genre = genre_var.get()
            visible = [
                game for game in self._games
                if (genre == "All Genres" or game.get("genre") == genre)
                and needle in (
                    f"{game.get('name', '')} {game.get('description', '')} "
                    f"{game.get('owner', '')} {game.get('version', '')}"
                ).casefold()
            ]
            if not visible:
                ctk.CTkLabel(
                    self.game_results,
                    text="No open prototypes match these filters.",
                    font=("Segoe UI", 12),
                    text_color=TEXT_MUTED,
                ).grid(row=0, column=0, sticky="w", padx=16, pady=20)
                return
            for row, game in enumerate(visible):
                self._game_card(row, game, parent=self.game_results)

        def on_search_change(event: Any) -> None:
            if event.widget is search:
                apply_filters()

        def on_genre_change(variable_name: str, _index: str, _mode: str) -> None:
            if variable_name == str(genre_var) and _index is not None and _mode == "write":
                apply_filters()

        search.bind("<KeyRelease>", on_search_change)
        genre_var.trace_add("write", on_genre_change)
        apply_filters()

    def _game_card(
        self,
        row: int,
        game: dict[str, Any],
        parent: ctk.CTkFrame | None = None,
    ) -> None:
        container = parent or self.content
        card = ctk.CTkFrame(
            container,
            fg_color=BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=BG_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="GAME",
            width=74,
            height=64,
            fg_color=BG_PANEL,
            corner_radius=10,
            font=("Segoe UI", 11, "bold"),
            text_color=ACCENT_CYAN,
        ).grid(row=0, column=1, rowspan=3, padx=(8, 18), pady=(12, 4), sticky="n")
        ctk.CTkLabel(
            card,
            text=game["name"],
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 3))
        detail = (
            f"{game.get('genre', 'Genre n/a')}  •  v{game.get('version', 'n/a')}  •  "
            f"Developer: {game.get('owner', 'n/a')}  •  "
            f"Submitted: {game.get('submission_date') or 'Date unavailable'}"
        )
        ctk.CTkLabel(
            card,
            text=detail,
            font=("Segoe UI", 9),
            text_color=ACCENT_CYAN,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text=game.get("description", ""),
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=740,
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 12))
        ctk.CTkButton(
            actions, text="View Details", width=112, height=32, corner_radius=8,
            fg_color=BG_PANEL, hover_color=ACCENT_BLUE_HOVER, text_color=TEXT_MAIN,
            command=lambda selected=game: self._show_game_details(selected),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions, text="Start Testing", width=112, height=32, corner_radius=8,
            fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE_HOVER, text_color=TEXT_MAIN,
            command=lambda selected=game: self._show_game_details(selected, start=True),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions, text="Report a Bug", width=112, height=32, corner_radius=8,
            fg_color=ACCENT_TEAL, hover_color=ACCENT_TEAL_HOVER, text_color=TEXT_MAIN,
            command=lambda selected=game: self._report_game(selected),
        ).pack(side="left", padx=4)

    def _show_game_details(self, game: dict[str, Any], start: bool = False) -> None:
        details = ctk.CTkToplevel(self.winfo_toplevel())
        details.title(f"{game['name']} — Game Details")
        details.geometry("640x520")
        details.configure(fg_color=BG_NAVY)
        details.transient(self.winfo_toplevel())
        details.grab_set()

        content = ctk.CTkScrollableFrame(details, fg_color=BG_PANEL, corner_radius=14)
        content.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(
            content, text=game["name"], font=("Segoe UI", 22, "bold"), text_color=TEXT_MAIN
        ).pack(anchor="w", padx=18, pady=(18, 8))
        information = (
            f"Developer: {game['owner']}\n"
            f"Version: {game['version']}\n"
            f"Genre: {game['genre']}\n"
            f"Testing status: {game['testing_status']}\n"
            f"Submitted: {game['submission_date']}\n"
            f"Build link/path: {game['build_path']}\n\n"
            f"Description\n{game['description']}\n\n"
            f"Testing instructions\n{game['instructions']}"
        )
        ctk.CTkLabel(
            content, text=information, font=("Segoe UI", 11), text_color=TEXT_MUTED,
            wraplength=540, justify="left", anchor="w",
        ).pack(anchor="w", padx=18, pady=(0, 18))
        if start:
            parts = urlsplit(game["build_path"])
            if parts.scheme in ("http", "https") and parts.netloc:
                ctk.CTkButton(
                    content,
                    text="Open Build Link",
                    fg_color=ACCENT_BLUE,
                    hover_color=ACCENT_BLUE_HOVER,
                    text_color=TEXT_MAIN,
                    command=lambda: self._open_web_build(game["build_path"]),
                ).pack(anchor="w", padx=18, pady=(0, 10))
            else:
                ctk.CTkLabel(
                    content,
                    text="Local builds are not launched by GameBugHub. Use the path above and follow the instructions in your trusted test environment.",
                    font=("Segoe UI", 10),
                    text_color=ACCENT_CYAN,
                    wraplength=540,
                    justify="left",
                ).pack(anchor="w", padx=18, pady=(0, 10))
        ctk.CTkButton(
            content,
            text="Close",
            fg_color=BG_CARD,
            hover_color=BG_BORDER,
            text_color=TEXT_MAIN,
            command=details.destroy,
        ).pack(anchor="w", padx=18, pady=(0, 18))

    def _open_web_build(self, url: str) -> None:
        try:
            opened = webbrowser.open(url, new=2)
        except webbrowser.Error as error:
            messagebox.showerror("Could Not Open Link", str(error), parent=self.winfo_toplevel())
            return
        if not opened:
            messagebox.showerror(
                "Could Not Open Link",
                "No browser could open the build link.",
                parent=self.winfo_toplevel(),
            )

    def _report_game(self, game: dict[str, Any]) -> None:
        if self.on_report_bug is None:
            messagebox.showerror(
                "Report Form Unavailable",
                "The host application has not connected the bug-report form.",
                parent=self.winfo_toplevel(),
            )
            return
        self.on_report_bug(game)

    def _report_card(self, row: int, report: dict[str, Any]) -> None:
        card = ctk.CTkFrame(
            self.content, fg_color=BG_PANEL, corner_radius=12,
            border_width=1, border_color=BG_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=report["title"],
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            card,
            text=(
                f"{report['game_name']}  •  {report['severity']}  •  "
                f"{report['status']}  •  {report.get('submitted_at') or 'Date unavailable'}"
            ),
            font=("Segoe UI", 9),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        ctk.CTkButton(
            card,
            text="View Report",
            width=100,
            height=30,
            corner_radius=8,
            fg_color=BG_CARD,
            hover_color=ACCENT_BLUE_HOVER,
            text_color=TEXT_MAIN,
            command=lambda report_id=report["id"]: self._view_report(report_id),
        ).grid(row=0, column=1, rowspan=2, padx=12, pady=8)

    def _view_report(self, report_id: int) -> None:
        if self.on_view_report is None:
            self._open_page("my_bug_reports")
        else:
            self.on_view_report(report_id)

    def _open_all_reports(self) -> None:
        self._open_page("my_bug_reports")

    def show_bug_reports(self) -> None:
        self._set_active("my_bug_reports")
        self._clear_content()
        self._section_header("My Bug Reports", row=0)
        try:
            reports = self.get_tester_bug_reports(self.username)
        except (sqlite3.Error, ValueError) as error:
            self.status_label.configure(text=f"Could not load reports: {error}", text_color="#F87171")
            return
        if not reports:
            self._empty_state(
                row=1,
                title="No bug reports yet",
                description="Reports you submit will appear here.",
            )
            return
        for row, report in enumerate(reports, start=1):
            self._report_card(row, report)


def build_tester_dashboard(
    parent: Any,
    username: str,
    get_bug_counts: Callable[[str], tuple[int, int, int]],
    get_open_games: Callable[[], list[dict[str, Any]]],
    get_tester_bug_reports: Callable[..., list[dict[str, Any]]],
    on_logout: Callable[[], None],
    on_open_reports: Callable[[], None] | None = None,
    on_report_bug: Callable[[dict[str, Any]], None] | None = None,
    on_view_report: Callable[[int], None] | None = None,
) -> TesterDashboard:
    """Create the dashboard in an existing CTk parent window."""
    return TesterDashboard(
        parent,
        username,
        get_bug_counts,
        get_open_games,
        get_tester_bug_reports,
        on_logout,
        on_open_reports,
        on_report_bug,
        on_view_report,
    )
