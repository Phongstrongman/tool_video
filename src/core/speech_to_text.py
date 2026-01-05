"""
Speech to Text - VERSION KHONG CAN PYDUB CHO FILE NHO
=====================================================
- File < 25MB: Gui truc tiep, KHONG can pydub
- File > 25MB: Moi can pydub de chia chunks
"""

import os
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed


class SpeechToText:
    """Speech to Text - TOI UU TOC DO TOI DA"""

    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    CHUNK_DURATION_SEC = 120  # 2 phut - chunks nho hon = upload nhanh hon
    MAX_RETRIES = 2  # Giam retry de khong mat thoi gian
    MAX_WORKERS = 2  # GIAM xuong 2 de TRANH RATE LIMIT cua Groq API

    def __init__(self):
        self.model = None
        self.current_model = None

    def transcribe_with_groq(
        self,
        audio_path: str,
        api_key: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> dict:
        """Transcribe bang Groq API"""

        # Import groq TRONG HAM, khong o dau file
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Chua cai groq! Chay: pip install groq")

        client = Groq(api_key=api_key)

        if progress_callback:
            progress_callback(10)

        # Kiem tra file size BANG OS, khong can pydub
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)

        if status_callback:
            status_callback(f"File size: {file_size_mb:.1f} MB")

        if file_size <= self.MAX_FILE_SIZE:
            # FILE NHO - Gui truc tiep, KHONG CAN PYDUB
            return self._transcribe_direct(client, audio_path, progress_callback, status_callback)
        else:
            # FILE LON - Can chia chunks, can pydub
            return self._transcribe_large_file(client, audio_path, progress_callback, status_callback)

    def _transcribe_direct(
        self,
        client,
        audio_path: str,
        progress_callback=None,
        status_callback=None
    ) -> dict:
        """Gui file truc tiep - KHONG CAN PYDUB"""

        if status_callback:
            status_callback("Dang gui truc tiep len Groq API...")

        if progress_callback:
            progress_callback(30)

        for attempt in range(self.MAX_RETRIES):
            try:
                with open(audio_path, "rb") as f:
                    # Dung whisper-large-v3-turbo - NHANH HON 8X
                    response = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=f,
                        response_format="verbose_json",
                        language="zh"
                    )

                if progress_callback:
                    progress_callback(100)

                if status_callback:
                    status_callback(f"Hoan thanh: {len(response.text)} ky tu")

                return {
                    "text": response.text,
                    "language": getattr(response, 'language', 'zh'),
                    "segments": [],
                    "duration": getattr(response, 'duration', 0),
                    "success_rate": 1.0
                }

            except Exception as e:
                error_str = str(e).lower()

                if "rate_limit" in error_str or "429" in error_str:
                    # TOI UU: GIAM wait time tu 60s xuong 10s
                    wait_time = 10 * (attempt + 1)
                    if status_callback:
                        status_callback(f"Rate limit, cho {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if attempt < self.MAX_RETRIES - 1:
                    if status_callback:
                        status_callback(f"Loi, thu lai lan {attempt + 2}...")
                    time.sleep(2)
                else:
                    raise Exception(f"Loi transcribe: {str(e)}")

        raise Exception("Het so lan thu lai")

    def _transcribe_large_file(
        self,
        client,
        audio_path: str,
        progress_callback=None,
        status_callback=None
    ) -> dict:
        """
        Xu ly file lon - XU LY SONG SONG DE TOI UU TOC DO
        File > 25MB duoc chia thanh chunks va xu ly song song (3-5 chunks cung luc)
        """

        # CHI IMPORT PYDUB KHI THUC SU CAN
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError("File qua lon (>25MB), can pydub de chia nho! Chay: pip install pydub")

        if status_callback:
            status_callback("File lon, dang chia nho...")

        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)
        chunk_length_ms = self.CHUNK_DURATION_SEC * 1000

        chunks = [audio[i:i+chunk_length_ms] for i in range(0, duration_ms, chunk_length_ms)]
        total_chunks = len(chunks)

        if status_callback:
            status_callback(f"Chia thanh {total_chunks} doan - XU LY SONG SONG...")

        print(f"[STT] Total chunks: {total_chunks}, Duration: {duration_ms/1000:.1f}s")

        # Prepare results array to maintain order
        results = [None] * total_chunks
        success_count = 0

        # XU LY SONG SONG VOI THREADPOOLEXECUTOR - TOI UU TOC DO
        max_workers = min(self.MAX_WORKERS, total_chunks)  # Toi da 6 chunks song song

        if status_callback:
            status_callback(f"[TURBO] Xu ly {max_workers} chunks song song...")

        print(f"[STT] Processing {total_chunks} chunks with {max_workers} workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunk processing tasks
            future_to_index = {}
            for i, chunk in enumerate(chunks):
                future = executor.submit(self._process_chunk_parallel, client, chunk, i, total_chunks)
                future_to_index[future] = i

            # Process completed chunks as they finish
            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    text = future.result()
                    if text:
                        results[idx] = text
                        success_count += 1
                        print(f"[STT] Chunk {idx+1}/{total_chunks} OK: {len(text)} chars")
                    else:
                        # Chunk failed but don't lose position - mark as empty
                        results[idx] = ""
                        print(f"[STT] Chunk {idx+1}/{total_chunks} FAILED - marked empty")
                    completed += 1

                    if progress_callback:
                        progress = int(10 + (completed / total_chunks) * 85)
                        progress_callback(progress)

                    if status_callback:
                        status_callback(f"Xong {completed}/{total_chunks} doan")

                except Exception as e:
                    # IMPORTANT: Mark failed chunk as empty to maintain order
                    results[idx] = ""
                    print(f"[STT] Chunk {idx+1}/{total_chunks} EXCEPTION: {str(e)[:50]}")
                    if status_callback:
                        status_callback(f"Loi doan {idx+1}: {str(e)[:30]}")
                    completed += 1

        if progress_callback:
            progress_callback(100)

        # Join all non-None results in order
        all_text = [text for text in results if text]

        # IMPORTANT: Log summary to help debug
        failed_chunks = total_chunks - success_count
        print(f"[STT] SUMMARY: {success_count}/{total_chunks} chunks OK, {failed_chunks} failed")
        print(f"[STT] Total text: {sum(len(t) for t in all_text)} chars")

        if failed_chunks > 0:
            print(f"[STT] WARNING: {failed_chunks} chunks failed - missing text!")

        return {
            "text": " ".join(all_text),
            "language": "zh",
            "success_rate": success_count / total_chunks if total_chunks > 0 else 0
        }

    def _process_chunk_parallel(self, client, chunk, chunk_index: int, total_chunks: int) -> str:
        """
        Xu ly 1 chunk - duoc goi song song boi ThreadPoolExecutor

        Args:
            client: Groq client
            chunk: AudioSegment chunk
            chunk_index: Index cua chunk (de maintain order)
            total_chunks: Tong so chunks

        Returns:
            Transcribed text hoac empty string neu loi
        """
        temp_path = None
        try:
            # Export chunk to temp file - GIAM bitrate xuong 24k de upload nhanh hon
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
                # 24k bitrate = file nho hon 30%, upload nhanh hon
                chunk.export(temp_path, format="mp3", bitrate="24k")

            # Transcribe chunk with retry
            text = self._transcribe_chunk(client, temp_path, status_callback=None)
            return text if text else ""

        except Exception as e:
            print(f"[ERROR] Chunk {chunk_index+1}/{total_chunks} failed: {str(e)}")
            return ""

        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    print(f"[WARNING] Failed to delete temp file {temp_path}: {e}")

    def _transcribe_chunk(self, client, temp_path: str, status_callback=None) -> str:
        """Transcribe 1 chunk - TOI UU TOC DO TOI DA"""
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                with open(temp_path, "rb") as f:
                    # Dung whisper-large-v3-turbo - NHANH HON 8X
                    response = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=f,
                        response_format="verbose_json",  # LAY TIMESTAMP CHO TUNG SEGMENT
                        language="zh"
                    )
                elapsed = time.time() - start_time
                print(f"[STT] Chunk done in {elapsed:.1f}s")
                return response.text
            except Exception as e:
                error_msg = str(e).lower()
                if "rate_limit" in error_msg or "429" in error_msg:
                    # Giam wait time xuong 5s
                    wait_time = 5 * (attempt + 1)
                    print(f"[STT] Rate limit! Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                if attempt < self.MAX_RETRIES - 1:
                    print(f"[STT] Error: {str(e)[:50]}, retrying...")
                    time.sleep(1)  # Giam tu 2s xuong 1s
        return ""

    def transcribe_local(
        self,
        audio_path: str,
        model_name: str = "small",
        progress_callback: Optional[Callable[[int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> dict:
        """Transcribe bang Local Whisper"""
        try:
            import whisper
        except ImportError:
            raise ImportError("Chua cai whisper! Chay: pip install openai-whisper")

        if self.current_model != model_name:
            if status_callback:
                status_callback(f"Dang load model {model_name}...")
            if progress_callback:
                progress_callback(5)
            self.model = whisper.load_model(model_name)
            self.current_model = model_name

        if progress_callback:
            progress_callback(10)
        if status_callback:
            status_callback("Dang transcribe...")

        result = self.model.transcribe(audio_path, language=None, verbose=False)

        if progress_callback:
            progress_callback(100)

        return {
            "text": result["text"].strip(),
            "language": result.get("language", "unknown"),
            "success_rate": 1.0
        }

    def transcribe(
        self,
        audio_path: str,
        engine: str = "local",
        api_key: str = None,
        model_name: str = "small",
        progress_callback=None,
        status_callback=None
    ) -> dict:
        """Ham chinh"""
        if engine == "groq" and api_key:
            return self.transcribe_with_groq(audio_path, api_key, progress_callback, status_callback)
        else:
            return self.transcribe_local(audio_path, model_name, progress_callback, status_callback)


def create_speech_to_text():
    return SpeechToText()


def transcribe_audio(
    audio_path: str,
    engine: str = "local",
    api_key: str = None,
    model_name: str = "small",
    progress_callback=None,
    status_callback=None
) -> dict:
    stt = SpeechToText()
    return stt.transcribe(audio_path, engine, api_key, model_name, progress_callback, status_callback)
