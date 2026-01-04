"""
Module trich xuat audio tu video
"""
import os
import subprocess
import uuid
from pathlib import Path


class AudioExtractor:
    """Trich xuat audio tu video file"""

    def __init__(self, temp_dir: Path = None):
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

    def extract(self, video_path: str, progress_callback=None) -> str:
        """
        Trich xuat audio tu video

        Args:
            video_path: Duong dan file video
            progress_callback: Callback(progress: int)

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

        # Dung FFmpeg de trich xuat audio
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vn',  # Khong lay video
            '-acodec', 'pcm_s16le',  # Format WAV
            '-ar', '16000',  # Sample rate 16kHz (tot cho STT)
            '-ac', '1',  # Mono
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if progress_callback:
                progress_callback(90)

            if not os.path.exists(output_path):
                raise Exception(f"FFmpeg loi: {result.stderr}")

            if progress_callback:
                progress_callback(100)

            print(f"[AudioExtractor] Trich xuat thanh cong: {output_path}")
            return output_path

        except Exception as e:
            raise Exception(f"Loi trich xuat audio: {str(e)}")

    def get_duration(self, audio_path: str) -> float:
        """Lay thoi luong audio file (giay)"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.strip())
        except:
            return 0.0
