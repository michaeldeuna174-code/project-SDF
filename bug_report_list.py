import sqlite3
from collections.abc import Callable
from typing import Any

import customtkinter as ctk


BG_NAVY = "#0B1120"
BG_PANEL = "#17263D"
BG_CARD = "#1B2D47"
BG_BORDER = "#2A3C56"
ACCENT_BLUE = "#3B82F6"
ACCENT_BLUE_HOVER = "#2563EB"
ACCENT_CYAN = "#22D3EE"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#94A3B8"


class BugReportList(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        username: str,
        get_reports: Callable[[str], list[dict[str, Any]]],
        on_back: Callable[[], None],
        on_view_report: Callable[[int, str, str], None],
    ) -> None:
        super().__init__(master, fg_color=BG_NAVY, corner_radius=0)
        self.username = username
        self.get_reports = get_reports
        self.on_back = on_back
        self.on_view_report = on_view_report

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self.list_area = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=BG_BORDER,
            scrollbar_button_hover_color=ACCENT_BLUE,
        )
        self.list_area.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 18))
        self.list_area.grid_columnconfigure(0, weight=1)
        self.refresh()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 18))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="My Bug Reports",
            font=("Segoe UI", 24, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="Refresh",
            width=100,
            height=36,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_PANEL,
            text_color=TEXT_MAIN,
            border_width=1,
            border_color=BG_BORDER,
            command=self.refresh,
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(
            header,
            text="Back",
            width=82,
            height=36,
            corner_radius=9,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            text_color=TEXT_MAIN,
            command=self.on_back,
        ).grid(row=0, column=2, padx=(8, 0))
        self.message = ctk.CTkLabel(
            header,
            text="",
            font=("Segoe UI", 10),
            text_color=ACCENT_CYAN,
        )
        self.message.grid(row=1, column=0, columnspan=3, sticky="w", pady=(7, 0))

    def refresh(self) -> None:
        for widget in self.list_area.winfo_children():
            widget.destroy()
        try:
            reports = self.get_reports(self.username)
        except (sqlite3.Error, ValueError) as error:
            self.message.configure(text=f"Could not load reports: {error}", text_color="#F87171")
            return

        self.message.configure(text=f"{len(reports)} report(s)", text_color=ACCENT_CYAN)
        if not reports:
            ctk.CTkLabel(
                self.list_area,
                text="No bug reports yet",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_MAIN,
            ).grid(row=0, column=0, sticky="w", padx=20, pady=(24, 4))
            ctk.CTkLabel(
                self.list_area,
                text="Reports you submit will appear here.",
                font=("Segoe UI", 11),
                text_color=TEXT_MUTED,
            ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 24))
            return

        for row, report in enumerate(reports):
            self._report_card(row, report)

    def _report_card(self, row: int, report: dict[str, Any]) -> None:
        card = ctk.CTkFrame(
            self.list_area,
            fg_color=BG_PANEL,
            corner_radius=14,
            border_width=1,
            border_color=BG_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", padx=5, pady=6)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=report["title"],
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 3))
        ctk.CTkLabel(
            card,
            text=(
                f"{report['game_name']}  •  {report['severity']}  •  "
                f"{report['status']}  •  {report['submitted_at'] or 'Date unavailable'}"
            ),
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 13))
        ctk.CTkButton(
            card,
            text="View Report",
            width=112,
            height=34,
            corner_radius=8,
            fg_color=BG_CARD,
            hover_color=ACCENT_BLUE_HOVER,
            text_color=TEXT_MAIN,
            command=lambda report_id=report["id"]: self.on_view_report(
                report_id, self.username, "Tester"
            ),
        ).grid(row=0, column=1, rowspan=2, padx=14, pady=10)
