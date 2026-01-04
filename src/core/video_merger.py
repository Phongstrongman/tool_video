"""
Module ghep video voi audio moi
Ho tro: anti-copyright effects, watermark, intro
"""
import os
import subprocess
import uuid
from pathlib import Path


class VideoMerger:
    """Ghep video voi audio moi va cac hieu ung"""

    def __init__(self, output_dir: Path = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

    def merge(self, video_path: str, audio_path: str, output_name: str,
              mix_original: bool = False, anti_copyright: dict = None,
              watermark: dict = None, intro: dict = None,
              sync_subtitle: bool = False, srt_path: str = None,
              progress_callback=None) -> str:
        """
        Ghep video voi audio moi

        Args:
            video_path: Duong dan video goc
            audio_path: Duong dan audio moi (TTS)
            output_name: Ten file output
            mix_original: Mix voi audio goc
            anti_copyright: Dict cac hieu ung chong ban quyen
            watermark: Dict cai dat watermark
            intro: Dict cai dat intro
            sync_subtitle: Hien thi subtitle tren video
            srt_path: Duong dan file SRT
            progress_callback: Callback(progress: int)

        Returns:
            Duong dan file output
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video khong ton tai: {video_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio khong ton tai: {audio_path}")

        # Tao output path
        output_filename = f"{output_name}.mp4"
        output_path = str(self.output_dir / output_filename)

        # Dam bao ten file khong trung
        counter = 1
        while os.path.exists(output_path):
            output_filename = f"{output_name}_{counter}.mp4"
            output_path = str(self.output_dir / output_filename)
            counter += 1

        if progress_callback:
            progress_callback(10)

        # Build FFmpeg filter
        video_filters = []
        audio_inputs = ['-i', audio_path]

        # Anti-copyright effects
        if anti_copyright:
            if anti_copyright.get("flip"):
                video_filters.append("hflip")
            if anti_copyright.get("zoom"):
                video_filters.append("scale=iw*1.05:ih*1.05,crop=iw/1.05:ih/1.05")
            if anti_copyright.get("effect"):
                video_filters.append("eq=brightness=0.02:contrast=1.02:saturation=1.05")
            if anti_copyright.get("remove_text"):
                # Crop phan text phia duoi (10% duoi cung)
                video_filters.append("crop=iw:ih*0.9:0:0")

        # Watermark
        if watermark and watermark.get("enabled") and watermark.get("text"):
            wm_text = watermark["text"]
            wm_pos = watermark.get("position", "Tren-Phai")

            # Vi tri watermark
            if wm_pos == "Tren-Phai":
                x, y = "w-tw-20", "20"
            elif wm_pos == "Tren-Trai":
                x, y = "20", "20"
            elif wm_pos == "Duoi-Phai":
                x, y = "w-tw-20", "h-th-20"
            else:  # Duoi-Trai
                x, y = "20", "h-th-20"

            # Escape text cho FFmpeg
            wm_text_escaped = wm_text.replace("'", "\\'").replace(":", "\\:")
            video_filters.append(
                f"drawtext=text='{wm_text_escaped}':fontsize=24:fontcolor=white@0.7:x={x}:y={y}"
            )

        # Subtitle
        if sync_subtitle and srt_path and os.path.exists(srt_path):
            # Escape path cho FFmpeg
            srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
            video_filters.append(f"subtitles='{srt_escaped}'")

        if progress_callback:
            progress_callback(30)

        # Build FFmpeg command
        filter_str = ",".join(video_filters) if video_filters else None

        cmd = ['ffmpeg', '-y', '-i', video_path]
        cmd.extend(audio_inputs)

        if filter_str:
            cmd.extend(['-vf', filter_str])

        # Map video va audio
        cmd.extend([
            '-map', '0:v:0',  # Video tu input 0
            '-map', '1:a:0',  # Audio tu input 1 (TTS)
        ])

        # Mix audio goc neu can
        if mix_original:
            cmd = ['ffmpeg', '-y', '-i', video_path, '-i', audio_path]
            if filter_str:
                cmd.extend(['-vf', filter_str])
            cmd.extend([
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[aout]',
                '-map', '0:v:0',
                '-map', '[aout]',
            ])

        # Output settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            output_path
        ])

        if progress_callback:
            progress_callback(50)

        # Run FFmpeg
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

            print(f"[VideoMerger] Xuat thanh cong: {output_path}")
            return output_path

        except Exception as e:
            raise Exception(f"Loi ghep video: {str(e)}")

    def get_video_duration(self, video_path: str) -> float:
        """Lay thoi luong video (giay)"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.strip())
        except:
            return 0.0

    def get_video_info(self, video_path: str) -> dict:
        """Lay thong tin video"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                video_path
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            import json
            data = json.loads(result.stdout)

            info = {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "size": int(data.get("format", {}).get("size", 0)),
            }

            # Tim video stream
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["width"] = stream.get("width", 0)
                    info["height"] = stream.get("height", 0)
                    info["fps"] = eval(stream.get("r_frame_rate", "0/1"))
                    break

            return info

        except Exception as e:
            print(f"[VideoMerger] Loi lay thong tin video: {e}")
            return {}
