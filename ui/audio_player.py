# audio waveform and playback controls
import os
import threading
import numpy as np

import customtkinter as ctk

from ui.styles import (
    BG_PANEL,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    PRIMARY,
    PRIMARY_HOVER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_TIMESTAMP,
    PANEL_PADDING,
    PANEL_CORNER_RADIUS,
    BTN_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
    get_speaker_colour,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AudioPlayer(ctk.CTkFrame):
    """Audio waveform display with playback controls."""

    def __init__(
        self,
        master,
        audio_path: str,
        segments: list,
        speaker_map: dict,
    ):
        super().__init__(
            master,
            fg_color=BG_PANEL,
            corner_radius=PANEL_CORNER_RADIUS,
        )

        self.audio_path = audio_path
        self.segments = segments
        self.speaker_map = speaker_map

        # Playback state
        self.playing = False
        self.current_time = 0.0
        self.duration = 0.0
        self.waveform_data = None
        self.playhead_line = None
        self.update_job = None

        # Speaker label → colour index mapping
        self.speaker_colours = {}
        for i, speaker in enumerate(sorted(speaker_map.keys())):
            self.speaker_colours[speaker] = i

        self._init_audio()
        self._build_ui()
        self._draw_waveform()

    def _init_audio(self):
        """Load audio file and extract waveform data for display."""
        try:
            import pygame
            pygame.mixer.init(frequency=44100)
            pygame.mixer.music.load(self.audio_path)

            # Get duration using pydub (more reliable than pygame)
            from pydub import AudioSegment

            audio = AudioSegment.from_file(self.audio_path)
            self.duration = len(audio) / 1000.0  # ms to seconds

            # Downsample to displayable waveform
            samples = np.array(audio.get_array_of_samples())
            if audio.channels == 2:
                samples = samples[::2]  # Take left channel

            # Downsample to ~800 points for canvas width
            chunk_size = max(1, len(samples) // 800)
            chunks = [
                samples[i : i + chunk_size]
                for i in range(0, len(samples), chunk_size)
            ]
            self.waveform_data = np.array(
                [np.max(np.abs(c)) for c in chunks if len(c) > 0]
            )

            # Normalise to 0-1
            peak = np.max(self.waveform_data)
            if peak > 0:
                self.waveform_data = self.waveform_data / peak

            logger.info(
                f"Audio loaded: {self.duration:.1f}s, "
                f"{len(self.waveform_data)} waveform points"
            )

        except Exception as e:
            logger.error(f"Audio init failed: {e}")
            self.duration = 0.0
            self.waveform_data = np.zeros(800)

    def _build_ui(self):
        """Construct player controls and waveform canvas."""

        self.canvas = ctk.CTkCanvas(
            self,
            bg=SURFACE,
            highlightthickness=0,
            height=70,
        )
        self.canvas.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(PANEL_PADDING, SPACING_SM),
        )
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", lambda e: self._draw_waveform())

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(
            fill="x",
            padx=PANEL_PADDING,
            pady=(0, PANEL_PADDING),
        )

        # Play/Pause button
        self.play_btn = ctk.CTkButton(
            controls,
            text="▶  Play",
            font=FONT_BODY_BOLD,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            width=100,
            height=32,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._toggle_playback,
        )
        self.play_btn.pack(side="left", padx=(0, SPACING_MD))

        # Stop button
        self.stop_btn = ctk.CTkButton(
            controls,
            text="■  Stop",
            font=FONT_BODY,
            fg_color=SURFACE,
            hover_color=PRIMARY_HOVER,
            width=80,
            height=32,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._stop_playback,
        )
        self.stop_btn.pack(side="left", padx=(0, SPACING_MD))

        # Current time label
        self.time_label = ctk.CTkLabel(
            controls,
            text="0:00 / 0:00",
            font=FONT_TIMESTAMP,
            text_color=TEXT_MUTED,
        )
        self.time_label.pack(side="left")

        # Speaker legend (right side)
        legend_frame = ctk.CTkFrame(controls, fg_color="transparent")
        legend_frame.pack(side="right")

        for speaker, idx in self.speaker_colours.items():
            colour = get_speaker_colour(idx)
            display_name = self.speaker_map.get(speaker, speaker)

            dot = ctk.CTkLabel(
                legend_frame,
                text="●",
                font=FONT_SMALL,
                text_color=colour,
            )
            dot.pack(side="left", padx=(SPACING_SM, 2))

            name = ctk.CTkLabel(
                legend_frame,
                text=display_name,
                font=FONT_SMALL,
                text_color=TEXT_SECONDARY,
            )
            name.pack(side="left")

    def _draw_waveform(self):
        """Draw speaker-coloured waveform bars on the canvas."""
        self.canvas.delete("all")

        if self.waveform_data is None or len(self.waveform_data) == 0:
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1:
            return

        num_bars = min(len(self.waveform_data), width // 2)
        bar_width = max(1, width / num_bars)
        mid_y = height / 2

        for i in range(num_bars):
            data_idx = int(i * len(self.waveform_data) / num_bars)
            amplitude = self.waveform_data[data_idx]

            # Find which speaker owns this time position
            time_pos = (i / num_bars) * self.duration
            colour = self._get_colour_at_time(time_pos)

            bar_height = max(2, amplitude * (height * 0.8))
            x = i * bar_width

            self.canvas.create_rectangle(
                x,
                mid_y - bar_height / 2,
                x + bar_width - 1,
                mid_y + bar_height / 2,
                fill=colour,
                outline="",
            )

    def _get_colour_at_time(self, time_seconds: float) -> str:
        """Return the speaker colour for a given timestamp."""
        for seg in self.segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            if start <= time_seconds <= end:
                speaker = seg.get("speaker", "")
                idx = self.speaker_colours.get(speaker, 0)
                return get_speaker_colour(idx)

        return SURFACE  # No speaker — silence/gap

    def _on_canvas_click(self, event):
        """Seek to the clicked position on the waveform."""
        width = self.canvas.winfo_width()
        if width <= 0 or self.duration <= 0:
            return

        ratio = event.x / width
        target_time = ratio * self.duration
        self.seek_to(target_time)

    def seek_to(self, seconds: float):
        """Jump playback to a specific timestamp."""
        seconds = max(0, min(seconds, self.duration))
        self.current_time = seconds

        try:
            import pygame

            was_playing = self.playing
            pygame.mixer.music.play(start=seconds)

            if not was_playing:
                pygame.mixer.music.pause()
            else:
                self._start_update_loop()

        except Exception as e:
            logger.error(f"Seek failed: {e}")

        self._update_playhead()
        self._update_time_display()

        logger.info(f"Seeked to {seconds:.1f}s")

    def _toggle_playback(self):
        """Play or pause audio."""
        try:
            import pygame

            if self.playing:
                pygame.mixer.music.pause()
                self.playing = False
                self.play_btn.configure(text="▶  Play")
                self._stop_update_loop()
            else:
                if self.current_time == 0.0:
                    pygame.mixer.music.play()
                else:
                    pygame.mixer.music.unpause()
                self.playing = True
                self.play_btn.configure(text="⏸  Pause")
                self._start_update_loop()

        except Exception as e:
            logger.error(f"Playback toggle failed: {e}")

    def _stop_playback(self):
        """Stop playback and reset to beginning."""
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass

        self.playing = False
        self.current_time = 0.0
        self.play_btn.configure(text="▶  Play")
        self._stop_update_loop()
        self._update_playhead()
        self._update_time_display()

    def _start_update_loop(self):
        self._stop_update_loop()
        self._tick()

    def _stop_update_loop(self):
        if self.update_job is not None:
            self.after_cancel(self.update_job)
            self.update_job = None

    def _tick(self):
        """Update playhead position every 100ms during playback."""
        if not self.playing:
            return

        try:
            import pygame

            if pygame.mixer.music.get_busy():
                # pygame doesn't expose position well,
                # so we track it manually
                self.current_time += 0.1
                if self.current_time >= self.duration:
                    self._stop_playback()
                    return

                self._update_playhead()
                self._update_time_display()
            else:
                self._stop_playback()
                return

        except Exception:
            pass

        self.update_job = self.after(100, self._tick)

    def _update_playhead(self):
        self.canvas.delete("playhead")

        if self.duration <= 0:
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        x = (self.current_time / self.duration) * width

        self.canvas.create_line(
            x, 0, x, height,
            fill=TEXT_PRIMARY,
            width=2,
            tags="playhead",
        )

    def _update_time_display(self):
        """Update the time label with current / total."""
        current = self._format_time(self.current_time)
        total = self._format_time(self.duration)
        self.time_label.configure(text=f"{current} / {total}")

    @staticmethod
    def _format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
