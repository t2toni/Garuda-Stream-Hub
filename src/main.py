import argparse
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure src and native are on python path
if hasattr(sys, "_MEIPASS"):
    sys.path.insert(0, sys._MEIPASS)
    sys.path.insert(0, os.path.join(sys._MEIPASS, "src"))
    sys.path.insert(0, os.path.join(sys._MEIPASS, "src", "native"))

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(CURRENT_DIR / "native") not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR / "native"))

from src.core.config import StreamConfig
from src.core.orchestrator import PipelineOrchestrator

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%H:%M:%S")

def run_cli_mode(orchestrator: PipelineOrchestrator):
    print("=======================================================")
    print("  GARUDA STREAM HUB - ONE-TAP STREAM PIPELINE (CLI)   ")
    print("=======================================================")

    def on_step(step, msg, ok):
        mark = "✔" if ok else "✖"
        print(f"[{mark}] Step {step}: {msg}")

    orchestrator.on_step_updated = on_step

    print("\n[+] Triggering One-Tap Pipeline Initialization...")
    ok, msg = orchestrator.initialize_pipeline()
    if ok:
        print(f"\n[✔] Pipeline active! Telemetry running. Press Ctrl+C to stop.")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[-] Teardown initiated by user...")
            orchestrator.teardown_pipeline()
            print("[✔] Teardown complete. Exiting.")
    else:
        print(f"\n[✖] Pipeline failed: {msg}")
        sys.exit(1)

def run_gui_mode(orchestrator: PipelineOrchestrator):
    from PyQt6.QtWidgets import QApplication
    from src.ui.main_window import MainWindow

    # Enable high DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Garuda Stream Hub")
    app.setApplicationDisplayName("Garuda Stream Hub")

    # Allow clean Ctrl+C handling in Qt event loop
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    window = MainWindow(orchestrator)
    window.show()

    sys.exit(app.exec())

def main():
    parser = argparse.ArgumentParser(description="Garuda Stream Hub - One-Tap Android Ultra-Low Latency Streaming Utility")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode without PyQt6 GUI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    config = StreamConfig.load()
    orchestrator = PipelineOrchestrator(config)

    if args.cli:
        run_cli_mode(orchestrator)
    else:
        run_gui_mode(orchestrator)

if __name__ == "__main__":
    main()
