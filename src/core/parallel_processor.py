"""
Parallel Processor for DouyinVoice Pro
Implements multi-threading and parallel processing for faster performance
"""
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, List, Any, Optional, Dict
from pathlib import Path
import time


@dataclass
class Task:
    """Represents a task to be executed in parallel"""
    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    priority: int = 0

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class ParallelProcessor:
    """Handles parallel execution of tasks using thread pools"""

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel processor

        Args:
            max_workers: Maximum number of worker threads (default: CPU cores * 2)
        """
        import multiprocessing
        if max_workers is None:
            max_workers = multiprocessing.cpu_count() * 2
        self.max_workers = max_workers
        self.progress_callback = None
        self.cancel_flag = threading.Event()

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self.progress_callback = callback

    def cancel(self):
        """Signal cancellation of all tasks"""
        self.cancel_flag.set()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested"""
        return self.cancel_flag.is_set()

    def run_parallel(self, tasks: List[Task], use_threads: bool = True) -> Dict[str, Any]:
        """
        Execute multiple tasks in parallel

        Args:
            tasks: List of Task objects to execute
            use_threads: Use ThreadPoolExecutor (True) or ProcessPoolExecutor (False)

        Returns:
            Dictionary mapping task IDs to results
        """
        results = {}
        self.cancel_flag.clear()

        # Sort tasks by priority (higher priority first)
        tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(task.func, *task.args, **task.kwargs): task
                for task in tasks
            }

            # Process completed tasks
            completed = 0
            total = len(tasks)

            for future in as_completed(future_to_task):
                if self.is_cancelled():
                    # Cancel remaining tasks
                    for f in future_to_task:
                        f.cancel()
                    break

                task = future_to_task[future]
                try:
                    result = future.result()
                    results[task.id] = result
                    completed += 1

                    if self.progress_callback:
                        self.progress_callback(completed, total, task.id, result)

                except Exception as e:
                    results[task.id] = {"error": str(e)}
                    if self.progress_callback:
                        self.progress_callback(completed, total, task.id, None, error=str(e))

        return results

    def download_parallel(self, urls: List[str], output_dir: str) -> List[str]:
        """
        Download multiple files in parallel

        Args:
            urls: List of URLs to download
            output_dir: Directory to save downloaded files

        Returns:
            List of paths to downloaded files
        """
        os.makedirs(output_dir, exist_ok=True)

        def download_file(url: str, index: int) -> str:
            """Download single file"""
            import urllib.request
            filename = os.path.join(output_dir, f"download_{index}.mp4")
            urllib.request.urlretrieve(url, filename)
            return filename

        tasks = [
            Task(
                id=f"download_{i}",
                func=download_file,
                args=(url, i)
            )
            for i, url in enumerate(urls)
        ]

        results = self.run_parallel(tasks)
        return [results[task.id] for task in tasks if task.id in results]

    def process_audio_chunks_parallel(
        self,
        chunks: List[str],
        process_func: Callable,
        **kwargs
    ) -> List[Any]:
        """
        Process multiple audio chunks in parallel (for STT)

        Args:
            chunks: List of audio chunk file paths
            process_func: Function to process each chunk
            **kwargs: Additional arguments for process_func

        Returns:
            List of results in order
        """
        tasks = [
            Task(
                id=f"chunk_{i}",
                func=process_func,
                args=(chunk,),
                kwargs=kwargs
            )
            for i, chunk in enumerate(chunks)
        ]

        results = self.run_parallel(tasks)

        # Return results in original order
        return [results[f"chunk_{i}"] for i in range(len(chunks))]

    def generate_tts_parallel(
        self,
        segments: List[str],
        tts_func: Callable,
        voice: str,
        **kwargs
    ) -> List[str]:
        """
        Generate TTS for multiple text segments in parallel

        Args:
            segments: List of text segments
            tts_func: Function to generate TTS
            voice: Voice to use
            **kwargs: Additional arguments for tts_func

        Returns:
            List of audio file paths in order
        """
        tasks = [
            Task(
                id=f"segment_{i}",
                func=tts_func,
                args=(segment, voice),
                kwargs=kwargs
            )
            for i, segment in enumerate(segments)
        ]

        results = self.run_parallel(tasks)

        # Return audio paths in original order
        return [results[f"segment_{i}"] for i in range(len(segments))]


