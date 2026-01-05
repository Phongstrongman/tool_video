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
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from src.core.parallel_processor import ParallelProcessor, ChunkedProcessor, Task


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
    # Tang len 1500 de giong doc lien mach hon, it bi ngat quang
    MAX_CHUNK_SIZE = 1500

    # Map ten giong UI sang API format
    UI_TO_GEMINI_VOICE = {
        "Aoede (Nu - Sang)": "gemini-Aoede",
        "Charon (Nam - Tram)": "gemini-Charon",
        "Fenrir (Nam - Trung)": "gemini-Fenrir",
        "Kore (Nu - Tre)": "gemini-Kore",
        "Puck (Nam - Vui)": "gemini-Puck",
        "Zephyr (Nu - Nhe)": "gemini-Zephyr",
        "Orbit (Nam - Ro)": "gemini-Orus",
        "Lyra (Nu - Am)": "gemini-Leda",
        "Nova (Nu - Pro)": "gemini-Despina",
        "Solaris (Nam - Manh)": "gemini-Enceladus",
        "Echo (Nam - Vang)": "gemini-Umbriel",
        "Aurora (Nu - Trang)": "gemini-Sulafat",
        "Titan (Nam - Sau)": "gemini-Iapetus",
        "Luna (Nu - Diu)": "gemini-Algenib",
    }

    UI_TO_EDGE_VOICE = {
        "vi-VN-HoaiMyNeural (Nu)": "vi-VN-HoaiMyNeural",
        "vi-VN-NamMinhNeural (Nam)": "vi-VN-NamMinhNeural",
    }

    def __init__(self, temp_dir: Path = None):
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(__file__).parent.parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize parallel processing components
        self.parallel_processor = None
        self.chunked_processor = ChunkedProcessor()

    def _convert_voice(self, voice: str) -> str:
        """Convert ten giong tu UI sang API format"""
        if voice in self.UI_TO_GEMINI_VOICE:
            return self.UI_TO_GEMINI_VOICE[voice]
        if voice in self.UI_TO_EDGE_VOICE:
            return self.UI_TO_EDGE_VOICE[voice]
        return voice

    def _is_gemini_voice(self, voice: str) -> bool:
        """Check if voice is Gemini voice"""
        return voice.startswith("gemini-") or voice in self.UI_TO_GEMINI_VOICE

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

        # Convert voice from UI format to API format
        voice = self._convert_voice(voice)

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
        AUTO FALLBACK sang Edge TTS neu Gemini khong kha dung
        """
        import wave

        # AUTO FALLBACK: Neu google-genai chua cai dat, dung Edge TTS
        if genai is None:
            print("[Gemini TTS] google-genai chua cai dat - AUTO FALLBACK sang Edge TTS")
            return self._generate_single(text, "vi-VN-HoaiMyNeural", "+0%", progress_callback)

        if progress_callback:
            progress_callback(5)

        # Lay API key tu environment neu khong truyen
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        # AUTO FALLBACK: Neu chua co API key, dung Edge TTS
        if not api_key:
            print("[Gemini TTS] Chua co API key - AUTO FALLBACK sang Edge TTS")
            return self._generate_single(text, "vi-VN-HoaiMyNeural", "+0%", progress_callback)

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

            # AUTO FALLBACK sang Edge-TTS cho TAT CA loi (bao gom ca API key)
            print("[Gemini TTS] AUTO FALLBACK sang Edge-TTS...")
            try:
                return self._generate_single(text, "vi-VN-HoaiMyNeural", "+0%", progress_callback)
            except Exception as fallback_error:
                # Neu Edge TTS cung fail, moi raise exception
                raise Exception(f"Gemini TTS va Edge TTS deu loi. Gemini: {error_msg}, Edge: {str(fallback_error)}")

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
        """Tao audio cho text dai - XU LY TUAN TU DE DAM BAO KHONG BO SOT"""
        import time

        # Chia text thanh cac chunk
        chunks = self._split_text(text)
        total_chunks = len(chunks)

        print(f"[TTS] Text dai: {len(text)} ky tu, chia thanh {total_chunks} chunks")
        print(f"[TTS] XU LY TUAN TU de dam bao khong bo sot bat ky doan nao")

        # Tao danh sach output paths theo thu tu
        session_id = uuid.uuid4().hex[:6]
        chunk_paths = []
        for i in range(total_chunks):
            chunk_filename = f"tts_chunk_{session_id}_{i:04d}.mp3"
            chunk_paths.append(str(self.temp_dir / chunk_filename))

        # XU LY TUAN TU - KHONG SONG SONG de dam bao khong bo sot
        successful_files = []

        try:
            for i, chunk_text in enumerate(chunks):
                output_path = chunk_paths[i]
                print(f"[TTS] Dang xu ly chunk {i+1}/{total_chunks} ({len(chunk_text)} ky tu)...")

                # RETRY TOI DA 5 LAN cho moi chunk
                success = False
                for attempt in range(5):
                    try:
                        if attempt > 0:
                            wait_time = 1.0 + attempt * 0.5
                            print(f"[TTS] Chunk {i+1}: Retry lan {attempt + 1}, doi {wait_time:.1f}s...")
                            time.sleep(wait_time)

                        # Thu voi voice duoc chon truoc
                        self._run_async_tts(chunk_text, voice, rate, output_path)

                        if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                            print(f"[TTS] Chunk {i+1}/{total_chunks}: OK ({os.path.getsize(output_path) / 1024:.1f} KB)")
                            successful_files.append(output_path)
                            success = True
                            break
                        else:
                            raise Exception("File audio khong hop le")

                    except Exception as e:
                        print(f"[TTS] Chunk {i+1}: Loi '{e}'")

                        # Sau 2 lan that bai, thu voi Edge TTS (stable hon)
                        if attempt >= 2:
                            print(f"[TTS] Chunk {i+1}: Thu voi Edge TTS...")
                            try:
                                self._run_async_tts(chunk_text, "vi-VN-HoaiMyNeural", "+0%", output_path)
                                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                                    print(f"[TTS] Chunk {i+1}: THANH CONG voi Edge TTS!")
                                    successful_files.append(output_path)
                                    success = True
                                    break
                            except Exception as edge_error:
                                print(f"[TTS] Chunk {i+1}: Edge TTS cung fail: {edge_error}")

                # Neu chunk nay that bai hoan toan, BAO LOI NGAY
                if not success:
                    raise Exception(f"Chunk {i+1}/{total_chunks} THAT BAI sau 5 lan retry! Dung xu ly.")

                # Update progress
                if progress_callback:
                    progress = int(((i + 1) / total_chunks) * 85) + 10
                    progress_callback(progress)

            # Kiem tra ket qua
            if len(successful_files) != total_chunks:
                raise Exception(f"Chi tao duoc {len(successful_files)}/{total_chunks} chunks!")

            print(f"[TTS] Da tao THANH CONG {len(successful_files)}/{total_chunks} chunks")

            # Ghep tat ca chunk thanh 1 file
            if progress_callback:
                progress_callback(90)

            output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            final_output_path = str(self.temp_dir / output_filename)

            print(f"[TTS] Dang ghep {len(successful_files)} file audio...")
            self._concat_audio_files(successful_files, final_output_path)

            # Kiem tra file output
            if not os.path.exists(final_output_path) or os.path.getsize(final_output_path) < 1000:
                raise Exception("Ghep file audio that bai!")

            print(f"[TTS] HOAN THANH: {os.path.getsize(final_output_path) / 1024:.1f} KB")

            if progress_callback:
                progress_callback(100)

            return final_output_path

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
        """Ghep nhieu file audio thanh 1 file bang FFmpeg - FIX CHO WINDOWS"""
        if len(input_files) == 1:
            import shutil
            shutil.copy(input_files[0], output_path)
            return

        # Neu chi co 2-3 files, dung crossfade de muot hon
        if len(input_files) <= 3:
            self._concat_with_crossfade(input_files, output_path)
            return

        # Neu nhieu files, dung concat thong thuong (nhanh hon)
        list_filename = f"concat_list_{uuid.uuid4().hex[:8]}.txt"
        list_path = str(self.temp_dir / list_filename)

        print(f"[TTS] Ghep {len(input_files)} file audio...")

        try:
            with open(list_path, 'w', encoding='utf-8') as f:
                for file_path in input_files:
                    # QUAN TRONG: Tren Windows, phai dung forward slash / hoac escape backslash
                    # FFmpeg concat demuxer can forward slash
                    normalized_path = file_path.replace('\\', '/')
                    f.write(f"file '{normalized_path}'\n")

            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_path,
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Kiem tra ket qua
            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                print(f"[TTS] FFmpeg concat error: {error_msg}")
                # Fallback: Thu ghep tung file mot
                self._concat_sequential(input_files, output_path)
            elif not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                print(f"[TTS] Concat output invalid, trying sequential merge...")
                self._concat_sequential(input_files, output_path)
            else:
                print(f"[TTS] Concat thanh cong: {os.path.getsize(output_path) / 1024:.1f} KB")

        finally:
            try:
                if os.path.exists(list_path):
                    os.unlink(list_path)
            except:
                pass

    def _concat_sequential(self, input_files: List[str], output_path: str):
        """Ghep file tuan tu - FALLBACK khi concat list fail"""
        import shutil

        print(f"[TTS] Fallback: Ghep {len(input_files)} file tuan tu...")

        # Ghep tung cap file mot
        temp_output = None
        current_input = input_files[0]

        for i, next_file in enumerate(input_files[1:], 1):
            temp_output = str(self.temp_dir / f"concat_temp_{i}.mp3")

            cmd = [
                'ffmpeg', '-y',
                '-i', current_input,
                '-i', next_file,
                '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]',
                '-map', '[out]',
                '-c:a', 'libmp3lame',
                '-b:a', '192k',
                temp_output
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if result.returncode != 0:
                print(f"[TTS] Sequential concat {i} failed: {result.stderr.decode()[:200]}")
                # Neu fail, copy file hien tai
                if os.path.exists(current_input):
                    shutil.copy(current_input, output_path)
                return

            # Xoa temp truoc do (neu khong phai file goc)
            if i > 1 and os.path.exists(current_input) and 'concat_temp' in current_input:
                try:
                    os.unlink(current_input)
                except:
                    pass

            current_input = temp_output
            print(f"[TTS] Ghep {i}/{len(input_files)-1} xong")

        # Copy ket qua cuoi cung
        if temp_output and os.path.exists(temp_output):
            shutil.copy(temp_output, output_path)
            try:
                os.unlink(temp_output)
            except:
                pass
            print(f"[TTS] Sequential concat hoan thanh: {os.path.getsize(output_path) / 1024:.1f} KB")

    def _concat_with_crossfade(self, input_files: List[str], output_path: str):
        """Ghep audio voi crossfade 50ms de giong muot hon"""
        if len(input_files) == 2:
            # 2 files: crossfade truc tiep
            cmd = [
                'ffmpeg', '-y',
                '-i', input_files[0],
                '-i', input_files[1],
                '-filter_complex', '[0][1]acrossfade=d=0.05:c1=tri:c2=tri',
                '-c:a', 'libmp3lame', '-b:a', '192k',
                output_path
            ]
        else:
            # 3 files: crossfade tung cap
            cmd = [
                'ffmpeg', '-y',
                '-i', input_files[0],
                '-i', input_files[1],
                '-i', input_files[2],
                '-filter_complex',
                '[0][1]acrossfade=d=0.05:c1=tri:c2=tri[a01];[a01][2]acrossfade=d=0.05:c1=tri:c2=tri',
                '-c:a', 'libmp3lame', '-b:a', '192k',
                output_path
            ]

        subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

    def _run_async_tts(self, text: str, voice: str, rate: str, output_path: str):
        """Chay async TTS voi timeout tang"""
        import concurrent.futures

        # Tang timeout cho text dai hon
        text_length = len(text)
        if text_length > 400:
            timeout_seconds = 120  # 2 phut cho text dai
        elif text_length > 200:
            timeout_seconds = 90   # 1.5 phut cho text vua
        else:
            timeout_seconds = 60   # 1 phut cho text ngan

        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_in_new_loop, text, voice, rate, output_path)
                future.result(timeout=timeout_seconds)
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

    def generate_parallel(
        self,
        text: str,
        voice: str = "vi-VN-HoaiMyNeural",
        speed: float = 1.0,
        num_threads: int = 4,
        max_chars: int = 500,
        add_silence: bool = True,
        silence_duration: float = 0.1,
        progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None
    ) -> str:
        """
        Generate TTS using parallel processing for faster performance

        Args:
            text: Text to convert to speech
            voice: Voice ID (edge-tts, gemini-X, gtts-vi)
            speed: Speech speed (0.5 - 2.0)
            num_threads: Number of parallel threads (default: 4)
            max_chars: Maximum characters per segment (default: 500)
            add_silence: Add silence between segments (default: True)
            silence_duration: Silence duration in seconds (default: 0.1)
            progress_callback: Callback(completed, total, segment_id, result)
            status_callback: Callback(status: str)

        Returns:
            str: Path to generated audio file
        """
        if not text or not text.strip():
            raise ValueError("Text khong duoc de trong!")

        text = text.strip()
        speed = max(0.5, min(2.0, speed))

        if status_callback:
            status_callback("Dang chia text thanh cac doan...")

        # Step 1: Split text into segments using smart splitting
        segments = self.chunked_processor.split_text_for_tts(text, max_chars=max_chars)
        total_segments = len(segments)

        if status_callback:
            status_callback(f"Da chia thanh {total_segments} doan. Bat dau tao giong song song...")

        # For very short text, use regular generate
        if total_segments == 1:
            if status_callback:
                status_callback("Text ngan, tao truc tiep...")
            return self.generate(text, voice, speed, progress_callback)

        # Step 2: Initialize parallel processor - TOI UU TOC DO TOI DA
        # Gemini TTS: 6 workers song song - NHANH NHAT
        # Edge TTS: 10 workers song song
        voice_converted = self._convert_voice(voice)
        is_gemini = voice_converted.startswith("gemini-")

        if is_gemini:
            # Gemini TTS - TOI UU: 6 workers song song
            adaptive_workers = 6
            print(f"[TTS Parallel] Gemini TTS - XU LY SONG SONG (6 workers) cho {total_segments} segments")
        else:
            # Edge-TTS - TOI UU: 10 workers song song
            adaptive_workers = 10
            print(f"[TTS Parallel] Edge-TTS - XU LY SONG SONG (10 workers) cho {total_segments} segments")

        self.parallel_processor = ParallelProcessor(max_workers=adaptive_workers)

        # Prepare rate string for edge-tts
        rate_percent = int((speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"

        # Step 3: Create tasks for each segment
        tasks = []
        segment_paths = []

        # TOI UU TOC DO: Giam retry de xu ly nhanh hon
        # Gemini: 1 retry (fallback nhanh), Edge: 3 retries
        max_retries_per_segment = 1 if is_gemini else 3

        # Tao session ID chung de dam bao thu tu khi ghep
        session_id = uuid.uuid4().hex[:6]

        for i, segment in enumerate(segments):
            # Format: tts_seg_SESSION_INDEX.mp3 - KHONG dung UUID rieng de dam bao thu tu
            segment_path = str(self.temp_dir / f"tts_seg_{session_id}_{i:04d}.mp3")
            segment_paths.append(segment_path)

            task = Task(
                id=f"segment_{i}",
                func=self._generate_segment_with_retry,
                args=(segment, i, total_segments),
                kwargs={
                    "voice": voice,
                    "rate": rate,
                    "output_path": segment_path,
                    "max_retries": max_retries_per_segment
                },
                priority=i  # Process in order
            )
            tasks.append(task)

        # Step 4: Set up progress callback wrapper
        if progress_callback:
            def progress_wrapper(completed, total, task_id, result, error=None):
                if error:
                    if status_callback:
                        status_callback(f"Loi tai {task_id}: {error}")
                else:
                    if status_callback:
                        status_callback(f"Dang tao giong {completed}/{total}...")
                progress_callback(completed, total, task_id, result)

            self.parallel_processor.set_progress_callback(progress_wrapper)

        # Step 5: Run parallel processing
        results = self.parallel_processor.run_parallel(tasks)

        # Step 6: Check for errors - cho phep mot so segments that bai
        errors = [task_id for task_id, result in results.items() if isinstance(result, dict) and "error" in result]
        total_segments_count = len(segment_paths)
        failed_count = len(errors)

        if failed_count > 0:
            print(f"[TTS Parallel] WARNING: {failed_count}/{total_segments_count} segments that bai")
            if status_callback:
                status_callback(f"Canh bao: {failed_count} segments that bai, dang xu ly...")

            # Neu qua nhieu segments that bai (>50%), bao loi
            if failed_count > total_segments_count * 0.5:
                error_msg = f"Qua nhieu segments that bai ({failed_count}/{total_segments_count}): {', '.join(errors[:5])}..."
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)

        # Step 7: Verify all segments - QUAN TRONG: Giu dung thu tu 0, 1, 2, 3...
        valid_segments = []  # List of (index, path)
        skipped_segments = []
        for i, segment_path in enumerate(segment_paths):
            if os.path.exists(segment_path) and os.path.getsize(segment_path) > 500:
                valid_segments.append((i, segment_path))  # Luu ca index de sort
            else:
                skipped_segments.append(i)
                print(f"[TTS Parallel] Skipping segment {i} - file khong ton tai hoac qua nho")

        if not valid_segments:
            raise Exception("Khong tao duoc bat ky segment audio nao!")

        # Sort theo index de dam bao thu tu dung
        valid_segments.sort(key=lambda x: x[0])
        valid_paths = [seg[1] for seg in valid_segments]

        print(f"[TTS Parallel] Ghep {len(valid_paths)} segments theo thu tu: {[s[0] for s in valid_segments]}")

        if skipped_segments:
            print(f"[TTS Parallel] Da bo qua {len(skipped_segments)} segments: {skipped_segments[:10]}...")

        # Step 8: Merge audio chunks with silence
        if status_callback:
            status_callback("Dang ghep cac doan audio...")

        output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        output_path = str(self.temp_dir / output_filename)

        success = self.chunked_processor.merge_audio_chunks(
            valid_paths,
            output_path,
            add_silence=add_silence,
            silence_duration=silence_duration
        )

        if not success:
            raise Exception("Khong the ghep cac doan audio!")

        # Step 9: Cleanup segment files
        for segment_path in segment_paths:
            try:
                if os.path.exists(segment_path):
                    os.remove(segment_path)
            except:
                pass

        if status_callback:
            status_callback("Hoan thanh!")

        if progress_callback:
            progress_callback(total_segments, total_segments, "final", output_path)

        print(f"[TTS Parallel] Hoan thanh: {output_path}")
        return output_path

    def _generate_segment_with_retry(
        self,
        segment_text: str,
        segment_index: int,
        total_segments: int,
        voice: str,
        rate: str,
        output_path: str,
        max_retries: int = 5
    ) -> str:
        """
        Generate TTS for a single segment with retry logic

        Args:
            segment_text: Text segment to convert
            segment_index: Index of this segment
            total_segments: Total number of segments
            voice: Voice ID
            rate: Speech rate
            output_path: Output file path
            max_retries: Maximum retry attempts (default: 5)

        Returns:
            str: Path to generated audio file
        """
        import time
        import random

        # Convert voice from UI format to API format
        voice = self._convert_voice(voice)
        last_error = None

        # Xac dinh engine
        is_gemini = voice.startswith("gemini-")

        for attempt in range(max_retries):
            try:
                # TOI UU TOC DO: Giam delay xuong muc toi thieu
                if attempt > 0:
                    # Retry delay: chi 1 giay cho moi attempt
                    wait_time = 1.0 + random.uniform(0, 0.5)
                    print(f"[TTS] Segment {segment_index}: Retry {attempt + 1}, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    # Delay request dau tien: TOI UU - chi 0.3-0.5s
                    if is_gemini:
                        time.sleep(random.uniform(0.3, 0.5))  # Gemini: 0.3-0.5s
                    else:
                        # Edge TTS: Delay cuc nho
                        time.sleep(random.uniform(0.05, 0.1))  # Edge: 0.05-0.1s

                # Generate audio for this segment
                # Handle different TTS engines
                if voice.startswith("gemini-"):
                    # Extract speed from rate string
                    rate_value = float(rate.rstrip('%')) / 100.0 + 1.0
                    result_path = self._generate_gemini(
                        segment_text,
                        voice,
                        rate_value,
                        progress_callback=None
                    )
                    # Move to expected output path
                    if result_path != output_path:
                        import shutil
                        shutil.move(result_path, output_path)
                elif voice.startswith("gtts"):
                    rate_value = float(rate.rstrip('%')) / 100.0 + 1.0
                    result_path = self._generate_gtts(
                        segment_text,
                        rate_value,
                        progress_callback=None
                    )
                    if result_path != output_path:
                        import shutil
                        shutil.move(result_path, output_path)
                else:
                    # Edge-TTS
                    self._run_async_tts(segment_text, voice, rate, output_path)

                # Verify file was created
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    return output_path
                else:
                    raise Exception("File audio khong hop le hoac qua nho!")

            except Exception as e:
                last_error = e
                error_msg = str(e)
                print(f"[TTS] Segment {segment_index}: Loi '{error_msg}'")

                if attempt < max_retries - 1:
                    continue
                else:
                    # Final attempt failed - FALLBACK TO EDGE TTS
                    if is_gemini:
                        print(f"[TTS] Segment {segment_index}: Gemini that bai sau {max_retries} lan - FALLBACK sang Edge TTS...")
                        try:
                            # Fallback to Edge TTS with Vietnamese voice
                            fallback_voice = "vi-VN-HoaiMyNeural"
                            self._run_async_tts(segment_text, fallback_voice, rate, output_path)

                            # Verify fallback succeeded
                            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                                print(f"[TTS] Segment {segment_index}: THANH CONG voi Edge TTS fallback!")
                                return output_path
                            else:
                                raise Exception("Edge TTS fallback tao file khong hop le")
                        except Exception as fallback_error:
                            print(f"[TTS] Segment {segment_index}: Edge TTS fallback cung that bai: {fallback_error}")
                            return {"error": f"Segment {segment_index + 1}/{total_segments} failed (Gemini + Edge fallback): {error_msg}"}
                    else:
                        # Edge TTS that bai - khong fallback
                        print(f"[TTS] Segment {segment_index}: THAT BAI sau {max_retries} lan")
                        return {"error": f"Segment {segment_index + 1}/{total_segments} failed: {error_msg}"}

        # Should not reach here, but just in case
        if is_gemini:
            # Try Edge TTS fallback
            print(f"[TTS] Segment {segment_index}: Gemini timeout - FALLBACK sang Edge TTS...")
            try:
                fallback_voice = "vi-VN-HoaiMyNeural"
                self._run_async_tts(segment_text, fallback_voice, rate, output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    print(f"[TTS] Segment {segment_index}: THANH CONG voi Edge TTS fallback!")
                    return output_path
            except:
                pass
        return {"error": f"Segment {segment_index + 1}/{total_segments} failed: {str(last_error)}"}

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
