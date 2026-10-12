"""Embedded Developer prototype-submission form."""

import sqlite3
from collections.abc import Callable
from tkinter import filedialog, messagebox
from typing import Any

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


class PrototypeSubmission(ctk.CTkFrame):
    def __init__(
        self,
        master: Any,
        developer: str,
        submit_prototype: Callable[..., tuple[bool, str, int | None]],
        on_cancel: Callable[[], None],
        on_submitted: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color=BG_NAVY, corner_radius=0)
        self.developer = developer
        self.submit_prototype = submit_prototype
        self.on_cancel = on_cancel
        self.on_submitted = on_submitted
        self._submitting = False
        self.build_path = ""
        self.thumbnail_path = ""

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 16))
        ctk.CTkLabel(
            heading,
            text="Submit a Game Prototype",
            font=("Segoe UI", 24, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            heading,
            text=f"Developer: {developer}  •  Choose Draft to keep it private or Open for Testing to publish it.",
            font=("Segoe UI", 11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        form = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=BG_BORDER,
        )
        form.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 18))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)

        self.name = self._entry(form, "Game name", 0, 0)
        self.version = self._entry(form, "Version", 0, 1)
        self.genre = self._entry(form, "Genre", 2, 0)
        self.testing_status = ctk.CTkOptionMenu(
            form,
            values=["Draft", "Open for Testing"],
            fg_color=BG_INPUT,
            button_color=BG_CARD,
            button_hover_color=BG_BORDER,
            dropdown_fg_color=BG_CARD,
            dropdown_hover_color=ACCENT_BLUE,
            text_color=TEXT_MAIN,
            dropdown_text_color=TEXT_MAIN,
            corner_radius=9,
        )
        self._label(form, "Testing status", 2, 1)
        self.testing_status.grid(row=3, column=1, sticky="ew", padx=12, pady=(3, 8))

        self.description = self._textbox(form, "Description", 4)
        self.instructions = self._textbox(form, "Testing instructions", 6)

        build_row = ctk.CTkFrame(form, fg_color="transparent")
        build_row.grid(row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=(3, 8))
        build_row.grid_columnconfigure(0, weight=1)
        self.build_entry = ctk.CTkEntry(
            build_row,
            height=38,
            placeholder_text="Build URL or local build path",
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_color=BG_BORDER,
            corner_radius=9,
        )
        self.build_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            build_row,
            text="Choose File",
            width=112,
            height=38,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_BORDER,
            text_color=TEXT_MAIN,
            command=self._choose_build,
        ).grid(row=0, column=1, padx=(8, 0))

        thumbnail_row = ctk.CTkFrame(form, fg_color="transparent")
        thumbnail_row.grid(row=9, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
        thumbnail_row.grid_columnconfigure(0, weight=1)
        self.thumbnail_label = ctk.CTkLabel(
            thumbnail_row,
            text="Thumbnail is optional",
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.thumbnail_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            thumbnail_row,
            text="Choose Thumbnail",
            width=150,
            height=34,
            corner_radius=9,
            fg_color=BG_CARD,
            hover_color=BG_BORDER,
            text_color=TEXT_MAIN,
            command=self._choose_thumbnail,
        ).grid(row=0, column=1, padx=(8, 0))

        self.error_label = ctk.CTkLabel(
            form,
            text="",
            font=("Segoe UI", 10),
            text_color="#F87171",
            wraplength=700,
            justify="left",
        )
        self.error_label.grid(row=10, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 5))

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=11, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 16))
        ctk.CTkButton(
            actions,
            text="Save Prototype",
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

    def _label(self, parent: ctk.CTkFrame, text: str, row: int, column: int = 0) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            text_color=TEXT_MAIN,
        ).grid(row=row, column=column, sticky="w", padx=12, pady=(10, 0))

    def _entry(self, parent: ctk.CTkFrame, label: str, row: int, column: int) -> ctk.CTkEntry:
        self._label(parent, label, row, column)
        entry = ctk.CTkEntry(
            parent,
            height=38,
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_color=BG_BORDER,
            corner_radius=9,
        )
        entry.grid(row=row + 1, column=column, sticky="ew", padx=12, pady=(3, 8))
        return entry

    def _textbox(self, parent: ctk.CTkFrame, label: str, row: int) -> ctk.CTkTextbox:
        self._label(parent, label, row)
        textbox = ctk.CTkTextbox(
            parent,
            height=68,
            fg_color=BG_INPUT,
            text_color=TEXT_MAIN,
            border_color=BG_BORDER,
            border_width=1,
            corner_radius=9,
            wrap="word",
        )
        textbox.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=12, pady=(3, 8))
        return textbox

    def _choose_build(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select game build",
            filetypes=[("All files", "*.*")],
        )
        if path:
            self.build_path = path
            self.build_entry.delete(0, "end")
            self.build_entry.insert(0, path)

    def _choose_thumbnail(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select game thumbnail",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.thumbnail_path = path
            self.thumbnail_label.configure(text=path)

    def _submit(self) -> None:
        if self._submitting:
            return
        name = self.name.get().strip()
        description = self.description.get("1.0", "end").strip()
        version = self.version.get().strip()
        genre = self.genre.get().strip()
        build_path = self.build_entry.get().strip()
        instructions = self.instructions.get("1.0", "end").strip()
        if not all((name, description, version, genre, build_path, instructions)):
            self.error_label.configure(text="Complete all required prototype fields.")
            return

        self._submitting = True
        self.error_label.configure(text="Saving prototype...")
        self.update_idletasks()
        try:
            ok, message, game_id = self.submit_prototype(
                self.developer,
                name,
                description,
                version,
                genre,
                build_path,
                instructions,
                self.testing_status.get(),
                self.thumbnail_path,
            )
        except (sqlite3.Error, ValueError) as error:
            self.error_label.configure(text=f"Could not save prototype: {error}")
            self._submitting = False
            return
        if not ok:
            self.error_label.configure(text=message)
            self._submitting = False
            return

        messagebox.showinfo(
            "Prototype Saved",
            f"{message}\nGame ID: {game_id}",
            parent=self.winfo_toplevel(),
        )
        self.on_submitted()
