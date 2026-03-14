# main application window
import customtkinter as ctk

from ui.styles import (
    BG_DARK,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    CUSTOMTKINTER_THEME,
    CUSTOMTKINTER_COLOUR_THEME,
    FONT_HEADING,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class QuorumApp(ctk.CTk):
    """Root application window for Quorum."""

    def __init__(self):
        super().__init__()

        self.title("Quorum — Meeting Intelligence")
        self.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=BG_DARK)

        ctk.set_appearance_mode(CUSTOMTKINTER_THEME)
        ctk.set_default_color_theme(CUSTOMTKINTER_COLOUR_THEME)

        self.pipeline_results = None  # Populated after processing
        self.audio_file_path = None   # Path to the loaded audio file
        self.current_screen = None    # Reference to active screen frame

        self.show_input_screen()

        logger.info("Quorum application initialised")

    def show_input_screen(self):
        """Switch to the input/configuration screen."""
        self._clear_screen()

        from ui.input_screen import InputScreen

        self.current_screen = InputScreen(
            master=self,
            on_processing_complete=self._on_processing_complete,
        )
        self.current_screen.pack(fill="both", expand=True)

        logger.info("Switched to input screen")

    def show_output_screen(self):
        """Switch to the output/results screen."""
        if self.pipeline_results is None:
            logger.warning("Cannot show output screen — no results")
            return

        self._clear_screen()

        from ui.output_screen import OutputScreen

        self.current_screen = OutputScreen(
            master=self,
            results=self.pipeline_results,
            audio_path=self.audio_file_path,
            on_back=self.show_input_screen,
        )
        self.current_screen.pack(fill="both", expand=True)

        logger.info("Switched to output screen")

    def _on_processing_complete(self, results: dict, audio_path: str):
        """Callback fired by InputScreen when the pipeline finishes."""
        self.pipeline_results = results
        self.audio_file_path = audio_path

        logger.info(
            f"Pipeline complete — "
            f"{len(results.get('segments', []))} segments, "
            f"{len(results.get('tasks', []))} tasks"
        )

        self.show_output_screen()

    def _clear_screen(self):
        if self.current_screen is not None:
            self.current_screen.destroy()
            self.current_screen = None


def launch():
    """Entry point — creates and runs the application."""
    app = QuorumApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
