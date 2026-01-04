"""
Module Text-to-Speech su dung Edge-TTS
PHIEN BAN CAI TIEN: Ho tro text dai bang cach chia nho va ghep

CHUC NANG:
1. Tao giong doc AI tieng Viet
2. Ho tro nhieu giong (nam/nu)
3. Dieu chinh toc do doc
4. Ho tro text dai (tu dong chia nho va ghep)
5. Xuat file MP3
6. TAO SUBTITLE DONG BO: Tao file SRT voi timestamp chinh xac

THU VIEN: edge-tts, ffmpeg
"""
import asyncio
import uuid
import os
import subprocess
import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SubtitleSegment:
    """Mot doan subtitle voi timestamp"""
    index: int
    start_time: float  # Giay
    end_time: float    # Giay
    text: str

try:
    import edge_tts
except ImportError:
    edge_tts = None

# Gemini TTS
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class TextToSpeech:
    """Tao giong doc AI - Ho tro Edge-TTS, Gemini TTS, gTTS, VietTTS"""

    # === GIONG GEMINI TTS (Google AI - MIEN PHI, CHAT LUONG CAO) ===
    GEMINI_VOICES = {
        # Giong nu - tuoi, vui ve
        "gemini-Aoede": "Aoede (Nu - tuoi sang, vui ve)",
        "gemini-Kore": "Kore (Nu - ro rang, chuyen nghiep)",
        "gemini-Leda": "Leda (Nu - nhe nhang, diu dang)",
        "gemini-Zephyr": "Zephyr (Nu - tre trung, nang dong)",
        "gemini-Puck": "Puck (Nu - hoat bat, vui nhon)",
        "gemini-Charon": "Charon (Nu - nghiem tuc, tin cay)",
        # Giong nam
        "gemini-Fenrir": "Fenrir (Nam - soi noi, nhiet huyet)",
        "gemini-Orus": "Orus (Nam - manh me, quyet doan)",
        "gemini-Enceladus": "Enceladus (Nam - nhe nhang, tho)",
        "gemini-Iapetus": "Iapetus (Nam - chuyen nghiep, ro rang)",
        "gemini-Umbriel": "Umbriel (Nam - thoai mai, de chiu)",
        "gemini-Algenib": "Algenib (Nam - tram, quyen ru)",
        "gemini-Despina": "Despina (Nu - am ap, than thien)",
        "gemini-Sulafat": "Sulafat (Nu - mem mai, cam xuc)",
    }

    # === TAT CA GIONG TIENG VIET ===
    VOICES = {
        # === EDGE-TTS TIENG VIET (Microsoft - CHAT LUONG CAO NHAT) ===
        "vi-VN-HoaiMyNeural": "Nu Hoai My (Viet - tu nhien, cam xuc)",
        "vi-VN-NamMinhNeural": "Nam Minh (Viet - tram, truyen cam)",
    }

    # Gioi han ky tu cho moi chunk
    MAX_CHUNK_SIZE = 500

    def __init__(self, temp_dir: Path = None):
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

    def generate(self, text: str, voice: str = "vi-VN-HoaiMyNeural",
                 speed: float = 1.0, progress_callback=None) -> str:
        """
        Tao audio tu text - ho tro nhieu engine TTS

        Args:
            text: Noi dung can doc (khong gioi han do dai)
            voice: ID giong doc (edge-tts, gtts-vi, gemini-X)
            speed: Toc do (0.5 - 2.0)
            progress_callback: Callback(progress: int)

        Returns:
            Duong dan file audio MP3
        """
        if not text or not text.strip():
            raise ValueError("Text khong duoc de trong!")

        text = text.strip()
        speed = max(0.5, min(2.0, speed))

        print(f"[TTS] Text: {len(text)} ky tu, voice: {voice}, speed: {speed}x")

        # === Phan loai engine dua tren voice ID ===

        # 1. Gemini TTS (Google AI - MIEN PHI)
        if voice.startswith("gemini-"):
            return self._generate_gemini(text, voice, speed, progress_callback)

        # 2. gTTS (Google TTS)
        if voice.startswith("gtts"):
            return self._generate_gtts(text, speed, progress_callback)

        # 3. Edge-TTS (Mac dinh)
        if edge_tts is None:
            raise Exception("edge-tts chua duoc cai dat. Chay: pip install edge-tts")

        # Validate Edge-TTS voice
        if voice not in self.VOICES and not ('Neural' in voice):
            print(f"[TTS] Giong {voice} khong hop le, dung mac dinh vi-VN-HoaiMyNeural")
            voice = "vi-VN-HoaiMyNeural"

        # Chuyen speed thanh rate string cho edge-tts
        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        # Neu text ngan, tao truc tiep
        if len(text) <= self.MAX_CHUNK_SIZE:
            return self._generate_single(text, voice, rate, progress_callback)

        # Text dai - chia nho va ghep
        print(f"[TTS] Text dai, dang chia nho...")
        return self._generate_long_text(text, voice, rate, progress_callback)

    def _generate_gemini(self, text: str, voice: str, speed: float,
                         progress_callback=None, api_key: str = None) -> str:
        """
        Tao audio bang Gemini TTS (Google AI - MIEN PHI)
        """
        import wave

        if genai is None:
            raise Exception("google-genai chua cai dat. Chay: pip install google-genai")

        if progress_callback:
            progress_callback(5)

        # Lay API key tu environment neu khong truyen
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if not api_key:
            raise Exception("Chua co Gemini API key! Vui long nhap API key trong phan cai dat.")

        # Lay ten giong tu voice ID (gemini-Kore -> Kore)
        voice_name = voice.replace("gemini-", "")

        print(f"[Gemini TTS] Voice: {voice_name}, Text: {len(text)} ky tu")

        if progress_callback:
            progress_callback(10)

        try:
            # Khoi tao client voi API key
            client = genai.Client(api_key=api_key)

            if progress_callback:
                progress_callback(20)

            # Tao prompt voi huong dan toc do
            speed_instruction = ""
            if speed < 0.8:
                speed_instruction = "Read very slowly and clearly: "
            elif speed < 1.0:
                speed_instruction = "Read slowly: "
            elif speed > 1.3:
                speed_instruction = "Read quickly: "
            elif speed > 1.1:
                speed_instruction = "Read at a slightly faster pace: "

            full_prompt = f"{speed_instruction}{text}"

            print(f"[Gemini TTS] Dang goi API...")

            # Goi Gemini TTS API
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                )
            )

            if progress_callback:
                progress_callback(70)

            # Lay du lieu audio (PCM)
            audio_data = response.candidates[0].content.parts[0].inline_data.data

            # Luu file WAV
            wav_path = str(self.temp_dir / f"tts_gemini_{uuid.uuid4().hex[:8]}.wav")

            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)      # Mono
                wf.setsampwidth(2)      # 16-bit
                wf.setframerate(24000)  # 24kHz
                wf.writeframes(audio_data)

            if progress_callback:
                progress_callback(85)

            # Chuyen sang MP3
            mp3_path = str(self.temp_dir / f"tts_gemini_{uuid.uuid4().hex[:8]}.mp3")

            cmd = [
                'ffmpeg', '-y',
                '-i', wav_path,
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                mp3_path
            ]

            subprocess.run(
                cmd, capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Xoa file WAV tam
            try:
                os.remove(wav_path)
            except:
                pass

            if progress_callback:
                progress_callback(100)

            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                print(f"[Gemini TTS] Thanh cong: {mp3_path}")
                return mp3_path
            else:
                raise Exception("Gemini TTS khong tao duoc audio!")

        except Exception as e:
            error_msg = str(e)
            print(f"[Gemini TTS] Loi: {error_msg}")

            # Fallback sang Edge-TTS neu loi
            if "API key" not in error_msg:
                print("[Gemini TTS] Fallback sang Edge-TTS...")
                return self._generate_single(text, "vi-VN-HoaiMyNeural", "+0%", progress_callback)
            else:
                raise Exception(f"Gemini TTS loi: {error_msg}")

    def _generate_gtts(self, text: str, speed: float, progress_callback=None) -> str:
        """Tao audio bang Google TTS (gTTS)"""
        try:
            from gtts import gTTS
        except ImportError:
            raise Exception("gTTS chua cai dat. Chay: pip install gtts")

        if progress_callback:
            progress_callback(10)

        output_path = str(self.temp_dir / f"tts_gtts_{uuid.uuid4().hex[:8]}.mp3")

        print("[TTS] Dang tao audio bang gTTS...")

        slow = speed < 0.9

        tts = gTTS(text=text, lang='vi', slow=slow)
        tts.save(output_path)

        if progress_callback:
            progress_callback(100)

        print(f"[TTS] gTTS hoan thanh: {output_path}")
        return output_path

    def _generate_single(self, text: str, voice: str, rate: str,
                         progress_callback=None) -> str:
        """Tao audio cho text ngan"""
        output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        output_path = str(self.temp_dir / output_filename)

        if progress_callback:
            progress_callback(10)

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self._run_async_tts(text, voice, rate, output_path)

                if not os.path.exists(output_path):
                    raise Exception("Khong tao duoc file audio!")

                file_size = os.path.getsize(output_path)
                if file_size < 1000:
                    raise Exception("File audio qua nho!")

                if progress_callback:
                    progress_callback(100)

                print(f"[TTS] Tao xong: {file_size / 1024:.1f} KB")
                return output_path

            except Exception as e:
                if attempt < max_retries - 1:
                    import time
                    print(f"[TTS] Loi: {e}, thu lai lan {attempt + 2}...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Loi TTS sau {max_retries} lan: {str(e)}")

        raise Exception("Khong the tao audio!")

    def _generate_long_text(self, text: str, voice: str, rate: str,
                            progress_callback=None) -> str:
        """Tao audio cho text dai - XU LY SONG SONG"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time

        # Chia text thanh cac chunk
        chunks = self._split_text(text)
        print(f"[TTS] Da chia thanh {len(chunks)} doan - XU LY SONG SONG")

        # Tao danh sach output paths theo thu tu
        chunk_paths = []
        for i in range(len(chunks)):
            chunk_filename = f"tts_chunk_{i:03d}_{uuid.uuid4().hex[:4]}.mp3"
            chunk_paths.append(str(self.temp_dir / chunk_filename))

        # Ham xu ly 1 chunk
        def process_chunk(args):
            idx, chunk_text, output_path = args
            for attempt in range(3):
                try:
                    self._run_async_tts(chunk_text, voice, rate, output_path)
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                        return (idx, output_path, True)
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.5)
            return (idx, output_path, False)

        # Xu ly song song
        completed = 0
        results = {}
        temp_files = []

        try:
            with ThreadPoolExecutor(max_workers=12) as executor:
                futures = {
                    executor.submit(process_chunk, (i, chunks[i], chunk_paths[i])): i
                    for i in range(len(chunks))
                }

                for future in as_completed(futures):
                    idx, path, success = future.result()
                    results[idx] = (path, success)
                    completed += 1

                    if progress_callback:
                        progress = int((completed / len(chunks)) * 80) + 10
                        progress_callback(progress)

            # Sap xep lai theo thu tu
            for i in range(len(chunks)):
                if i in results and results[i][1]:
                    temp_files.append(results[i][0])

            if not temp_files:
                raise Exception("Khong tao duoc bat ky chunk audio nao!")

            # Ghep tat ca chunk
            if progress_callback:
                progress_callback(90)

            output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            output_path = str(self.temp_dir / output_filename)

            print(f"[TTS] Dang ghep {len(temp_files)} file audio...")
            self._concat_audio_files(temp_files, output_path)

            if progress_callback:
                progress_callback(100)

            return output_path

        finally:
            # Xoa file chunk tam
            for path in chunk_paths:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except:
                    pass

    def _split_text(self, text: str) -> List[str]:
        """Chia text thanh cac chunk nho"""
        chunks = []
        current_chunk = ""

        sentences = self._split_sentences(text)

        for sentence in sentences:
            if len(sentence) > self.MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                sub_chunks = self._split_long_sentence(sentence)
                chunks.extend(sub_chunks)
                continue

            if len(current_chunk) + len(sentence) > self.MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    def _split_sentences(self, text: str) -> List[str]:
        """Chia text thanh cac cau"""
        pattern = r'([.!?。！？\n])'
        parts = re.split(pattern, text)

        sentences = []
        i = 0
        while i < len(parts):
            sentence = parts[i]
            if i + 1 < len(parts) and re.match(pattern, parts[i + 1]):
                sentence += parts[i + 1]
                i += 1
            if sentence.strip():
                sentences.append(sentence)
            i += 1

        return sentences if sentences else [text]

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Chia cau dai thanh cac phan nho"""
        chunks = []

        sub_pattern = r'([,，;；:])'
        parts = re.split(sub_pattern, sentence)

        current = ""
        for part in parts:
            if len(current) + len(part) > self.MAX_CHUNK_SIZE:
                if current:
                    chunks.append(current)
                current = part
            else:
                current += part

        if current:
            chunks.append(current)

        # Cat cung neu van con qua dai
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.MAX_CHUNK_SIZE:
                for i in range(0, len(chunk), self.MAX_CHUNK_SIZE):
                    final_chunks.append(chunk[i:i + self.MAX_CHUNK_SIZE])
            else:
                final_chunks.append(chunk)

        return final_chunks if final_chunks else [sentence]

    def _concat_audio_files(self, input_files: List[str], output_path: str):
        """Ghep nhieu file audio thanh 1 file bang FFmpeg"""
        if len(input_files) == 1:
            import shutil
            shutil.copy(input_files[0], output_path)
            return

        # Tao file list cho FFmpeg concat
        list_filename = f"concat_list_{uuid.uuid4().hex[:8]}.txt"
        list_path = str(self.temp_dir / list_filename)

        try:
            with open(list_path, 'w', encoding='utf-8') as f:
                for file_path in input_files:
                    escaped_path = file_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_path,
                '-c', 'copy',
                output_path
            ]

            subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

        finally:
            try:
                if os.path.exists(list_path):
                    os.unlink(list_path)
            except:
                pass

    def _run_async_tts(self, text: str, voice: str, rate: str, output_path: str):
        """Chay async TTS"""
        import concurrent.futures

        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_in_new_loop, text, voice, rate, output_path)
                future.result(timeout=60)
        except RuntimeError:
            asyncio.run(self._generate_async(text, voice, rate, output_path))

    def _run_in_new_loop(self, text: str, voice: str, rate: str, output_path: str):
        """Chay trong event loop moi"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._generate_async(text, voice, rate, output_path))
        finally:
            loop.close()

    async def _generate_async(self, text: str, voice: str, rate: str, output_path: str):
        """Async function tao audio"""
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)

    def get_available_voices(self) -> dict:
        """Lay danh sach giong"""
        return self.VOICES.copy()

    def _get_audio_duration(self, audio_path: str) -> float:
        """Lay thoi luong audio file bang FFprobe"""
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
