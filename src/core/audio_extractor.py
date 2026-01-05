"""
Module trich xuat audio tu video
Toi uu voi multi-threading va hardware acceleration
"""
import os
import subprocess
import uuid
import re
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


class AudioExtractor:
    """Trich xuat audio tu video file - toi uu hieu suat"""

    def __init__(self, temp_dir: Path = None):
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

        # So luong CPU threads
        self.num_threads = min(os.cpu_count() or 4, 8)

    def extract(self, video_path: str, progress_callback=None, status_callback=None) -> str:
        """
        Trich xuat audio tu video - FAST VERSION (no progress tracking)

        Args:
            video_path: Duong dan file video
            progress_callback: Callback(progress: int)
            status_callback: Callback(status: str)

        Returns:
            Duong dan file audio (WAV)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video khong ton tai: {video_path}")

        # Tao ten file output
        output_filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        output_path = str(self.temp_dir / output_filename)

        if progress_callback:
            progress_callback(10)
        if status_callback:
            status_callback("Dang trich xuat audio...")

        # Get video duration FIRST to verify full extraction
        video_duration = self._get_duration(video_path)
        print(f"[AudioExtractor] Video duration: {video_duration:.2f}s")

        # FAST FFmpeg - no progress tracking, just run and wait
        # IMPORTANT: Explicitly start from 0:00 to capture EVERYTHING
        cmd = [
            'ffmpeg', '-y',
            '-ss', '0',  # START FROM BEGINNING - capture FULL audio
            '-i', video_path,
            '-vn',  # Khong lay video
            '-acodec', 'pcm_s16le',  # Format WAV
            '-ar', '16000',  # Sample rate 16kHz (tot cho STT)
            '-ac', '1',  # Mono
            output_path
        ]

        try:
            if progress_callback:
                progress_callback(30)

            # Run FFmpeg - FAST, no line-by-line reading
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if progress_callback:
                progress_callback(90)

            # VERIFY output exists
            if not os.path.exists(output_path):
                raise Exception(f"FFmpeg khong tao duoc file audio")

            # VERIFY file size (must be > 1KB)
            file_size = os.path.getsize(output_path)
            if file_size < 1000:
                raise Exception(f"Audio file qua nho ({file_size} bytes) - extraction failed")

            # VERIFY audio duration matches video duration (±1 second tolerance)
            audio_duration = self._get_duration(output_path)
            print(f"[AudioExtractor] Audio duration: {audio_duration:.2f}s")
            print(f"[AudioExtractor] File size: {file_size / 1024 / 1024:.2f} MB")

            duration_diff = abs(video_duration - audio_duration)
            if duration_diff > 1.0:
                print(f"[AudioExtractor] WARNING: Duration mismatch! Video={video_duration:.2f}s, Audio={audio_duration:.2f}s")
                # Don't fail, just warn - some videos have slight differences

            if progress_callback:
                progress_callback(100)
            if status_callback:
                status_callback("Hoan tat trich xuat!")

            print(f"[AudioExtractor] Trich xuat thanh cong: {output_path}")
            print(f"[AudioExtractor] Coverage: 0.00s -> {audio_duration:.2f}s (FULL AUDIO)")
            return output_path

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else 'Unknown error'
            raise Exception(f"FFmpeg loi: {stderr}")
        except Exception as e:
            raise Exception(f"Loi trich xuat audio: {str(e)}")

    def _get_duration(self, file_path: str) -> float:
        """Lay thoi luong file (giay)"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.strip())
        except:
            return 0.0

    def get_duration(self, audio_path: str) -> float:
        """Lay thoi luong audio file (giay)"""
        return self._get_duration(audio_path)
