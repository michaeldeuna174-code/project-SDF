import sqlite3
from collections.abc import Callable
from typing import Any
from tkinter import filedialog, messagebox

import customtkinter as ctk


BG_NAVY = "#0B1120"
BG_PANEL = "#17263D"
BG_CARD = "#1B2D47"
BG_INPUT = "#0D1728"
BG_BORDER = "#2A3C56"
ACCENT_BLUE = "#3B82F6"
ACCENT_BLUE_HOVER = "#2563EB"
ACCENT_TEAL = "#14B8A6"
ACCENT_TEAL_HOVER = "#0F9F92"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#94A3B8"


class BugReportForm(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        username: str,
        game: dict[str, Any],
        submit_report: Callable[..., tuple[bool, str, int | None]],
        on_cancel: Callable[[], None],
        on_submitted: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color=BG_NAVY, corner_radius=0)
        self.username = username
        self.game = game
        self.submit_report = submit_report
        self.on_cancel = on_cancel
        self.on_submitted = on_submitted
        self._submitting = False

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 14))
        heading.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            heading,
            text=f"Report a Bug  /  {game['name']}",
            font=("Segoe UI", 24, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            heading,
            text=f"Testing as {username}  •  Developer: {game['owner']}",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.form = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=BG_BORDER,
        )
        self.form.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 18))
        self.form.grid_columnconfigure(0, weight=1)

        self.title_entry = self._entry_field("Bug title", 0)
        self.severity = ctk.CTkOptionMenu(
            self.form,
            values=["Low", "Medium", "High", "Critical"],
            fg_color=BG_INPUT,
            button_color=BG_CARD,
            button_hover_color=BG_BORDER,
            text_color=TEXT_MAIN,
            dropdown_fg_color=BG_CARD,
            dropdown_hover_color=ACCENT_BLUE,
            dropdown_text_color=TEXT_MAIN,
            corner_radius=9,
        )
        self._field_label("Severity", 2)
        self.severity.grid(row=3, column=0, sticky="ew", padx=22, pady=(3, 12))

        self.description = self._textbox_field("Description", 4)
        self.steps = self._textbox_field("Steps to reproduce", 6)
        self.expected = self._textbox_field("Expected result", 8)
        self.actual = self._textbox_field("Actual result", 10)

        attachment_row = ctk.CTkFrame(self.form, fg_color="transparent")
        attachment_row.grid(row=12, column=0, sticky="ew", padx=22, pady=(3, 12))
        attachment_row.grid_columnconfigure(0, weight=1)
        self.attachment_path = ""
        self.attachment_label = ctk.CTkLabel(
            attachment_row,
            text="No screenshot attached",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.attachment_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            attachment_row,
            text="Choose Screenshot",
            width=150,
            height=34,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_BORDER,
            text_color=TEXT_MAIN,
            command=self._choose_screenshot,
        ).grid(row=0, column=1, padx=(10, 0))

        self.error_label = ctk.CTkLabel(
            self.form,
            text="",
            font=("Segoe UI", 10),
            text_color="#F87171",
            wraplength=650,
            justify="left",
        )
        self.error_label.grid(row=13, column=0, sticky="w", padx=22, pady=(0, 4))

        actions = ctk.CTkFrame(self.form, fg_color="transparent")
        actions.grid(row=14, column=0, sticky="ew", padx=22, pady=(4, 18))
        ctk.CTkButton(
            actions,
            text="Submit Report",
            height=40,
            corner_radius=9,
            fg_color=ACCENT_TEAL,
            hover_color=ACCENT_TEAL_HOVER,
            text_color=TEXT_MAIN,
            command=self._submit,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            actions,
            text="Cancel",
            height=40,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_BORDER,
            text_color=TEXT_MAIN,
            command=self.on_cancel,
        ).pack(side="left")

    def _field_label(self, label: str, row: int) -> None:
        ctk.CTkLabel(
            self.form,
            text=label,
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=row, column=0, sticky="w", padx=22, pady=(9, 0))

    def _entry_field(self, label: str, row: int) -> ctk.CTkEntry:
        self._field_label(label, row)
        entry = ctk.CTkEntry(
            self.form,
            height=38,
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_color=BG_BORDER,
            corner_radius=9,
        )
        entry.grid(row=row + 1, column=0, sticky="ew", padx=22, pady=(3, 8))
        return entry

    def _textbox_field(self, label: str, row: int) -> ctk.CTkTextbox:
        self._field_label(label, row)
        textbox = ctk.CTkTextbox(
            self.form,
            height=72,
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_color=BG_BORDER,
            border_width=1,
            corner_radius=9,
            wrap="word",
        )
        textbox.grid(row=row + 1, column=0, sticky="ew", padx=22, pady=(3, 8))
        return textbox

    def _choose_screenshot(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Attach screenshot",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.attachment_path = path
            self.attachment_label.configure(text=path)

    def _submit(self) -> None:
        if self._submitting:
            return
        values = (
            self.title_entry.get().strip(),
            self.severity.get(),
            self.description.get("1.0", "end").strip(),
            self.steps.get("1.0", "end").strip(),
            self.expected.get("1.0", "end").strip(),
            self.actual.get("1.0", "end").strip(),
        )
        if not all(values[index] for index in (0, 2, 3, 4, 5)):
            self.error_label.configure(text="Complete the title, description, steps, expected result, and actual result.")
            return

        self._submitting = True
        self.error_label.configure(text="Submitting report...")
        self.update_idletasks()
        try:
            ok, message, report_id = self.submit_report(
                self.username,
                self.game["id"],
                values[0],
                values[1],
                values[2],
                values[3],
                values[4],
                values[5],
                self.attachment_path,
            )
        except (sqlite3.Error, ValueError) as error:
            self.error_label.configure(text=f"Could not submit report: {error}")
            self._submitting = False
            return

        if not ok:
            self.error_label.configure(text=message)
            self._submitting = False
            return

        messagebox.showinfo(
            "Report Submitted",
            f"{message}\nReport ID: {report_id}",
            parent=self.winfo_toplevel(),
        )
        self.on_submitted()
