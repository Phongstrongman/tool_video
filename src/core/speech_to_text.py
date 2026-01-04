"""
Module Speech-to-Text - Ho tro nhieu engine
1. Local Whisper (offline)
2. Groq API (online, nhanh)
3. AssemblyAI (online, chinh xac)
"""
import os
from pathlib import Path


class SpeechToText:
    """Chuyen giong noi thanh van ban"""

    def __init__(self, temp_dir: Path = None):
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

    def transcribe(self, audio_path: str, model: str = "small",
                   engine: str = "groq", api_key: str = None,
                   progress_callback=None, status_callback=None) -> dict:
        """
        Chuyen giong noi thanh van ban

        Args:
            audio_path: Duong dan file audio
            model: Model whisper (tiny/base/small/medium/large)
            engine: Engine su dung (local/groq/assemblyai)
            api_key: API key (cho groq/assemblyai)
            progress_callback: Callback(progress: int)
            status_callback: Callback(status: str)

        Returns:
            dict: {"text": str, "language": str}
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio khong ton tai: {audio_path}")

        if engine == "local":
            return self._transcribe_local(audio_path, model, progress_callback, status_callback)
        elif engine == "groq":
            return self._transcribe_groq(audio_path, api_key, progress_callback, status_callback)
        elif engine == "assemblyai":
            return self._transcribe_assemblyai(audio_path, api_key, progress_callback, status_callback)
        else:
            raise ValueError(f"Engine khong hop le: {engine}")

    def _transcribe_local(self, audio_path: str, model: str,
                          progress_callback=None, status_callback=None) -> dict:
        """Transcribe bang Local Whisper"""
        try:
            import whisper
        except ImportError:
            raise Exception("openai-whisper chua cai. Chay: pip install openai-whisper")

        if status_callback:
            status_callback(f"Dang tai model {model}...")
        if progress_callback:
            progress_callback(10)

        # Load model
        whisper_model = whisper.load_model(model)

        if status_callback:
            status_callback("Dang nhan dang giong noi...")
        if progress_callback:
            progress_callback(30)

        # Transcribe
        result = whisper_model.transcribe(audio_path, language="zh")

        if progress_callback:
            progress_callback(100)

        return {
            "text": result["text"],
            "language": result.get("language", "zh")
        }

    def _transcribe_groq(self, audio_path: str, api_key: str,
                         progress_callback=None, status_callback=None) -> dict:
        """Transcribe bang Groq API (Whisper large-v3)"""
        try:
            from groq import Groq
        except ImportError:
            raise Exception("groq chua cai. Chay: pip install groq")

        if not api_key:
            raise ValueError("Groq API key khong duoc de trong!")

        if status_callback:
            status_callback("Dang ket noi Groq API...")
        if progress_callback:
            progress_callback(10)

        client = Groq(api_key=api_key)

        if status_callback:
            status_callback("Dang gui audio len Groq...")
        if progress_callback:
            progress_callback(30)

        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), audio_file.read()),
                model="whisper-large-v3",
                language="zh",
                response_format="json"
            )

        if progress_callback:
            progress_callback(100)

        return {
            "text": transcription.text,
            "language": "zh"
        }

    def _transcribe_assemblyai(self, audio_path: str, api_key: str,
                               progress_callback=None, status_callback=None) -> dict:
        """Transcribe bang AssemblyAI"""
        try:
            import assemblyai as aai
        except ImportError:
            raise Exception("assemblyai chua cai. Chay: pip install assemblyai")

        if not api_key:
            raise ValueError("AssemblyAI API key khong duoc de trong!")

        aai.settings.api_key = api_key

        if status_callback:
            status_callback("Dang upload audio len AssemblyAI...")
        if progress_callback:
            progress_callback(10)

        config = aai.TranscriptionConfig(
            language_code="zh"
        )

        transcriber = aai.Transcriber()

        if status_callback:
            status_callback("Dang nhan dang giong noi...")
        if progress_callback:
            progress_callback(30)

        transcript = transcriber.transcribe(audio_path, config=config)

        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"AssemblyAI loi: {transcript.error}")

        if progress_callback:
            progress_callback(100)

        return {
            "text": transcript.text,
            "language": "zh"
        }
