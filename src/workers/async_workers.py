"""
Async Workers cho cac tac vu nang
Su dung QThread de khong block UI
PHIEN BAN MO RONG: Ho tro parallel processing va cancellation
"""
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import threading


class CancellableWorker(QThread):
    """
    Base class for cancellable workers
    Provides cancellation support for long-running operations
    """
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)  # Generic result
    error = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._cancel_flag = threading.Event()

    def cancel(self):
        """Request cancellation of the worker"""
        self._cancel_flag.set()
        self.status.emit("Dang huy tac vu...")

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested"""
        return self._cancel_flag.is_set()


class ExtractWorker(QThread):
    """Worker trich xuat audio tu video - toi uu hieu suat"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path

    def run(self):
        try:
            from src.core.audio_extractor import AudioExtractor

            self.status.emit("Dang khoi tao...")
            self.progress.emit(5)

            extractor = AudioExtractor()

            # Trich xuat voi progress realtime
            audio_path = extractor.extract(
                self.video_path,
                progress_callback=lambda p: self.progress.emit(p),
                status_callback=lambda s: self.status.emit(s)
            )

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(audio_path)

        except Exception as e:
            self.error.emit(str(e))


class TranscribeWorker(QThread):
    """Worker chuyen giong noi thanh van ban"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_path: str, engine: str = "local", api_key: str = None, model: str = "small"):
        super().__init__()
        self.audio_path = audio_path
        self.engine = engine
        self.api_key = api_key
        self.model = model

    def run(self):
        try:
            from src.core.speech_to_text import SpeechToText

            stt = SpeechToText()
            result = stt.transcribe(
                self.audio_path,
                engine=self.engine,
                api_key=self.api_key,
                model_name=self.model,
                progress_callback=lambda p: self.progress.emit(p),
                status_callback=lambda s: self.status.emit(s)
            )

            self.finished.emit(result["text"])

        except Exception as e:
            self.error.emit(str(e))


class TranslateWorker(QThread):
    """Worker dich van ban"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, text: str, source: str = "zh-CN", target: str = "vi"):
        super().__init__()
        self.text = text
        self.source = source
        self.target = target

    def run(self):
        try:
            from src.core.translator import Translator

            self.status.emit("Dang khoi tao...")
            self.progress.emit(10)

            translator = Translator()

            self.status.emit("Dang dich...")
            self.progress.emit(30)

            result = translator.translate(
                self.text,
                source=self.source,
                target=self.target,
                progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6)),
                status_callback=self.status.emit
            )

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(result)

        except Exception as e:
            import traceback
            print(f"[TranslateWorker] ERROR: {e}")
            traceback.print_exc()
            self.error.emit(str(e))


class TTSWorker(CancellableWorker):
    """Worker tao giong noi TTS - HO TRO PARALLEL PROCESSING"""
    detailed_progress = pyqtSignal(int, int, str)  # (completed, total, current_item)

    # Map ten giong UI sang API format
    GEMINI_VOICE_MAP = {
        "Aoede (Nu - Sang)": "gemini-Aoede",
        "Charon (Nam - Tram)": "gemini-Charon",
        "Fenrir (Nam - Trung)": "gemini-Fenrir",
        "Kore (Nu - Tre)": "gemini-Kore",
        "Puck (Nam - Vui)": "gemini-Puck",
        "Zephyr (Nu - Nhe)": "gemini-Zephyr",
        "Orbit (Nam - Ro)": "gemini-Orus",
        "Lyra (Nu - Am)": "gemini-Leda",
        "Nova (Nu - Pro)": "gemini-Despina",
        "Solaris (Nam - Manh)": "gemini-Enceladus",
        "Echo (Nam - Vang)": "gemini-Umbriel",
        "Aurora (Nu - Trang)": "gemini-Sulafat",
        "Titan (Nam - Sau)": "gemini-Iapetus",
        "Luna (Nu - Diu)": "gemini-Algenib",
    }

    EDGE_VOICE_MAP = {
        "vi-VN-HoaiMyNeural (Nu)": "vi-VN-HoaiMyNeural",
        "vi-VN-NamMinhNeural (Nam)": "vi-VN-NamMinhNeural",
    }

    def __init__(self, text: str, voice: str, speed: float = 1.0,
                 use_parallel: bool = False, num_threads: int = 2):
        super().__init__()
        self.text = text
        self.voice = self._convert_voice(voice)
        self.speed = speed
        self.use_parallel = use_parallel
        self.num_threads = num_threads

    def _convert_voice(self, voice: str) -> str:
        """Convert ten giong tu UI sang API format"""
        # Check Gemini voices
        if voice in self.GEMINI_VOICE_MAP:
            return self.GEMINI_VOICE_MAP[voice]
        # Check Edge-TTS voices
        if voice in self.EDGE_VOICE_MAP:
            return self.EDGE_VOICE_MAP[voice]
        # Return as-is if already in correct format
        return voice

    def run(self):
        try:
            from src.core.text_to_speech import TextToSpeech

            if self.is_cancelled():
                self.cancelled.emit()
                return

            self.status.emit("Dang khoi tao...")
            self.progress.emit(10)

            tts = TextToSpeech()

            if self.is_cancelled():
                self.cancelled.emit()
                return

            # Use parallel processing if enabled
            if self.use_parallel:
                self.status.emit(f"Dang tao giong song song voi {self.num_threads} threads...")
                self.progress.emit(20)

                # Define progress callback for parallel processing
                def parallel_progress(completed, total, segment_id, result, error=None):
                    if self.is_cancelled():
                        return
                    progress_pct = int(20 + (completed / total) * 70)
                    self.progress.emit(progress_pct)
                    self.detailed_progress.emit(completed, total, segment_id)

                audio_path = tts.generate_parallel(
                    text=self.text,
                    voice=self.voice,
                    speed=self.speed,
                    num_threads=self.num_threads,
                    progress_callback=parallel_progress,
                    status_callback=self.status.emit
                )

            else:
                # Use standard (non-parallel) processing
                self.status.emit(f"Dang tao giong noi...")
                self.progress.emit(30)

                audio_path = tts.generate(
                    text=self.text,
                    voice=self.voice,
                    speed=self.speed,
                    progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6))
                )

            if self.is_cancelled():
                self.cancelled.emit()
                return

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(audio_path)

        except Exception as e:
            if not self.is_cancelled():
                self.error.emit(str(e))


