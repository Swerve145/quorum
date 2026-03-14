# task list display panel
import customtkinter as ctk

from ui.styles import (
    BG_PANEL,
    BG_INPUT,
    SURFACE,
    SURFACE_HOVER,
    PRIMARY,
    PRIMARY_LIGHT,
    PRIMARY_DARK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    SUCCESS,
    WARNING,
    ERROR,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_TIMESTAMP,
    PANEL_PADDING,
    PANEL_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
    get_speaker_colour,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Priority display config
PRIORITY_COLOURS = {
    "high": ERROR,
    "medium": WARNING,
    "low": SUCCESS,
}

PRIORITY_LABELS = {
    "high": "HIGH",
    "medium": "MED",
    "low": "LOW",
}


class TaskPanel(ctk.CTkFrame):
    """Displays extracted tasks with assignee, priority,"""

    def __init__(
        self,
        master,
        tasks: list,
        speaker_map: dict,
        on_task_click: callable = None,
    ):
        super().__init__(
            master,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
        )

        self.tasks = tasks
        self.speaker_map = speaker_map
        self.on_task_click = on_task_click

        # Speaker colour mapping
        self.speaker_colours = {}
        for i, speaker in enumerate(sorted(speaker_map.keys())):
            self.speaker_colours[speaker] = i

        self.task_rows = []

        self._build_ui()

    def _build_ui(self):
        """Construct header with count and scrollable task list."""

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(PANEL_PADDING, SPACING_SM),
        )

        title = ctk.CTkLabel(
            header_frame,
            text="Tasks",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        title.pack(side="left")

        self.count_label = ctk.CTkLabel(
            header_frame,
            text=f"{len(self.tasks)} found",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            anchor="e",
        )
        self.count_label.pack(side="right")

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

        if len(self.tasks) == 0:
            empty = ctk.CTkLabel(
                self.scroll_frame,
                text="No tasks extracted from this meeting.",
                font=FONT_BODY,
                text_color=TEXT_MUTED,
            )
            empty.pack(pady=SPACING_MD)
        else:
            for i, task in enumerate(self.tasks):
                row = self._create_task_row(task, i)
                self.task_rows.append(row)

    def _create_task_row(self, task: dict, index: int) -> dict:
        """Create a single task card with priority badge, text,"""
        # Extract task fields
        source = task.get("source_segment", {})
        task_text = (
            task.get("task_text", "")
            or task.get("text", "")
            or source.get("text", "")
            or "No task text available"
        )
        speaker = source.get("speaker", "Unknown")
        confidence = task.get("confidence", 0.0)
        priority = task.get("priority", "medium")
        start_time = source.get("start", 0.0)

        display_name = self.speaker_map.get(speaker, speaker)
        priority_colour = PRIORITY_COLOURS.get(priority, WARNING)
        priority_label = PRIORITY_LABELS.get(priority, "MED")

        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=SURFACE,
            corner_radius=8,
            cursor="hand2",
        )
        card.pack(fill="x", pady=(0, SPACING_SM))

        # Click to seek audio
        def on_click(event, t=task):
            self._handle_click(t)

        card.bind("<Button-1>", on_click)

        # Hover
        def on_enter(event, c=card):
            c.configure(fg_color=SURFACE_HOVER)

        def on_leave(event, c=card):
            c.configure(fg_color=SURFACE)

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(
            fill="x",
            padx=SPACING_SM,
            pady=(SPACING_SM, 0),
        )
        top_row.bind("<Button-1>", on_click)

        # Priority badge
        priority_badge = ctk.CTkLabel(
            top_row,
            text=f" {priority_label} ",
            font=FONT_SMALL,
            text_color=TEXT_PRIMARY,
            fg_color=priority_colour,
            corner_radius=4,
        )
        priority_badge.pack(side="left")
        priority_badge.bind("<Button-1>", on_click)

        # Confidence
        conf_label = ctk.CTkLabel(
            top_row,
            text=f"{confidence:.0%} conf",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        conf_label.pack(side="right")
        conf_label.bind("<Button-1>", on_click)

        # Boosted/rescued indicators from context bridge
        if task.get("context_boosted"):
            boost_label = ctk.CTkLabel(
                top_row,
                text="⬆ boosted",
                font=FONT_SMALL,
                text_color=SUCCESS,
            )
            boost_label.pack(side="right", padx=(0, SPACING_SM))
            boost_label.bind("<Button-1>", on_click)

        if task.get("context_rescued"):
            rescue_label = ctk.CTkLabel(
                top_row,
                text="★ rescued",
                font=FONT_SMALL,
                text_color=WARNING,
            )
            rescue_label.pack(side="right", padx=(0, SPACING_SM))
            rescue_label.bind("<Button-1>", on_click)

        text_label = ctk.CTkLabel(
            card,
            text=task_text,
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=350,
        )
        text_label.pack(
            fill="x",
            padx=SPACING_SM,
            pady=(SPACING_SM, 0),
        )
        text_label.bind("<Button-1>", on_click)

        bottom_row = ctk.CTkFrame(card, fg_color="transparent")
        bottom_row.pack(
            fill="x",
            padx=SPACING_SM,
            pady=(2, SPACING_SM),
        )
        bottom_row.bind("<Button-1>", on_click)

        # Speaker/assignee
        speaker_idx = self.speaker_colours.get(speaker, 0)
        speaker_colour = get_speaker_colour(speaker_idx)

        assignee_label = ctk.CTkLabel(
            bottom_row,
            text=f"⤷ {display_name}",
            font=FONT_SMALL,
            text_color=speaker_colour,
        )
        assignee_label.pack(side="left")
        assignee_label.bind("<Button-1>", on_click)

        # Source timestamp
        time_str = self._format_time(start_time)
        time_label = ctk.CTkLabel(
            bottom_row,
            text=f"at {time_str}",
            font=FONT_TIMESTAMP,
            text_color=TEXT_MUTED,
        )
        time_label.pack(side="right")
        time_label.bind("<Button-1>", on_click)

        return {
            "frame": card,
            "task": task,
            "speaker": speaker,
            "text": task_text.lower(),
            "priority": priority,
            "visible": True,
        }

    def _handle_click(self, task: dict):
        """Fire callback with the task's source timestamp."""
        if self.on_task_click:
            source = task.get("source_segment", {})
            start = source.get("start", 0.0)
            self.on_task_click(start)
            logger.info(
                f"Task click: {start:.1f}s — "
                f"{source.get('text', '')[:40]}"
            )

    def filter_by_speaker(self, speaker: str = None):
        """Show only tasks from a specific speaker. None shows all."""
        visible_count = 0
        for row in self.task_rows:
            if speaker is None or row["speaker"] == speaker:
                row["frame"].pack(fill="x", pady=(0, SPACING_SM))
                row["visible"] = True
                visible_count += 1
            else:
                row["frame"].pack_forget()
                row["visible"] = False

        self.count_label.configure(text=f"{visible_count} shown")

    def filter_by_priority(self, priority: str = None):
        """Show only tasks of a specific priority. None shows all."""
        visible_count = 0
        for row in self.task_rows:
            if priority is None or row["priority"] == priority:
                row["frame"].pack(fill="x", pady=(0, SPACING_SM))
                row["visible"] = True
                visible_count += 1
            else:
                row["frame"].pack_forget()
                row["visible"] = False

        self.count_label.configure(text=f"{visible_count} shown")

    def filter_by_keyword(self, keyword: str = ""):
        """Show only tasks containing the keyword."""
        keyword = keyword.lower().strip()
        visible_count = 0

        for row in self.task_rows:
            if keyword == "" or keyword in row["text"]:
                row["frame"].pack(fill="x", pady=(0, SPACING_SM))
                row["visible"] = True
                visible_count += 1
            else:
                row["frame"].pack_forget()
                row["visible"] = False

        self.count_label.configure(text=f"{visible_count} shown")

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
