# meeting summary display panel
import customtkinter as ctk

from ui.styles import (
    BG_PANEL,
    SURFACE,
    SURFACE_HOVER,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    SUCCESS,
    WARNING,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_TIMESTAMP,
    PANEL_PADDING,
    PANEL_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SummaryPanel(ctk.CTkFrame):
    """Displays the structured meeting summary produced by"""

    def __init__(
        self,
        master,
        summary: dict,
        on_timestamp_click: callable = None,
    ):
        super().__init__(
            master,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
        )

        self.summary = summary
        self.on_timestamp_click = on_timestamp_click

        self._build_ui()

    def _build_ui(self):
        """Construct the summary sections."""

        header = ctk.CTkLabel(
            self,
            text="Meeting Summary",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        header.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(PANEL_PADDING, SPACING_SM),
        )

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        self.scroll_frame.pack(
            fill="both",
            expand=True,
            padx=SPACING_SM,
            pady=(0, PANEL_PADDING),
        )

        overview = self.summary.get("overview", "")
        if overview:
            self._add_section("Overview", overview)

        decisions = self.summary.get("decisions", [])
        if decisions:
            self._add_section_header("Decisions")
            for decision in decisions:
                self._add_decision_item(decision)

        topics = self.summary.get("topics", [])
        if topics:
            self._add_section_header("Topics Discussed")
            for topic in topics:
                self._add_topic_item(topic)

        timeline = self.summary.get("timeline", [])
        if timeline:
            self._add_section_header("Conversation Flow")
            for entry in timeline:
                self._add_timeline_item(entry)

        if not overview and not decisions and not topics:
            empty = ctk.CTkLabel(
                self.scroll_frame,
                text="No summary available for this meeting.",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
            )
            empty.pack(pady=SPACING_MD)

    def _add_section(self, title: str, text: str):
        """Add a titled text section."""
        self._add_section_header(title)

        body = ctk.CTkLabel(
            self.scroll_frame,
            text=text,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=380,
        )
        body.pack(
            fill="x",
            padx=SPACING_SM,
            pady=(0, SPACING_MD),
        )

    def _add_section_header(self, title: str):
        """Add a section divider with title."""
        header = ctk.CTkLabel(
            self.scroll_frame,
            text=title,
            font=FONT_BODY_BOLD,
            text_color=PRIMARY,
            anchor="w",
        )
        header.pack(
            fill="x",
            padx=SPACING_SM,
            pady=(SPACING_MD, SPACING_SM),
        )

    def _add_decision_item(self, decision: dict):
        """Add a decision entry. Expects dict with 'text' and"""
        # Handle both dict and plain string decisions
        if isinstance(decision, str):
            text = decision
            timestamp = None
        elif isinstance(decision, dict):
            text = decision.get("text", decision.get("topic", ""))
            if not text or text.startswith("{"):
                text = str(decision)[:100]
            timestamp = decision.get("timestamp", decision.get("start", None))
            if timestamp is not None:
                try:
                    timestamp = float(timestamp)
                except (TypeError, ValueError):
                    timestamp = None
        else:
            text = str(decision)[:100]
            timestamp = None

        row = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=SURFACE,
            corner_radius=6,
        )
        row.pack(fill="x", pady=(0, SPACING_SM), padx=SPACING_SM)

        # Decision icon + text
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(
            fill="x",
            padx=SPACING_SM,
            pady=SPACING_SM,
        )

        icon = ctk.CTkLabel(
            content,
            text="✓",
            font=FONT_BODY_BOLD,
            text_color=SUCCESS,
            width=20,
        )
        icon.pack(side="left", padx=(0, SPACING_SM))

        text_label = ctk.CTkLabel(
            content,
            text=text,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=320,
        )
        text_label.pack(side="left", fill="x", expand=True)

        # Clickable timestamp if available
        if timestamp is not None:
            self._add_clickable_timestamp(content, timestamp)
            row.configure(cursor="hand2")

            def on_click(event, t=timestamp):
                self._handle_timestamp_click(t)

            row.bind("<Button-1>", on_click)
            content.bind("<Button-1>", on_click)
            icon.bind("<Button-1>", on_click)
            text_label.bind("<Button-1>", on_click)

    def _add_topic_item(self, topic):
        """Add a topic entry. Handles dicts, strings, and"""
        # Extract text from whatever format we receive
        if isinstance(topic, str):
            text = topic
            timestamp = None
        elif isinstance(topic, dict):
            text = topic.get("text", topic.get("topic", str(topic)))
            timestamp = topic.get("timestamp", topic.get("start", None))
            # Convert numpy floats if present
            if timestamp is not None:
                try:
                    timestamp = float(timestamp)
                except (TypeError, ValueError):
                    timestamp = None
        else:
            text = str(topic)
            timestamp = None

        # Skip entries that look like raw data dumps
        if len(text) > 200 or text.startswith("{") or text.startswith("["):
            text = text[:100] + "..." if len(text) > 100 else text

        row = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="transparent",
        )
        row.pack(fill="x", pady=(0, 2), padx=SPACING_SM)

        bullet = ctk.CTkLabel(
            row,
            text="•",
            font=FONT_BODY,
            text_color=TEXT_MUTED,
            width=15,
        )
        bullet.pack(side="left", anchor="n")

        text_label = ctk.CTkLabel(
            row,
            text=text,
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=330,
        )
        text_label.pack(side="left", fill="x", expand=True)

        if timestamp is not None:
            self._add_clickable_timestamp(row, timestamp)
            row.configure(cursor="hand2")

            def on_click(event, t=timestamp):
                self._handle_timestamp_click(t)

            row.bind("<Button-1>", on_click)
            bullet.bind("<Button-1>", on_click)
            text_label.bind("<Button-1>", on_click)

    def _add_timeline_item(self, entry: dict):
        """Add a timeline entry. Expects dict with 'text',"""
        if isinstance(entry, str):
            text = entry
            timestamp = None
            speaker = None
        else:
            text = entry.get("text", str(entry))
            timestamp = entry.get("timestamp", None)
            speaker = entry.get("speaker", None)

        row = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="transparent",
            cursor="hand2" if timestamp else "arrow",
        )
        row.pack(fill="x", pady=(0, 2), padx=SPACING_SM)

        # Timestamp on the left
        if timestamp is not None:
            time_str = self._format_time(timestamp)
            time_label = ctk.CTkLabel(
                row,
                text=time_str,
                font=FONT_TIMESTAMP,
                text_color=TEXT_MUTED,
                width=45,
            )
            time_label.pack(side="left", padx=(0, SPACING_SM))

            def on_click(event, t=timestamp):
                self._handle_timestamp_click(t)

            row.bind("<Button-1>", on_click)
            time_label.bind("<Button-1>", on_click)

        # Timeline dot
        dot = ctk.CTkLabel(
            row,
            text="○",
            font=FONT_SMALL,
            text_color=WARNING,
            width=15,
        )
        dot.pack(side="left")

        text_label = ctk.CTkLabel(
            row,
            text=text,
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=300,
        )
        text_label.pack(side="left", fill="x", expand=True)

        if timestamp is not None:
            dot.bind("<Button-1>", on_click)
            text_label.bind("<Button-1>", on_click)

    def _add_clickable_timestamp(self, parent, timestamp: float):
        """Add a small clickable timestamp label to a row."""
        time_str = self._format_time(timestamp)

        ts_label = ctk.CTkLabel(
            parent,
            text=time_str,
            font=FONT_TIMESTAMP,
            text_color=PRIMARY,
            cursor="hand2",
        )
        ts_label.pack(side="right", padx=(SPACING_SM, 0))

        def on_click(event, t=timestamp):
            self._handle_timestamp_click(t)

        ts_label.bind("<Button-1>", on_click)

    def _handle_timestamp_click(self, timestamp: float):
        """Fire callback to seek audio to this timestamp."""
        if self.on_timestamp_click:
            self.on_timestamp_click(timestamp)
            logger.info(f"Summary timestamp click: {timestamp:.1f}s")

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
