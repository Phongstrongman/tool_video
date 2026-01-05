"""
Module ghep video voi audio moi
Toi uu voi multi-threading va hardware acceleration
Ho tro: anti-copyright effects, watermark, intro
"""
import os
import subprocess
import uuid
import json
from pathlib import Path


class VideoMerger:
    """Ghep video voi audio moi va cac hieu ung - toi uu hieu suat"""

    def __init__(self, output_dir: Path = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

        # So luong CPU threads
        self.num_threads = min(os.cpu_count() or 4, 8)

        # Kiem tra GPU acceleration
        self.hw_accel = self._detect_hw_acceleration()

    def _detect_hw_acceleration(self) -> str:
        """Phat hien GPU acceleration kha dung - TEST THAT THU"""
        # Test NVIDIA NVENC
        if self._test_encoder('h264_nvenc'):
            print("[VideoMerger] Detected: NVIDIA NVENC (GPU)")
            return 'nvenc'

        # Test Intel QuickSync
        if self._test_encoder('h264_qsv'):
            print("[VideoMerger] Detected: Intel QuickSync (GPU)")
            return 'qsv'

        # Test AMD AMF
        if self._test_encoder('h264_amf'):
            print("[VideoMerger] Detected: AMD AMF (GPU)")
            return 'amf'

        print("[VideoMerger] No GPU acceleration found, using CPU")
        return 'cpu'

    def _test_encoder(self, encoder: str) -> bool:
        """Test xem encoder co hoat dong khong (khong chi check list)"""
        try:
            # Tao test video 1 frame de test encoder
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'color=black:s=320x240:d=0.1',
                '-c:v', encoder, '-f', 'null', '-'
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            # Neu return code = 0 thi encoder hoat dong
            return result.returncode == 0
        except:
            return False

    def merge(self, video_path: str, audio_path: str, output_name: str,
              mix_original: bool = False, anti_copyright: dict = None,
              watermark: dict = None, intro: dict = None,
              sync_subtitle: bool = False, srt_path: str = None,
              progress_callback=None, status_callback=None, output_folder: str = None) -> str:
        """
        Ghep video voi audio moi - toi uu hieu suat

        Args:
            video_path: Duong dan video goc
            audio_path: Duong dan audio moi (TTS)
            output_name: Ten file output
            mix_original: Mix voi audio goc
            anti_copyright: Dict cac hieu ung chong ban quyen
                - flip: Lat ngang video
                - zoom: Phong to 5%
                - effect: Dieu chinh mau sac
                - remove_text: Cat phan text (10% duoi)
                - remove_watermark: Lam mo watermark (crop)
                - remove_metadata: Xoa metadata ban quyen
            watermark: Dict cai dat watermark
            intro: Dict cai dat intro
            sync_subtitle: Hien thi subtitle tren video
            srt_path: Duong dan file SRT
            progress_callback: Callback(progress: int)
            status_callback: Callback(status: str)
            output_folder: Thu muc luu output (optional)

        Returns:
            Duong dan file output
        """
        # Normalize paths for Windows
        video_path = os.path.normpath(video_path)
        audio_path = os.path.normpath(audio_path)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video khong ton tai: {video_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio khong ton tai: {audio_path}")

        # Lay duration de track progress
        duration = self.get_video_duration(video_path)

        # Tao output path
        output_filename = f"{output_name}.mp4"
        if output_folder:
            output_dir = Path(output_folder)
            output_dir.mkdir(exist_ok=True)
        else:
            output_dir = self.output_dir

        output_path = str(output_dir / output_filename)

        # Dam bao ten file khong trung
        counter = 1
        while os.path.exists(output_path):
            output_filename = f"{output_name}_{counter}.mp4"
            output_path = str(output_dir / output_filename)
            counter += 1

        if progress_callback:
            progress_callback(5)
        if status_callback:
            status_callback("Dang chuan bi...")

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
                # Cat 10% duoi cung (subtitle tieng Trung)
                video_filters.append("crop=iw:ih*0.9:0:0")
            if anti_copyright.get("remove_watermark"):
                # Cat 5% tren + 5% duoi (watermark thuong o goc tren hoac duoi)
                video_filters.append("crop=iw:ih*0.9:0:ih*0.05")

        # Watermark
        if watermark and watermark.get("enabled") and watermark.get("text"):
            wm_text = watermark["text"]
            wm_pos = watermark.get("position", "Tren-Phai")

            if wm_pos == "Tren-Phai":
                x, y = "w-tw-20", "20"
            elif wm_pos == "Tren-Trai":
                x, y = "20", "20"
            elif wm_pos == "Duoi-Phai":
                x, y = "w-tw-20", "h-th-20"
            else:
                x, y = "20", "h-th-20"

            wm_text_escaped = wm_text.replace("'", "\\'").replace(":", "\\:")
            video_filters.append(
                f"drawtext=text='{wm_text_escaped}':fontsize=24:fontcolor=white@0.7:x={x}:y={y}"
            )

        # Subtitle
        if sync_subtitle and srt_path and os.path.exists(srt_path):
            srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
            video_filters.append(f"subtitles='{srt_escaped}'")

        if progress_callback:
            progress_callback(10)
        if status_callback:
            status_callback("Dang xu ly video...")

        # Build FFmpeg command - SIMPLIFIED AND ROBUST
        filter_str = ",".join(video_filters) if video_filters else None

        # Get audio duration to check if we need to loop
        audio_duration = self._get_audio_duration(audio_path)

        print(f"[VideoMerger] Video duration: {duration:.1f}s, Audio duration: {audio_duration:.1f}s")

        # SIMPLE APPROACH: Build command based on whether we need filters/mixing
        if mix_original:
            # Mix original audio with new audio
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-stream_loop', '-1',  # Loop audio indefinitely
                '-i', audio_path
            ]

            if filter_str:
                # Video filter + audio mix
                cmd.extend([
                    '-filter_complex', f'[0:v]{filter_str}[v];[0:a][1:a]amix=inputs=2:duration=longest[a]',
                    '-map', '[v]',
                    '-map', '[a]'
                ])
            else:
                # Just audio mix, no video filter
                cmd.extend([
                    '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[a]',
                    '-map', '0:v:0',
                    '-map', '[a]'
                ])

        else:
            # Replace audio (no mixing) - KHONG LOOP, chi phat 1 lan
            # Neu audio ngan hon video: phan con lai se im lang
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path
            ]

            if filter_str:
                # Co video filter: can dung filter_complex de pad audio
                cmd.extend([
                    '-filter_complex',
                    f'[0:v]{filter_str}[vout];[1:a]apad=whole_dur={duration}[aout]',
                    '-map', '[vout]',
                    '-map', '[aout]'
                ])
            else:
                # Khong co video filter: pad audio voi silence
                cmd.extend([
                    '-filter_complex',
                    f'[1:a]apad=whole_dur={duration}[aout]',
                    '-map', '0:v:0',
                    '-map', '[aout]'
                ])

        # Output settings - TOI UU DUNG LUONG NHO + CHAT LUONG TOT
        # CRF 28 = chat luong tot, file nho hon 50% so voi CRF 23
        if self.hw_accel == 'nvenc':
            # NVIDIA GPU - CQ 28 tuong duong CRF 28
            cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'p4',
                '-rc', 'vbr',
                '-cq', '28',      # Tang tu 23 len 28 (file nho hon 50%)
                '-b:v', '2M',     # Giam tu 5M xuong 2M
                '-maxrate', '3M',
                '-bufsize', '4M',
            ])
            print("[VideoMerger] Using NVIDIA NVENC (GPU) - Optimized size")
        elif self.hw_accel == 'qsv':
            # Intel QuickSync
            cmd.extend([
                '-c:v', 'h264_qsv',
                '-preset', 'veryfast',
                '-global_quality', '28',  # Tang tu 23 len 28
            ])
            print("[VideoMerger] Using Intel QuickSync (GPU) - Optimized size")
        elif self.hw_accel == 'amf':
            # AMD GPU
            cmd.extend([
                '-c:v', 'h264_amf',
                '-quality', 'speed',
                '-rc', 'vbr_peak',
                '-qp_i', '28',    # Tang tu 23 len 28
            ])
            print("[VideoMerger] Using AMD AMF (GPU) - Optimized size")
        else:
            # CPU fallback
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '28',     # Tang tu 23 len 28 (file nho hon 50%)
            ])
            print("[VideoMerger] Using CPU encoding - Optimized size")

        # Audio settings - CHUNG CHO TAT CA
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-t', str(duration),  # GIU NGUYEN DO DAI VIDEO GOC (KHONG DUNG -shortest)
            '-movflags', '+faststart'
        ])

        # Remove metadata if requested (anti-copyright)
        if anti_copyright and anti_copyright.get("remove_metadata"):
            cmd.extend(['-map_metadata', '-1'])  # Xoa tat ca metadata

        cmd.append(output_path)

        # Run FFmpeg voi progress tracking
        try:
            import logging
            logging.basicConfig(level=logging.DEBUG)
            logger = logging.getLogger(__name__)

            logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
            logger.debug(f"Video path: {video_path} (exists: {os.path.exists(video_path)})")
            logger.debug(f"Audio path: {audio_path} (exists: {os.path.exists(audio_path)})")
            logger.debug(f"Output path: {output_path}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Collect stderr output in real-time
            stderr_output = []

            # Read stderr in separate thread to avoid blocking
            import threading
            def read_stderr():
                for line in process.stderr:
                    stderr_output.append(line)
                    logger.debug(f"FFmpeg: {line.strip()}")

            stderr_thread = threading.Thread(target=read_stderr)
            stderr_thread.start()

            # Read stdout for progress
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break

                if 'out_time_ms=' in line:
                    try:
                        time_ms = int(line.split('=')[1].strip())
                        current_time = time_ms / 1000000
                        if duration > 0 and progress_callback:
                            progress = min(95, int((current_time / duration) * 85) + 10)
                            progress_callback(progress)
                    except:
                        pass

            # Wait for stderr thread to finish
            stderr_thread.join(timeout=5)

            return_code = process.wait()

            if return_code != 0:
                error_msg = "".join(stderr_output) if stderr_output else "Unknown FFmpeg error"
                logger.error(f"FFmpeg failed with code {return_code}")
                logger.error(f"FFmpeg stderr:\n{error_msg}")
                raise Exception(f"FFmpeg loi (code {return_code}). Chi tiet:\n{error_msg[:500]}")

            if not os.path.exists(output_path):
                error_msg = "".join(stderr_output) if stderr_output else "File output khong duoc tao"
                logger.error(f"Output file not created: {error_msg}")
                raise Exception(f"FFmpeg khong tao duoc file output:\n{error_msg[:500]}")

            file_size = os.path.getsize(output_path)
            if file_size < 1000:
                logger.error(f"Output file too small: {file_size} bytes")
                raise Exception(f"File output qua nho ({file_size} bytes), co the FFmpeg loi")

            if progress_callback:
                progress_callback(100)
            if status_callback:
                status_callback("Xuat video hoan tat!")

            logger.info(f"[VideoMerger] Xuat thanh cong: {output_path} ({file_size / 1024 / 1024:.2f} MB)")
            print(f"[VideoMerger] Xuat thanh cong: {output_path}")
            return output_path

        except subprocess.SubprocessError as e:
            import traceback
            error_details = f"Loi subprocess: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] VideoMerger subprocess error:\n{error_details}")
            raise Exception(error_details)
        except Exception as e:
            import traceback
            error_details = f"Loi ghep video: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] VideoMerger error:\n{error_details}")
            raise Exception(error_details)

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

    def _get_audio_duration(self, audio_path: str) -> float:
        """Lay thoi luong audio (giay)"""
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

            data = json.loads(result.stdout)

            info = {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "size": int(data.get("format", {}).get("size", 0)),
            }

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
