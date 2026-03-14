# search bar and filter controls
import customtkinter as ctk

from ui.styles import (
    BG_PANEL,
    BG_INPUT,
    SURFACE,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    PANEL_PADDING,
    PANEL_CORNER_RADIUS,
    BTN_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SearchFilter(ctk.CTkFrame):
    """Search bar and filter dropdowns that control what"""

    def __init__(
        self,
        master,
        speaker_map: dict,
        on_search: callable = None,
        on_speaker_filter: callable = None,
        on_priority_filter: callable = None,
    ):
        super().__init__(
            master,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
        )

        self.speaker_map = speaker_map
        self.on_search = on_search
        self.on_speaker_filter = on_speaker_filter
        self.on_priority_filter = on_priority_filter

        self._build_ui()

    def _build_ui(self):
        """Construct search bar and filter dropdowns."""

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=PANEL_PADDING,
        )

        self.search_entry = ctk.CTkEntry(
            inner,
            font=FONT_BODY,
            fg_color=BG_INPUT,
            border_color=SURFACE,
            text_color=TEXT_PRIMARY,
            placeholder_text="Search transcript & tasks...",
            height=34,
        )
        self.search_entry.pack(fill="x", pady=(0, SPACING_MD))
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        filter_row = ctk.CTkFrame(inner, fg_color="transparent")
        filter_row.pack(fill="x")

        # Speaker filter
        speaker_label = ctk.CTkLabel(
            filter_row,
            text="Speaker:",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        speaker_label.pack(side="left", padx=(0, SPACING_SM))

        # Build speaker dropdown values
        speaker_options = ["All Speakers"]
        self._speaker_key_map = {"All Speakers": None}

        for key in sorted(self.speaker_map.keys()):
            display = self.speaker_map.get(key, key)
            speaker_options.append(display)
            self._speaker_key_map[display] = key

        self.speaker_var = ctk.StringVar(value="All Speakers")
        self.speaker_dropdown = ctk.CTkComboBox(
            filter_row,
            values=speaker_options,
            variable=self.speaker_var,
            width=150,
            fg_color=BG_INPUT,
            border_color=SURFACE,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=BG_PANEL,
            font=FONT_SMALL,
            state="readonly",
            command=self._on_speaker_change,
        )
        self.speaker_dropdown.pack(side="left", padx=(0, SPACING_MD))

        # Priority filter
        priority_label = ctk.CTkLabel(
            filter_row,
            text="Priority:",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        priority_label.pack(side="left", padx=(0, SPACING_SM))

        self.priority_var = ctk.StringVar(value="All")
        self.priority_dropdown = ctk.CTkComboBox(
            filter_row,
            values=["All", "High", "Medium", "Low"],
            variable=self.priority_var,
            width=110,
            fg_color=BG_INPUT,
            border_color=SURFACE,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=BG_PANEL,
            font=FONT_SMALL,
            state="readonly",
            command=self._on_priority_change,
        )
        self.priority_dropdown.pack(side="left", padx=(0, SPACING_MD))

        # Clear all button
        self.clear_btn = ctk.CTkButton(
            filter_row,
            text="Clear",
            font=FONT_SMALL,
            fg_color=SURFACE,
            hover_color=PRIMARY_HOVER,
            width=60,
            height=28,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._clear_all,
        )
        self.clear_btn.pack(side="right")

    def _on_search_change(self, event=None):
        """Fire search callback on every keystroke."""
        keyword = self.search_entry.get()
        if self.on_search:
            self.on_search(keyword)

    def _on_speaker_change(self, value: str):
        """Fire speaker filter callback."""
        speaker_key = self._speaker_key_map.get(value, None)
        if self.on_speaker_filter:
            self.on_speaker_filter(speaker_key)

        logger.info(f"Speaker filter: {value} ({speaker_key})")

    def _on_priority_change(self, value: str):
        """Fire priority filter callback."""
        priority = None if value == "All" else value.lower()
        if self.on_priority_filter:
            self.on_priority_filter(priority)

        logger.info(f"Priority filter: {value}")

    def _clear_all(self):
        """Reset all filters and search to default."""
        self.search_entry.delete(0, "end")
        self.speaker_var.set("All Speakers")
        self.priority_var.set("All")

        if self.on_search:
            self.on_search("")
        if self.on_speaker_filter:
            self.on_speaker_filter(None)
        if self.on_priority_filter:
            self.on_priority_filter(None)

        logger.info("Filters cleared")

    def update_speaker_options(self, speaker_map: dict):
        """Refresh speaker dropdown after aliasing."""
        self.speaker_map = speaker_map

        speaker_options = ["All Speakers"]
        self._speaker_key_map = {"All Speakers": None}

        for key in sorted(speaker_map.keys()):
            display = speaker_map.get(key, key)
            speaker_options.append(display)
            self._speaker_key_map[display] = key

        self.speaker_dropdown.configure(values=speaker_options)
        self.speaker_var.set("All Speakers")
