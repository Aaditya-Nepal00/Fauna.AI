"""
Folder watcher for real-time image processing.
Watches a directory for new image files and automatically
runs them through the full pipeline as they appear.

Usage: python -m app.watcher <survey_id> <camera_id> <watch_folder>
This simulates real-time camera trap capture for field demos.
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

from app.database import AsyncSessionLocal
from app.pipeline.orchestrator import PipelineOrchestrator


class FaunaWatcher:
    """
    Watches a folder for new .jpg/.jpeg/.png files.
    Each new file is immediately passed to PipelineOrchestrator.
    Results are printed to console in real time.
    Used for live demo: drop an image into the watched folder → alert fires instantly.
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    def __init__(self, survey_id: str, camera_id: str, watch_path: str):
        self.survey_id = survey_id
        self.camera_id = camera_id
        self.watch_path = Path(watch_path)
        self.logger = logging.getLogger(__name__)
        self.orchestrator = PipelineOrchestrator()

    def start(self):
        """Start watching. Blocks until KeyboardInterrupt."""
        from watchdog.events import FileCreatedEvent, FileSystemEventHandler
        from watchdog.observers import Observer

        watcher = self

        class ImageHandler(FileSystemEventHandler):
            def on_created(self, event: FileCreatedEvent):
                if event.is_directory:
                    return
                path = Path(event.src_path)
                if path.suffix.lower() not in watcher.SUPPORTED_EXTENSIONS:
                    return
                # Small delay to ensure file is fully written before reading
                time.sleep(0.5)
                watcher._handle_new_image(str(path))

        observer = Observer()
        observer.schedule(ImageHandler(), str(self.watch_path), recursive=False)
        observer.start()
        self.logger.info(
            f"Watching {self.watch_path} | survey={self.survey_id} camera={self.camera_id}"
        )
        print(f"\n🌿 Fauna.AI Watcher active — drop images into: {self.watch_path}\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def _handle_new_image(self, image_path: str):
        """Synchronously process one new image and print result."""
        async def _run():
            async with AsyncSessionLocal() as db:
                result = await self.orchestrator.process_image(
                    image_path, self.camera_id, db
                )
                self._print_result(result)

        asyncio.run(_run())

    def _print_result(self, result):
        band_symbol = {"CONFIRMED": "🟢", "REVIEW": "🟡", "EMPTY": "⚫"}.get(result.band, "?")
        print(f"{band_symbol} {result.filename}")
        if result.species:
            print(f"   └─ {result.species} ({result.species_confidence}) × {result.count_estimate}")
        print(f"   └─ {result.processing_ms}ms\n")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python -m app.watcher <survey_id> <camera_id> <watch_folder>")
        sys.exit(1)
    FaunaWatcher(sys.argv[1], sys.argv[2], sys.argv[3]).start()
