"""
Intro Generator for DouyinVoice Pro
Creates intro video from source video clips WITH TTS AUDIO
"""
import subprocess
import os
from pathlib import Path


class IntroGenerator:
    def __init__(self, tts_instance=None):
        self.words_per_second = 3.5  # 3-4 words per second (average 3.5)
        self.tts = tts_instance  # TextToSpeech instance for generating intro audio

    def calculate_intro_duration(self, text: str) -> float:
        """
        Calculate intro duration based on text length
        Uses 3-4 words per second (average 3.5 words/sec)
        """
        # Count words (split by whitespace)
        words = text.strip().split()
        word_count = len(words)

        # Calculate duration: words / words_per_second
        duration = word_count / self.words_per_second

        # Min 3s, Max 30s
        return max(3.0, min(duration, 30.0))

    def get_video_duration(self, video_path: str) -> float:
        """Get video duration using FFmpeg"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())

    def extract_clip(self, video_path: str, start: float, duration: float, output_path: str, speed: float = 1.2) -> bool:
        """
        Extract a clip from video with speed adjustment and audio normalization

        Args:
            video_path: Source video
            start: Start time in seconds
            duration: Duration in seconds
            output_path: Output path
            speed: Speed multiplier (1.2 = 20% faster)

        Returns:
            True if successful
        """
        # Normalize paths
        video_path = os.path.normpath(video_path)
        output_path = os.path.normpath(output_path)

        # For 1.2x speed:
        # - Video: setpts=0.833*PTS (1/1.2 = 0.833)
        # - Audio: atempo=1.2

        setpts_value = 1.0 / speed  # 1/1.2 = 0.833

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            # Apply speed filters: video + audio synced
            '-filter_complex',
            f'[0:v]setpts={setpts_value}*PTS[v];[0:a]atempo={speed}[a]',
            '-map', '[v]',
            '-map', '[a]',
            # Normalize audio format: AAC, 44100Hz, stereo, 128k
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-ar', '44100',  # Sample rate: 44100Hz
            '-ac', '2',      # Channels: stereo (2)
            '-b:a', '128k',  # Bitrate: 128k
            '-preset', 'ultrafast',  # TOI UU TOC DO (ultrafast nhanh nhat)
            '-pix_fmt', 'yuv420p',  # Pixel format
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            print(f"[ERROR] extract_clip failed: {result.stderr.decode()}")

        return result.returncode == 0

    def generate_intro(self, video_path: str, text: str, output_path: str, temp_dir: str = "temp",
                      voice: str = "vi-VN-HoaiMyNeural", speed: float = 1.0, progress_callback=None) -> bool:
        """
        Generate intro video from 3 clips (start, middle, end) WITH TTS AUDIO

        Args:
            video_path: Source video path
            text: Text for TTS audio (also determines intro length)
            output_path: Output intro video path
            temp_dir: Temp directory for intermediate files
            voice: TTS voice (default: vi-VN-HoaiMyNeural)
            speed: TTS speed (default: 1.0)
            progress_callback: Progress callback function
        """
        # Normalize paths
        video_path = os.path.normpath(video_path)
        output_path = os.path.normpath(output_path)
        temp_dir = os.path.normpath(temp_dir)

        os.makedirs(temp_dir, exist_ok=True)

        # === STEP 1: Generate TTS audio from text ===
        print(f"[Intro] Tao TTS audio cho intro text...")
        if progress_callback:
            progress_callback(10)

        if self.tts is None:
            # Import TextToSpeech if not provided
            from src.core.text_to_speech import TextToSpeech
            self.tts = TextToSpeech(temp_dir=Path(temp_dir))

        try:
            tts_audio_path = self.tts.generate(text, voice=voice, speed=speed)
            print(f"[Intro] TTS audio created: {tts_audio_path}")
        except Exception as e:
            print(f"[Intro ERROR] Failed to generate TTS audio: {e}")
            return False

        if progress_callback:
            progress_callback(30)

        # Get TTS audio duration
        tts_duration = self._get_audio_duration(tts_audio_path)
        if tts_duration <= 0:
            print(f"[Intro ERROR] Invalid TTS audio duration!")
            return False

        print(f"[Intro] TTS audio duration: {tts_duration:.2f}s")

        # === STEP 2: Create intro video (silent, matching TTS duration) ===
        if progress_callback:
            progress_callback(40)

        video_duration = self.get_video_duration(video_path)
        clip_duration = tts_duration / 3

        # Calculate clip positions
        clip1_start = 0  # Start of video
        clip2_start = (video_duration / 2) - (clip_duration / 2)  # Middle
        clip3_start = video_duration - clip_duration  # End

        # Extract 3 clips WITHOUT audio (silent)
        clip1_path = os.path.join(temp_dir, "intro_clip1_silent.mp4")
        clip2_path = os.path.join(temp_dir, "intro_clip2_silent.mp4")
        clip3_path = os.path.join(temp_dir, "intro_clip3_silent.mp4")

        self._extract_clip_silent(video_path, clip1_start, clip_duration, clip1_path)
        self._extract_clip_silent(video_path, clip2_start, clip_duration, clip2_path)
        self._extract_clip_silent(video_path, clip3_start, clip_duration, clip3_path)

        if progress_callback:
            progress_callback(60)

        # Concatenate clips (silent video)
        concat_list = os.path.join(temp_dir, "intro_concat.txt")
        with open(concat_list, 'w') as f:
            f.write(f"file '{os.path.abspath(clip1_path)}'\n")
            f.write(f"file '{os.path.abspath(clip2_path)}'\n")
            f.write(f"file '{os.path.abspath(clip3_path)}'\n")

        intro_silent_path = os.path.join(temp_dir, "intro_silent.mp4")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list,
            '-c', 'copy',
            intro_silent_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            print(f"[Intro ERROR] Concat failed: {result.stderr.decode()}")
            return False

        if progress_callback:
            progress_callback(80)

        # === STEP 3: Merge TTS audio with silent intro video ===
        print(f"[Intro] Merging TTS audio with intro video...")
        success = self._merge_audio_with_video(intro_silent_path, tts_audio_path, output_path)

        if progress_callback:
            progress_callback(100)

        # Cleanup temp files
        for f in [clip1_path, clip2_path, clip3_path, concat_list, intro_silent_path, tts_audio_path]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

        if success:
            print(f"[Intro] Intro video created successfully: {output_path}")
        else:
            print(f"[Intro ERROR] Failed to create intro video!")

        return success

    def _extract_clip_silent(self, video_path: str, start: float, duration: float, output_path: str, speed: float = 1.2) -> bool:
        """
        Extract a clip from video WITHOUT audio (silent) with speed adjustment

        Args:
            video_path: Source video
            start: Start time in seconds
            duration: Duration in seconds
            output_path: Output path
            speed: Speed multiplier (1.2 = 20% faster)

        Returns:
            True if successful
        """
        # Normalize paths
        video_path = os.path.normpath(video_path)
        output_path = os.path.normpath(output_path)

        setpts_value = 1.0 / speed  # 1/1.2 = 0.833

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            # Apply speed filter to video only (NO AUDIO)
            '-vf', f'setpts={setpts_value}*PTS',
            '-an',  # Remove audio
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # TOI UU TOC DO
            '-pix_fmt', 'yuv420p',
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            print(f"[ERROR] extract_clip_silent failed: {result.stderr.decode()}")

        return result.returncode == 0

    def _merge_audio_with_video(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """
        Merge audio with video (replace video's audio with new audio)

        Args:
            video_path: Video file (can be silent or with audio)
            audio_path: Audio file to add
            output_path: Output video with new audio

        Returns:
            True if successful
        """
        video_path = os.path.normpath(video_path)
        audio_path = os.path.normpath(audio_path)
        output_path = os.path.normpath(output_path)

        # Get video duration and audio duration
        video_duration = self.get_video_duration(video_path)
        audio_duration = self._get_audio_duration(audio_path)

        print(f"[Merge] Video: {video_duration:.2f}s, Audio: {audio_duration:.2f}s")

        # QUAN TRONG: GIU NGUYEN DO DAI VIDEO GOC, KHONG CAT NGAN!
        # AUDIO CHI PHAT 1 LAN (KHONG LAP), phan con lai im lang
        if audio_duration < video_duration:
            # Audio ngan hon video: Pad silence vao cuoi
            print(f"[Merge] Audio ngan hon video, pad silence {video_duration - audio_duration:.2f}s")
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-filter_complex', f'[1:a]apad=whole_dur={video_duration}s[a]',  # Pad silence
                '-map', '0:v:0',  # Video from video_path
                '-map', '[a]',     # Padded audio
                '-c:v', 'copy',    # Copy video (khong encode)
                '-c:a', 'aac',
                '-b:a', '192k',
                '-t', str(video_duration),
                output_path
            ]
        else:
            # Audio dai hon hoac bang video: Cat audio theo video
            print(f"[Merge] Audio dai hon video, cat audio")
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-t', str(video_duration),
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',  # Cut theo video
                output_path
            ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            print(f"[ERROR] merge_audio_with_video failed: {result.stderr.decode()}")

        return result.returncode == 0

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using FFprobe"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(result.stdout.strip())
        except:
            return 0.0

    def merge_intro_with_main(self, intro_path: str, main_video_path: str, output_path: str, temp_dir: str = "temp") -> bool:
        """
        Merge intro with main video WITHOUT audio issues
        Normalizes BOTH videos to same format before concat
        """
        # Normalize paths
        intro_path = os.path.normpath(intro_path)
        main_video_path = os.path.normpath(main_video_path)
        output_path = os.path.normpath(output_path)
        temp_dir = os.path.normpath(temp_dir)

        os.makedirs(temp_dir, exist_ok=True)

        # Get main video properties
        cmd_probe = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate',
            '-of', 'csv=p=0',
            main_video_path
        ]
        result = subprocess.run(cmd_probe, capture_output=True, text=True)
        width, height, fps = result.stdout.strip().split(',')

        # CRITICAL: Normalize BOTH intro and main video to same format
        # This prevents audio desync/corruption when concatenating
        intro_normalized = os.path.join(temp_dir, "intro_normalized.mp4")
        main_normalized = os.path.join(temp_dir, "main_normalized.mp4")

        # Normalize intro: AAC 44100Hz stereo 128k, match resolution/fps
        # TOI UU: Dung ultrafast de tang toc do normalize
        cmd_norm_intro = [
            'ffmpeg', '-y',
            '-i', intro_path,
            '-vf', f'scale={width}:{height},fps={fps}',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-ar', '44100',     # Sample rate: 44100Hz
            '-ac', '2',         # Channels: stereo
            '-b:a', '128k',     # Bitrate: 128k
            '-preset', 'ultrafast',  # TOI UU TOC DO (nhanh hon 2-3 lan)
            '-pix_fmt', 'yuv420p',
            intro_normalized
        ]

        # Normalize main video: AAC 44100Hz stereo 128k (same as intro)
        # TOI UU: Dung ultrafast de tang toc do normalize
        cmd_norm_main = [
            'ffmpeg', '-y',
            '-i', main_video_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-ar', '44100',     # Sample rate: 44100Hz
            '-ac', '2',         # Channels: stereo
            '-b:a', '128k',     # Bitrate: 128k
            '-preset', 'ultrafast',  # TOI UU TOC DO (nhanh hon 2-3 lan)
            '-pix_fmt', 'yuv420p',
            main_normalized
        ]

        # Run normalizations
        subprocess.run(
            cmd_norm_intro,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        subprocess.run(
            cmd_norm_main,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        # Create concat list with normalized files
        concat_list = os.path.join(temp_dir, "final_concat.txt")
        with open(concat_list, 'w') as f:
            f.write(f"file '{os.path.abspath(intro_normalized)}'\n")
            f.write(f"file '{os.path.abspath(main_normalized)}'\n")

        # Merge using concat demuxer with stream copy (fast, no quality loss)
        cmd_merge = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list,
            '-c', 'copy',  # Stream copy - both videos have same format now
            output_path
        ]
        result = subprocess.run(
            cmd_merge,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            print(f"[ERROR] merge failed: {result.stderr.decode()}")

        # Cleanup
        for f in [intro_normalized, main_normalized, concat_list]:
            if os.path.exists(f):
                os.remove(f)

        return result.returncode == 0
