"""
Async Workers cho cac tac vu nang
Su dung QThread de khong block UI
"""
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


class ExtractWorker(QThread):
    """Worker trich xuat audio tu video"""
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
            self.progress.emit(10)

            extractor = AudioExtractor()

            self.status.emit("Dang trich xuat audio...")
            self.progress.emit(30)

            audio_path = extractor.extract(
                self.video_path,
                progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6))
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

    def __init__(self, audio_path: str, engine: str = "groq", api_key: str = None):
        super().__init__()
        self.audio_path = audio_path
        self.engine = engine
        self.api_key = api_key

    def run(self):
        try:
            from src.core.speech_to_text import SpeechToText

            self.status.emit("Dang khoi tao...")
            self.progress.emit(10)

            stt = SpeechToText(engine=self.engine, api_key=self.api_key)

            self.status.emit(f"Dang xu ly voi {self.engine}...")
            self.progress.emit(30)

            text = stt.transcribe(
                self.audio_path,
                progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6)),
                status_callback=self.status.emit
            )

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(text)

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
            self.error.emit(str(e))


class TTSWorker(QThread):
    """Worker tao giong noi TTS"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, text: str, engine: str, voice: str,
                 speed: float = 1.0, api_key: str = None):
        super().__init__()
        self.text = text
        self.engine = engine
        self.voice = voice
        self.speed = speed
        self.api_key = api_key

    def run(self):
        try:
            from src.core.text_to_speech import TextToSpeech

            self.status.emit("Dang khoi tao...")
            self.progress.emit(10)

            tts = TextToSpeech()

            self.status.emit(f"Dang tao giong noi voi {self.engine}...")
            self.progress.emit(30)

            audio_path = tts.generate(
                text=self.text,
                engine=self.engine,
                voice=self.voice,
                speed=self.speed,
                api_key=self.api_key,
                progress_callback=lambda p: self.progress.emit(30 + int(p * 0.6)),
                status_callback=self.status.emit
            )

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(audio_path)

        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    """Worker xuat video cuoi cung"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path: str, audio_path: str, output_name: str,
                 mix_original: bool = False, anti_copyright: dict = None,
                 watermark: dict = None, intro: dict = None,
                 sync_subtitle: bool = False, srt_path: str = None):
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

    def run(self):
        try:
            from src.core.video_merger import VideoMerger

            self.status.emit("Dang khoi tao...")
            self.progress.emit(10)

            merger = VideoMerger()

            self.status.emit("Dang ghep video...")
            self.progress.emit(20)

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
                progress_callback=lambda p: self.progress.emit(20 + int(p * 0.7))
            )

            self.progress.emit(100)
            self.status.emit("Hoan tat!")
            self.finished.emit(output_path)

        except Exception as e:
            self.error.emit(str(e))
