# input screen — file selection and pipeline config
import os
import threading
from tkinter import filedialog

import customtkinter as ctk

from ui.styles import (
    BG_DARK,
    BG_PANEL,
    BG_INPUT,
    SURFACE,
    SURFACE_HOVER,
    PRIMARY,
    PRIMARY_HOVER,
    PRIMARY_LIGHT,
    PRIMARY_DARK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    SUCCESS,
    ERROR,
    FONT_HEADING,
    FONT_SUBHEADING,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    PANEL_PADDING,
    PANEL_CORNER_RADIUS,
    INPUT_DRAG_AREA_HEIGHT,
    BTN_HEIGHT,
    BTN_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Supported audio formats
AUDIO_EXTENSIONS = [
    ("Audio Files", "*.wav *.mp3 *.m4a *.flac *.ogg *.wma *.aac *.webm"),
    ("All Files", "*.*"),
]

# Pipeline stage labels for progress display
STAGE_LABELS = [
    "Pre-processing audio...",
    "Transcribing with Whisper...",
    "Running speaker diarisation...",
    "Aligning transcript with speakers...",
    "Analysing — summarising and extracting tasks...",
    "Complete.",
]


class InputScreen(ctk.CTkFrame):
    """Input screen with file selection, configuration options,"""

    def __init__(self, master, on_processing_complete: callable):
        super().__init__(master, fg_color=BG_DARK)

        self.on_processing_complete = on_processing_complete
        self.selected_file = None
        self.processing = False

        self._build_ui()

    def _build_ui(self):
        """Construct all input screen widgets."""

        header = ctk.CTkLabel(
            self,
            text="Quorum",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        )
        header.pack(pady=(SPACING_LG * 2, SPACING_SM))

        subtitle = ctk.CTkLabel(
            self,
            text="Intelligent Meeting Intelligence",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        )
        subtitle.pack(pady=(0, SPACING_LG * 2))

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=80)

        self.file_frame = ctk.CTkFrame(
            container,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
            height=INPUT_DRAG_AREA_HEIGHT,
        )
        self.file_frame.pack(fill="x", pady=(0, SPACING_LG))
        self.file_frame.pack_propagate(False)

        self.file_label = ctk.CTkLabel(
            self.file_frame,
            text="No file selected",
            font=FONT_BODY,
            text_color=TEXT_MUTED,
        )
        self.file_label.pack(expand=True)

        self.browse_btn = ctk.CTkButton(
            self.file_frame,
            text="Browse Audio File",
            font=FONT_BODY_BOLD,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            height=BTN_HEIGHT,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._browse_file,
        )
        self.browse_btn.pack(pady=(0, SPACING_LG))

        settings_frame = ctk.CTkFrame(
            container,
            fg_color="transparent",
        )
        settings_frame.pack(fill="x", pady=(0, SPACING_LG))

        # Whisper model size
        model_label = ctk.CTkLabel(
            settings_frame,
            text="Whisper Model:",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        )
        model_label.pack(side="left", padx=(0, SPACING_SM))

        self.model_var = ctk.StringVar(value="base")
        self.model_dropdown = ctk.CTkComboBox(
            settings_frame,
            values=["tiny", "base", "small", "medium"],
            variable=self.model_var,
            width=140,
            fg_color=BG_INPUT,
            border_color=SURFACE,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=BG_PANEL,
            font=FONT_BODY,
            state="readonly",
        )
        self.model_dropdown.pack(side="left", padx=(0, SPACING_LG))

        # Expected speaker count
        speaker_label = ctk.CTkLabel(
            settings_frame,
            text="Expected Speakers:",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        )
        speaker_label.pack(side="left", padx=(0, SPACING_SM))

        self.speaker_var = ctk.StringVar(value="Auto")
        self.speaker_dropdown = ctk.CTkComboBox(
            settings_frame,
            values=["Auto", "2", "3", "4", "5", "6"],
            variable=self.speaker_var,
            width=100,
            fg_color=BG_INPUT,
            border_color=SURFACE,
            button_color=PRIMARY,
            button_hover_color=PRIMARY_HOVER,
            dropdown_fg_color=BG_PANEL,
            font=FONT_BODY,
            state="readonly",
        )
        self.speaker_dropdown.pack(side="left")

        self.start_btn = ctk.CTkButton(
            container,
            text="Start Processing",
            font=FONT_BODY_BOLD,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            height=BTN_HEIGHT + 8,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._start_processing,
            state="disabled",
        )
        self.start_btn.pack(fill="x", pady=(0, SPACING_LG))

        self.progress_frame = ctk.CTkFrame(
            container,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
        )

        self.stage_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=FONT_BODY,
            text_color=TEXT_SECONDARY,
        )
        self.stage_label.pack(pady=(SPACING_MD, SPACING_SM))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            fg_color=SURFACE,
            progress_color=PRIMARY,
            height=20,
        )
        self.progress_bar.pack(
            fill="x",
            padx=SPACING_LG,
            pady=(0, SPACING_MD),
        )
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        self.status_label.pack(pady=(0, SPACING_MD))

    def _browse_file(self):
        """Open file dialog and store selected audio file path."""
        path = filedialog.askopenfilename(
            title="Select Meeting Audio",
            filetypes=AUDIO_EXTENSIONS,
        )

        if not path:
            return

        self.selected_file = path
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        self.file_label.configure(
            text=f"{filename}  ({size_mb:.1f} MB)",
            text_color=TEXT_PRIMARY,
        )
        self.start_btn.configure(state="normal")

        logger.info(f"Selected file: {path} ({size_mb:.1f} MB)")

    def _start_processing(self):
        """Launch the pipeline in a background thread."""
        if self.processing or self.selected_file is None:
            return

        self.processing = True
        self.start_btn.configure(state="disabled", text="Processing...")
        self.browse_btn.configure(state="disabled")
        self.model_dropdown.configure(state="disabled")
        self.speaker_dropdown.configure(state="disabled")

        # Show progress section
        self.progress_frame.pack(fill="x", pady=(0, SPACING_LG))

        # Run pipeline in background thread
        thread = threading.Thread(
            target=self._run_pipeline,
            daemon=True,
        )
        thread.start()

    def _run_pipeline(self):
        """Execute the full pipeline. Runs in a background thread."""
        try:
            self._update_progress(0, "Initialising pipeline...")

            from audio.preprocessor import preprocess_audio
            from transcription.transcriber import Transcriber
            from diarisation.diariser import Diariser
            from alignment.aligner import Aligner
            from analysis.analyser import Analyser

            self._update_progress(0, STAGE_LABELS[0])
            preprocess_result = preprocess_audio(self.selected_file)
            chunks = preprocess_result["chunks"]
            self._update_progress(1, STAGE_LABELS[1])
            transcriber = Transcriber()
            transcript = transcriber.transcribe(chunks)

            self._update_progress(2, STAGE_LABELS[2])
            diariser = Diariser()
            diarisation = diariser.diarise(self.selected_file)

            self._update_progress(3, STAGE_LABELS[3])
            aligner = Aligner()
            aligned_segments = aligner.align(
                transcript["segments"],
                diarisation["segments"],
            )

            self._update_progress(4, STAGE_LABELS[4])
            analyser = Analyser()
            analysis = analyser.analyse(aligned_segments)

            results = {
                "segments": aligned_segments,
                "speaker_map": diarisation.get("speaker_map", {}),
                "tasks": analysis.get("tasks", []),
                "summary": analysis.get("summary", {}),
                "metadata": {
                    "whisper_model": self.model_var.get(),
                    "audio_file": self.selected_file,
                },
            }

            self._update_progress(5, STAGE_LABELS[5])

            # Switch to output screen on the main thread
            self.after(
                500,
                lambda: self.on_processing_complete(
                    results, self.selected_file
                ),
            )

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.after(0, lambda: self._show_error(str(e)))

    def _update_progress(self, stage_index: int, message: str):
        """Thread-safe progress update via after()."""
        progress = stage_index / (len(STAGE_LABELS) - 1)

        def _update():
            self.stage_label.configure(text=message)
            self.progress_bar.set(progress)
            self.status_label.configure(
                text=f"Stage {stage_index + 1} of {len(STAGE_LABELS)}"
            )

        self.after(0, _update)

    def _show_error(self, message: str):
        """Display error state in the progress section."""
        self.stage_label.configure(
            text="Processing failed",
            text_color=ERROR,
        )
        self.status_label.configure(
            text=message[:120],
            text_color=ERROR,
        )
        self.start_btn.configure(
            state="normal",
            text="Retry",
        )
        self.browse_btn.configure(state="normal")
        self.processing = False
