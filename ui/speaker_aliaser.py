# dialog for renaming speaker labels
import customtkinter as ctk

from ui.styles import (
    BG_DARK,
    BG_PANEL,
    BG_INPUT,
    SURFACE,
    PRIMARY,
    PRIMARY_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    FONT_HEADING,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    PANEL_CORNER_RADIUS,
    BTN_HEIGHT,
    BTN_CORNER_RADIUS,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
    get_speaker_colour,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SpeakerAliaser(ctk.CTkToplevel):
    """Modal dialog for assigning human-readable names"""

    def __init__(
        self,
        master,
        speaker_map: dict,
        on_apply: callable = None,
    ):
        super().__init__(master)

        self.speaker_map = dict(speaker_map)  # Copy to edit
        self.on_apply = on_apply
        self.name_entries = {}

        self.title("Assign Speaker Names")
        self.geometry("420x400")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)

        # Make modal — grab focus
        self.transient(master)
        self.grab_set()

        self._build_ui()

        # Centre on parent
        self.after(10, self._centre_on_parent)

    def _centre_on_parent(self):
        """Position the dialog centred over the main window."""
        self.update_idletasks()
        parent = self.master

        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        w = self.winfo_width()
        h = self.winfo_height()

        x = px + (pw - w) // 2
        y = py + (ph - h) // 2

        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Construct the speaker name entry form."""

        title = ctk.CTkLabel(
            self,
            text="Speaker Names",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY,
        )
        title.pack(pady=(SPACING_LG, SPACING_SM))

        subtitle = ctk.CTkLabel(
            self,
            text="Assign names to update the transcript, tasks, and summary.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
        )
        subtitle.pack(pady=(0, SPACING_LG))

        entries_frame = ctk.CTkFrame(self, fg_color="transparent")
        entries_frame.pack(fill="both", expand=True, padx=SPACING_LG)

        sorted_speakers = sorted(self.speaker_map.keys())

        for i, speaker_label in enumerate(sorted_speakers):
            current_name = self.speaker_map.get(speaker_label, speaker_label)
            colour = get_speaker_colour(i)

            row = ctk.CTkFrame(entries_frame, fg_color="transparent")
            row.pack(fill="x", pady=(0, SPACING_MD))

            # Colour dot + original label
            dot = ctk.CTkLabel(
                row,
                text="●",
                font=FONT_BODY,
                text_color=colour,
                width=20,
            )
            dot.pack(side="left")

            label = ctk.CTkLabel(
                row,
                text=speaker_label,
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
                width=100,
                anchor="w",
            )
            label.pack(side="left", padx=(SPACING_SM, SPACING_MD))

            # Name entry
            entry = ctk.CTkEntry(
                row,
                font=FONT_BODY,
                fg_color=BG_INPUT,
                border_color=SURFACE,
                text_color=TEXT_PRIMARY,
                placeholder_text="Enter name...",
                height=34,
            )
            entry.pack(side="left", fill="x", expand=True)

            # Pre-fill if already aliased
            if current_name != speaker_label:
                entry.insert(0, current_name)

            self.name_entries[speaker_label] = entry

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(
            fill="x",
            padx=SPACING_LG,
            pady=(SPACING_MD, SPACING_LG),
        )

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            font=FONT_BODY,
            fg_color=SURFACE,
            hover_color=PRIMARY_HOVER,
            height=BTN_HEIGHT,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._cancel,
        )
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(0, SPACING_SM))

        apply_btn = ctk.CTkButton(
            btn_frame,
            text="Apply Names",
            font=FONT_BODY_BOLD,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            height=BTN_HEIGHT,
            corner_radius=BTN_CORNER_RADIUS,
            command=self._apply,
        )
        apply_btn.pack(side="left", expand=True, fill="x", padx=(SPACING_SM, 0))

    def _apply(self):
        """Read entries, update speaker_map, fire callback."""
        for speaker_label, entry in self.name_entries.items():
            name = entry.get().strip()
            if name:
                self.speaker_map[speaker_label] = name
            else:
                # If cleared, revert to original label
                self.speaker_map[speaker_label] = speaker_label

        logger.info(f"Speaker aliases applied: {self.speaker_map}")

        if self.on_apply:
            self.on_apply(self.speaker_map)

        self.destroy()

    def _cancel(self):
        """Close without applying changes."""
        self.destroy()