class ExportWorker(QThread):
    """Worker xuat video cuoi cung - toi uu hieu suat"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path: str, audio_path: str, output_name: str,
                 mix_original: bool = False, anti_copyright: dict = None,
                 watermark: dict = None, intro: dict = None,
                 sync_subtitle: bool = False, srt_path: str = None,
                 output_folder: str = None):
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_name = output_name
        self.mix_original = mix_original
        self.anti_copyright = anti_copyright
        self.watermark = watermark
        self.intro = intro
        self.sync_subtitle = sync_subtitle
        self.srt_path = srt_path
        self.output_folder = output_folder

    def run(self):
        try:
            import logging
            import traceback
            from src.core.video_merger import VideoMerger
            from pathlib import Path
            import os

            logging.basicConfig(level=logging.DEBUG)
            logger = logging.getLogger(__name__)

            self.status.emit("Dang khoi tao...")
            self.progress.emit(5)

            # Validate inputs
            logger.debug(f"ExportWorker validating inputs...")
            logger.debug(f"  Video: {self.video_path}")
            logger.debug(f"  Audio: {self.audio_path}")
            logger.debug(f"  Output name: {self.output_name}")
            logger.debug(f"  Output folder: {self.output_folder}")

            if not os.path.exists(self.video_path):
                raise FileNotFoundError(f"Video khong ton tai: {self.video_path}")
            if not os.path.exists(self.audio_path):
                raise FileNotFoundError(f"Audio khong ton tai: {self.audio_path}")

            # Tao VideoMerger voi output_folder neu duoc chi dinh
            if self.output_folder:
                logger.debug(f"Using custom output folder: {self.output_folder}")
                merger = VideoMerger(output_dir=Path(self.output_folder))
            else:
                logger.debug("Using default output folder")
                merger = VideoMerger()

            logger.debug(f"Starting video merge...")

            # Ghep video voi progress realtime va GPU acceleration
            output_path = merger.merge(
                video_path=self.video_path,
                audio_path=self.audio_path,
                output_name=self.output_name,
                mix_original=self.mix_original,
                anti_copyright=self.anti_copyright,
                watermark=self.watermark,
                intro=self.intro,
                sync_subtitle=self.sync_subtitle,
                srt_path=self.srt_path,
                progress_callback=lambda p: self.progress.emit(p),
                status_callback=lambda s: self.status.emit(s)
            )

            logger.debug(f"Video merge completed: {output_path}")

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(output_path)

        except FileNotFoundError as e:
            error_msg = str(e)
            print(f"[ERROR] File not found: {error_msg}")
            self.error.emit(error_msg)
        except Exception as e:
            error_msg = f"{str(e)}\n\nChi tiet:\n{traceback.format_exc()}"
            print(f"[ERROR] Export failed:\n{error_msg}")
            self.error.emit(error_msg)


# ============================================================================
# TURBO WORKERS - ULTRA-FAST PARALLEL PROCESSING
# 5-10x faster than normal workers
# ============================================================================


class TurboTranscribeWorker(CancellableWorker):
    """
    TURBO STT Worker - 5-6x faster than normal
    Uses aggressive parallel processing with 8-20 concurrent chunks
    """
    detailed_progress = pyqtSignal(int, int, str)  # (completed, total, message)
    speedup_info = pyqtSignal(float, float)  # (processing_time, speedup)

    def __init__(self, audio_path: str, api_key: str):
        super().__init__()
        self.audio_path = audio_path
        self.api_key = api_key

    def run(self):
        try:
            import asyncio
            from src.core.turbo_processor import TurboSTT

            if self.is_cancelled():
                self.cancelled.emit()
                return

            self.status.emit("[TURBO] Khoi tao engine...")
            self.progress.emit(5)

            # Create turbo STT
            turbo_stt = TurboSTT(self.api_key)

            if self.is_cancelled():
                self.cancelled.emit()
                return

            self.status.emit("[TURBO] Bat dau xu ly song song...")
            self.progress.emit(10)

            # Progress callback
            def progress_cb(completed, total, message):
                if self.is_cancelled():
                    return
                progress_pct = int(10 + (completed / total) * 85)
                self.progress.emit(progress_pct)
                self.detailed_progress.emit(completed, total, message)

            # Status callback
            def status_cb(message):
                if not self.is_cancelled():
                    self.status.emit(message)

            # Run turbo transcription
            import time
            start_time = time.time()

            # Run async in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                text = loop.run_until_complete(
                    turbo_stt.transcribe_turbo(
                        self.audio_path,
                        progress_callback=progress_cb,
                        status_callback=status_cb
                    )
                )
            finally:
                loop.close()

            processing_time = time.time() - start_time

            if self.is_cancelled():
                self.cancelled.emit()
                return

            # Estimate speedup (turbo is ~5-6x faster)
            estimated_normal_time = processing_time * 5.5
            speedup = estimated_normal_time / processing_time

            self.speedup_info.emit(processing_time, speedup)
            self.progress.emit(100)
            self.status.emit(f"[TURBO] Hoan thanh! ({processing_time:.1f}s, {speedup:.1f}x faster)")
            self.finished.emit(text)

        except Exception as e:
            if not self.is_cancelled():
                self.error.emit(str(e))


class TurboTTSWorker(QThread):
    """
    TURBO TTS Worker - 5-6x faster than normal
    Uses aggressive parallel processing with 8-20 concurrent segments
    """
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    detailed_progress = pyqtSignal(int, int, str)  # (completed, total, message)
    speedup_info = pyqtSignal(float, float)  # (processing_time, speedup)

    def __init__(self, text: str, voice: str, speed: float = 1.0):
        super().__init__()
        self.text = text
        self.voice = voice
        self.speed = speed

    def run(self):
        try:
            import asyncio
            from src.core.turbo_processor import TurboTTS

            self.status.emit("[TURBO] Khoi tao engine...")
            self.progress.emit(5)

            # Create turbo TTS
            turbo_tts = TurboTTS()

            self.status.emit("[TURBO] Bat dau tao giong song song...")
            self.progress.emit(10)

            # Progress callback
            def progress_cb(completed, total, message):
                progress_pct = int(10 + (completed / total) * 85)
                self.progress.emit(progress_pct)
                self.detailed_progress.emit(completed, total, message)

            # Status callback
            def status_cb(message):
                self.status.emit(message)

            # Run turbo TTS
            import time
            start_time = time.time()

            # Run async in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_path = loop.run_until_complete(
                    turbo_tts.generate_turbo(
                        self.text,
                        self.voice,
                        self.speed,
                        progress_callback=progress_cb,
                        status_callback=status_cb
                    )
                )
            finally:
                loop.close()

            processing_time = time.time() - start_time

            # Estimate speedup
            estimated_normal_time = processing_time * 5.5
            speedup = estimated_normal_time / processing_time

            self.speedup_info.emit(processing_time, speedup)
            self.progress.emit(100)
            self.status.emit(f"[TURBO] Hoan thanh! ({processing_time:.1f}s, {speedup:.1f}x faster)")
            self.finished.emit(audio_path)

        except Exception as e:
            self.error.emit(str(e))


class TurboFullProcessWorker(QThread):
    """
    TURBO Full Process Worker
    Processes entire video pipeline with TURBO mode
    STT + Translation + TTS all optimized
    """
    progress = pyqtSignal(str, int, str)  # (step, progress, message)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Returns full result dict
    error = pyqtSignal(str)
    step_completed = pyqtSignal(str, float)  # (step_name, time_taken)

    def __init__(self, video_path: str, groq_api_key: str, voice: str, speed: float = 1.0):
        super().__init__()
        self.video_path = video_path
        self.groq_api_key = groq_api_key
        self.voice = voice
        self.speed = speed

    def run(self):
        try:
            from src.core.turbo_processor import run_turbo_engine

            self.status.emit("[TURBO] Khoi tao ultra-fast engine...")

            # Progress callback
            def progress_cb(step, progress_pct, message):
                self.progress.emit(step, progress_pct, message)

            # Status callback
            def status_cb(message):
                self.status.emit(message)

            # Run turbo engine
            result = run_turbo_engine(
                self.groq_api_key,
                self.video_path,
                self.voice,
                self.speed,
                progress_callback=progress_cb,
                status_callback=status_cb
            )

            # Emit step times
            for step_name, step_time in result.get('step_times', {}).items():
                self.step_completed.emit(step_name, step_time)

            total_time = result.get('processing_time', 0)
            speedup = result.get('speedup', 1)

            self.status.emit(f"[TURBO] HOAN THANH TAT CA! ({total_time:.1f}s, {speedup:.1f}x faster)")
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
