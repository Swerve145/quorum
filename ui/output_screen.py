# output screen — assembles all panels
import customtkinter as ctk

from ui.styles import (
    BG_DARK,
    BG_PANEL,
    SURFACE,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    PANEL_PADDING,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
    BTN_HEIGHT,
    BTN_CORNER_RADIUS,
    TRANSCRIPT_WEIGHT,
    SIDEBAR_WEIGHT,
    AUDIO_PLAYER_HEIGHT,
)
from ui.transcript_panel import TranscriptPanel
from ui.task_panel import TaskPanel
from ui.summary_panel import SummaryPanel
from ui.audio_player import AudioPlayer
from ui.search_filter import SearchFilter
from ui.speaker_aliaser import SpeakerAliaser
from utils.logger import setup_logger

logger = setup_logger(__name__)

class OutputScreen(ctk.CTkFrame):
    """Main output view — assembles transcript, tasks, summary,"""

    def __init__(
        self,
        master,
        results: dict,
        audio_path: str,
        on_back: callable = None,
    ):
        super().__init__(master, fg_color=BG_DARK)

        self.results = results
        self.audio_path = audio_path
        self.on_back = on_back

        # Extract data from results
        self.segments = results.get("segments", [])
        self.tasks = results.get("tasks", [])
        self.summary = results.get("summary", {})
        self.speaker_map = results.get("speaker_map", {})

        # Build speaker map from segments if not provided
        if not self.speaker_map:
            self.speaker_map = self._build_speaker_map()

        # Panel references (set during build)
        self.audio_player = None
        self.transcript_panel = None
        self.task_panel = None
        self.summary_panel = None
        self.search_filter = None

        self._build_ui()

        logger.info(
            f"Output screen loaded — {len(self.segments)} segments, "
            f"{len(self.tasks)} tasks, "
            f"{len(self.speaker_map)} speakers"
        )

    def _build_speaker_map(self) -> dict:
        """Extract unique speakers from segments if no map provided."""
        speakers = set()
        for seg in self.segments:
            speaker = seg.get("speaker", "")
            if speaker:
                speakers.add(speaker)

        # Default: label maps to itself
        return {s: s for s in sorted(speakers)}

    def _build_ui(self):
        """Construct the full output layout."""

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(PANEL_PADDING, SPACING_SM),
        )

        back_btn = ctk.CTkButton(
            top_bar,
            text="← New Meeting",
            font=FONT_BODY,
            fg_color=SURFACE,
            hover_color=PRIMARY_HOVER,
            width=130,
            height=32,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._go_back,
        )
        back_btn.pack(side="left")

        title = ctk.CTkLabel(
            top_bar,
            text="Meeting Results",
            font=FONT_BODY_BOLD,
            text_color=TEXT_PRIMARY,
        )
        title.pack(side="left", padx=SPACING_LG)

        # Metadata
        meta = self.results.get("metadata", {})
        model_name = meta.get("whisper_model", "unknown")
        meta_text = (
            f"{len(self.segments)} segments  •  "
            f"{len(self.tasks)} tasks  •  "
            f"{len(self.speaker_map)} speakers  •  "
            f"Whisper {model_name}"
        )
        meta_label = ctk.CTkLabel(
            top_bar,
            text=meta_text,
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
        )
        meta_label.pack(side="left", padx=SPACING_MD)

        # Alias speakers button
        alias_btn = ctk.CTkButton(
            top_bar,
            text="Rename Speakers",
            font=FONT_BODY,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            width=140,
            height=32,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._open_aliaser,
        )
        alias_btn.pack(side="right")

        self.search_filter = SearchFilter(
            self,
            speaker_map=self.speaker_map,
            on_search=self._on_search,
            on_speaker_filter=self._on_speaker_filter,
            on_priority_filter=self._on_priority_filter,
        )
        self.search_filter.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(0, SPACING_SM),
        )

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(
            fill="both",
            expand=True,
            padx=PANEL_PADDING,
            pady=(0, SPACING_SM),
        )

        content.columnconfigure(0, weight=TRANSCRIPT_WEIGHT)
        content.columnconfigure(1, weight=SIDEBAR_WEIGHT)
        content.rowconfigure(0, weight=1)

        self.transcript_panel = TranscriptPanel(
            content,
            segments=self.segments,
            speaker_map=self.speaker_map,
            on_segment_click=self._on_seek,
        )
        self.transcript_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, SPACING_SM),
        )

        right_col = ctk.CTkFrame(content, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.rowconfigure(0, weight=1)
        right_col.rowconfigure(1, weight=1)
        right_col.columnconfigure(0, weight=1)

        self.task_panel = TaskPanel(
            right_col,
            tasks=self.tasks,
            speaker_map=self.speaker_map,
            on_task_click=self._on_seek,
        )
        self.task_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            pady=(0, SPACING_SM),
        )

        self.summary_panel = SummaryPanel(
            right_col,
            summary=self.summary,
            on_timestamp_click=self._on_seek,
        )
        self.summary_panel.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        self.audio_player = AudioPlayer(
            self,
            audio_path=self.audio_path,
            segments=self.segments,
            speaker_map=self.speaker_map,
        )
        self.audio_player.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(0, PANEL_PADDING),
        )

    def _on_seek(self, timestamp: float):
        if self.audio_player:
            self.audio_player.seek_to(timestamp)

    def _on_search(self, keyword: str):
        """Search callback — filters both transcript and tasks."""
        if self.transcript_panel:
            self.transcript_panel.filter_by_keyword(keyword)
        if self.task_panel:
            self.task_panel.filter_by_keyword(keyword)

    def _on_speaker_filter(self, speaker: str):
        """Speaker filter — filters both transcript and tasks."""
        if self.transcript_panel:
            self.transcript_panel.filter_by_speaker(speaker)
        if self.task_panel:
            self.task_panel.filter_by_speaker(speaker)

    def _on_priority_filter(self, priority: str):
        """Priority filter — filters task panel only."""
        if self.task_panel:
            self.task_panel.filter_by_priority(priority)

    def _open_aliaser(self):
        """Open the speaker aliasing dialog."""
        SpeakerAliaser(
            self,
            speaker_map=self.speaker_map,
            on_apply=self._apply_aliases,
        )

    def _apply_aliases(self, updated_map: dict):
        """Refresh all panels with new speaker names."""
        self.speaker_map = updated_map

        # Update the results dict so it stays consistent
        self.results["speaker_map"] = updated_map

        logger.info(f"Applying aliases: {updated_map}")

        # Rebuild panels that display speaker names
        # This is the simplest reliable approach — destroy and
        # recreate with the new map rather than trying to
        # update labels in place across hundreds of widgets

        # Store current search/filter state
        current_search = self.search_filter.search_entry.get()
        current_speaker = self.search_filter.speaker_var.get()
        current_priority = self.search_filter.priority_var.get()

        # Update search filter dropdown
        self.search_filter.update_speaker_options(updated_map)

        # Rebuild transcript panel
        parent = self.transcript_panel.master
        grid_info = self.transcript_panel.grid_info()
        self.transcript_panel.destroy()

        self.transcript_panel = TranscriptPanel(
            parent,
            segments=self.segments,
            speaker_map=self.speaker_map,
            on_segment_click=self._on_seek,
        )
        self.transcript_panel.grid(**grid_info)

        # Rebuild task panel
        parent = self.task_panel.master
        grid_info = self.task_panel.grid_info()
        self.task_panel.destroy()

        self.task_panel = TaskPanel(
            parent,
            tasks=self.tasks,
            speaker_map=self.speaker_map,
            on_task_click=self._on_seek,
        )
        self.task_panel.grid(**grid_info)

        # Rebuild summary panel
        parent = self.summary_panel.master
        grid_info = self.summary_panel.grid_info()
        self.summary_panel.destroy()

        self.summary_panel = SummaryPanel(
            parent,
            summary=self.summary,
            on_timestamp_click=self._on_seek,
        )
        self.summary_panel.grid(**grid_info)

        # Restore search/filter state
        if current_search:
            self.search_filter.search_entry.insert(0, current_search)
            self._on_search(current_search)

        logger.info("All panels refreshed with new speaker names")

    def _go_back(self):
        """Return to the input screen."""
        if self.audio_player:
            self.audio_player._stop_playback()

        if self.on_back:
            self.on_back()