class ChunkedProcessor:
    """Handles splitting and merging of audio/text for parallel processing"""

    def __init__(self):
        self.temp_dir = "temp/chunks"
        os.makedirs(self.temp_dir, exist_ok=True)

    def split_audio_for_stt(
        self,
        audio_path: str,
        chunk_duration: int = 30,
        overlap: float = 1.0
    ) -> List[str]:
        """
        Split audio into chunks for parallel STT processing
        FIXED: No gaps, proper overlap, captures EVERYTHING from start to end

        Args:
            audio_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds
            overlap: Overlap between chunks in seconds (prevents word cutting)

        Returns:
            List of chunk file paths
        """
        # Get audio duration
        cmd_duration = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(cmd_duration, capture_output=True, text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        total_duration = float(result.stdout.strip())

        print(f"[ChunkedProcessor] Total audio duration: {total_duration:.2f}s")

        chunks = []
        chunk_index = 0
        current_position = 0.0  # Track actual position in audio

        # Calculate effective step (chunk duration minus overlap)
        effective_step = chunk_duration - overlap

        while current_position < total_duration:
            # Start exactly at current position (no gaps!)
            chunk_start = current_position

            # Duration: go forward by chunk_duration, but don't exceed total
            remaining = total_duration - chunk_start
            this_chunk_duration = min(chunk_duration, remaining)

            chunk_path = os.path.join(self.temp_dir, f"chunk_{chunk_index:04d}.wav")

            cmd_extract = [
                'ffmpeg', '-y',
                '-ss', str(chunk_start),  # Start exactly here
                '-i', audio_path,
                '-t', str(this_chunk_duration),  # Take this much
                '-ar', '16000',  # 16kHz sample rate (optimal for STT)
                '-ac', '1',  # Mono
                '-c:a', 'pcm_s16le',  # WAV format
                chunk_path
            ]

            subprocess.run(cmd_extract, capture_output=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 100:
                chunks.append(chunk_path)
                print(f"[ChunkedProcessor] Chunk {chunk_index}: {chunk_start:.2f}s - {chunk_start + this_chunk_duration:.2f}s")
            else:
                print(f"[ChunkedProcessor] WARNING: Failed to create chunk {chunk_index} at {chunk_start:.2f}s")

            # Move forward by (chunk_duration - overlap) to create overlap
            current_position += effective_step
            chunk_index += 1

        print(f"[ChunkedProcessor] Created {len(chunks)} chunks")

        # VERIFY: Calculate actual coverage to ensure we didn't miss anything
        if chunks:
            # First chunk should start at 0
            first_chunk_start = 0.0
            # Last chunk calculation
            last_chunk_start = (len(chunks) - 1) * effective_step
            # Get duration of last chunk
            cmd_last = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                       '-of', 'default=noprint_wrappers=1:nokey=1', chunks[-1]]
            result_last = subprocess.run(cmd_last, capture_output=True, text=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            last_chunk_duration = float(result_last.stdout.strip()) if result_last.returncode == 0 else chunk_duration
            last_chunk_end = last_chunk_start + last_chunk_duration

            print(f"[ChunkedProcessor] Coverage: {first_chunk_start:.2f}s - {last_chunk_end:.2f}s")
            print(f"[ChunkedProcessor] Total audio duration: {total_duration:.2f}s")

            # Check for missing parts
            if first_chunk_start > 0.5:
                print(f"[ChunkedProcessor] WARNING: Missing beginning! First chunk starts at {first_chunk_start:.2f}s")

            if last_chunk_end < total_duration - 0.5:
                print(f"[ChunkedProcessor] WARNING: Missing ending! Last chunk ends at {last_chunk_end:.2f}s, audio ends at {total_duration:.2f}s")
                print(f"[ChunkedProcessor] Missing: {total_duration - last_chunk_end:.2f}s at the end!")

            coverage_percent = (last_chunk_end / total_duration * 100) if total_duration > 0 else 0
            print(f"[ChunkedProcessor] Coverage: {coverage_percent:.1f}% of audio")

        return chunks

    def split_text_for_tts(
        self,
        text: str,
        max_chars: int = 500
    ) -> List[str]:
        """
        Split text into segments for parallel TTS generation

        Args:
            text: Text to split
            max_chars: Maximum characters per segment

        Returns:
            List of text segments
        """
        # Sentence endings for Chinese and Vietnamese
        sentence_endings = ['。', '.', '!', '?', '！', '？', '\n']

        segments = []
        current_segment = ""

        for char in text:
            current_segment += char

            # Check if we should split here
            if char in sentence_endings and len(current_segment) >= max_chars * 0.7:
                segments.append(current_segment.strip())
                current_segment = ""
            elif len(current_segment) >= max_chars:
                # Force split if we exceed max_chars
                # Try to split at last space or punctuation
                split_pos = max_chars
                for i in range(len(current_segment) - 1, max(0, max_chars - 50), -1):
                    if current_segment[i] in [' ', ',', '，', ';', '；'] + sentence_endings:
                        split_pos = i + 1
                        break

                segments.append(current_segment[:split_pos].strip())
                current_segment = current_segment[split_pos:]

        # Add remaining text
        if current_segment.strip():
            segments.append(current_segment.strip())

        return segments

    def merge_audio_chunks(
        self,
        chunk_paths: List[str],
        output_path: str,
        add_silence: bool = True,
        silence_duration: float = 0.1
    ) -> bool:
        """
        Merge audio chunks into single file

        Args:
            chunk_paths: List of audio chunk paths
            output_path: Output file path
            add_silence: Add silence between chunks
            silence_duration: Duration of silence in seconds

        Returns:
            True if successful
        """
        if not chunk_paths:
            return False

        # Create concat file
        concat_file = os.path.join(self.temp_dir, "concat_list.txt")

        with open(concat_file, 'w') as f:
            for chunk_path in chunk_paths:
                f.write(f"file '{os.path.abspath(chunk_path)}'\n")
                if add_silence and chunk_path != chunk_paths[-1]:
                    # Add silence between chunks
                    silence_path = self._create_silence(silence_duration)
                    f.write(f"file '{os.path.abspath(silence_path)}'\n")

        # Merge using concat demuxer
        cmd_merge = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_path
        ]

        result = subprocess.run(cmd_merge, capture_output=True)

        # Cleanup
        if os.path.exists(concat_file):
            os.remove(concat_file)

        return result.returncode == 0

    def _create_silence(self, duration: float) -> str:
        """Create silent audio file"""
        silence_path = os.path.join(self.temp_dir, f"silence_{duration}.wav")

        if not os.path.exists(silence_path):
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'anullsrc=r=16000:cl=mono',
                '-t', str(duration),
                '-c:a', 'pcm_s16le',
                silence_path
            ]
            subprocess.run(cmd, capture_output=True)

        return silence_path

    def merge_results(self, results: List[Any]) -> Any:
        """
        Merge STT results maintaining order and removing boundary duplicates

        Args:
            results: List of transcription results

        Returns:
            Combined result with duplicates removed
        """
        # Simple concatenation for text results
        if all(isinstance(r, str) for r in results):
            merged = " ".join(results)
            return self._remove_boundary_duplicates(merged)

        # For dict results with 'text' key
        if all(isinstance(r, dict) and 'text' in r for r in results):
            merged = " ".join(r['text'] for r in results)
            return self._remove_boundary_duplicates(merged)

        return results

    def _remove_boundary_duplicates(self, text: str) -> str:
        """
        Remove duplicate words at chunk boundaries caused by overlap
        """
        words = text.split()
        if len(words) <= 1:
            return text

        cleaned = [words[0]]
        for i in range(1, len(words)):
            # Skip if same as previous word (case insensitive)
            if words[i].lower() != words[i-1].lower():
                cleaned.append(words[i])

        result = " ".join(cleaned)
        if len(words) != len(cleaned):
            print(f"[ChunkedProcessor] Removed {len(words) - len(cleaned)} duplicate words at boundaries")
        return result

    def cleanup_chunks(self):
        """Remove all temporary chunk files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)
