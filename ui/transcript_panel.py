# scrollable transcript display with confidence colouring
import customtkinter as ctk

from ui.styles import (
    BG_PANEL,
    BG_INPUT,
    SURFACE,
    SURFACE_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_TIMESTAMP,
    PANEL_PADDING,
    PANEL_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
    get_speaker_colour,
    get_confidence_colour,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TranscriptPanel(ctk.CTkFrame):
    """Scrollable transcript with speaker badges, confidence"""

    def __init__(
        self,
        master,
        segments: list,
        speaker_map: dict,
        on_segment_click: callable = None,
    ):
        super().__init__(
            master,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
        )

        self.segments = segments
        self.speaker_map = speaker_map
        self.on_segment_click = on_segment_click

        # Speaker label → colour index
        self.speaker_colours = {}
        for i, speaker in enumerate(sorted(speaker_map.keys())):
            self.speaker_colours[speaker] = i

        # Store segment row widgets for filtering
        self.segment_rows = []

        self._build_ui()

    def _build_ui(self):
        """Construct the panel header and scrollable transcript."""

        header = ctk.CTkLabel(
            self,
            text="Transcript",
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

        self._render_segments(self.segments)

    def _render_segments(self, segments: list):
        """Build a row for each transcript segment."""
        # Clear existing rows
        for row in self.segment_rows:
            row["frame"].destroy()
        self.segment_rows.clear()

        for i, seg in enumerate(segments):
            row = self._create_segment_row(seg, i)
            self.segment_rows.append(row)

    def _create_segment_row(self, segment: dict, index: int) -> dict:
        """Create a single transcript row with speaker badge,"""
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "")
        start = segment.get("start", 0.0)
        confidence = segment.get("confidence", 1.0)

        # Confidence colour
        conf_colours = get_confidence_colour(confidence)
        text_colour = conf_colours["fg"]

        # Speaker colour
        speaker_idx = self.speaker_colours.get(speaker, 0)
        speaker_colour = get_speaker_colour(speaker_idx)

        # Display name (aliased or raw label)
        display_name = self.speaker_map.get(speaker, speaker)

        row_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="transparent",
            cursor="hand2",
        )
        row_frame.pack(fill="x", pady=1)

        # Click binding on the whole row
        def on_click(event, s=segment):
            self._handle_click(s)

        row_frame.bind("<Button-1>", on_click)

        # Hover effect
        def on_enter(event, f=row_frame):
            f.configure(fg_color=SURFACE_HOVER)

        def on_leave(event, f=row_frame):
            f.configure(fg_color="transparent")

        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)

        left = ctk.CTkFrame(row_frame, fg_color="transparent", width=110)
        left.pack(side="left", anchor="n", padx=(SPACING_SM, 0))
        left.pack_propagate(False)

        # Timestamp
        time_str = self._format_time(start)
        time_label = ctk.CTkLabel(
            left,
            text=time_str,
            font=FONT_TIMESTAMP,
            text_color=TEXT_MUTED,
            anchor="w",
        )
        time_label.pack(anchor="w")
        time_label.bind("<Button-1>", on_click)

        # Speaker badge
        badge = ctk.CTkLabel(
            left,
            text=f" {display_name} ",
            font=FONT_SMALL,
            text_color=TEXT_PRIMARY,
            fg_color=speaker_colour,
            corner_radius=4,
        )
        badge.pack(anchor="w", pady=(2, 0))
        badge.bind("<Button-1>", on_click)

        text_label = ctk.CTkLabel(
            row_frame,
            text=text,
            font=FONT_BODY,
            text_color=text_colour,
            anchor="w",
            justify="left",
            wraplength=500,
        )
        text_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(SPACING_MD, SPACING_SM),
            pady=SPACING_SM,
        )
        text_label.bind("<Button-1>", on_click)

        conf_text = f"{abs(confidence):.0%}" if confidence < 0 else f"{confidence:.0%}"
        conf_label = ctk.CTkLabel(
            row_frame,
            text=conf_text,
            font=FONT_SMALL,
            text_color=text_colour,
            width=45,
        )
        conf_label.pack(side="right", padx=(0, SPACING_SM))
        conf_label.bind("<Button-1>", on_click)

        return {
            "frame": row_frame,
            "segment": segment,
            "speaker": speaker,
            "text": text.lower(),
            "text_label": text_label,
            "visible": True,
        }

    def _handle_click(self, segment: dict):
        """Fire the click callback with the segment's start time."""
        if self.on_segment_click:
            start = segment.get("start", 0.0)
            self.on_segment_click(start)
            logger.info(
                f"Transcript click: {start:.1f}s — "
                f"{segment.get('text', '')[:40]}"
            )

    def filter_by_speaker(self, speaker: str = None):
        """Show only segments from a specific speaker."""
        for row in self.segment_rows:
            if speaker is None or row["speaker"] == speaker:
                row["frame"].pack(fill="x", pady=1)
                row["visible"] = True
            else:
                row["frame"].pack_forget()
                row["visible"] = False

    def filter_by_keyword(self, keyword: str = ""):
        """Show only segments containing the keyword."""
        keyword = keyword.lower().strip()

        for row in self.segment_rows:
            if keyword == "" or keyword in row["text"]:
                row["frame"].pack(fill="x", pady=1)
                row["visible"] = True
            else:
                row["frame"].pack_forget()
                row["visible"] = False

    def highlight_segment(self, segment_index: int):
        """Briefly highlight a specific segment row."""
        if 0 <= segment_index < len(self.segment_rows):
            row = self.segment_rows[segment_index]
            row["frame"].configure(fg_color=SURFACE)

            # Scroll to the segment
            # CTkScrollableFrame doesn't have a direct scroll-to,
            # so we use the frame's position
            self.after(
                2000,
                lambda f=row["frame"]: f.configure(fg_color="transparent"),
            )

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
