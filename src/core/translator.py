"""
Module dich van ban - Ho tro nhieu provider voi fallback
"""
import time
import urllib.request
import urllib.parse
import json
import re
from typing import Optional


class Translator:
    """Dich van ban tu tieng Trung sang tieng Viet"""

    def __init__(self):
        # Thu tu uu tien cac provider
        self.providers = [
            "google_free",      # Google Translate free API (khong can key)
            "google_web",       # Google Translate web scraping
            "mymemory",         # MyMemory API (free)
            "deep_google",      # deep-translator Google
        ]

    def translate(self, text: str, source: str = "zh-CN", target: str = "vi",
                  progress_callback=None, status_callback=None) -> str:
        """
        Dich van ban voi nhieu provider fallback
        """
        if not text or not text.strip():
            return ""

        text = text.strip()

        if progress_callback:
            progress_callback(10)

        errors = []

        # Thu tung provider
        for i, provider in enumerate(self.providers):
            try:
                if status_callback:
                    status_callback(f"Dang dich voi {provider}...")

                if progress_callback:
                    progress_callback(10 + int((i / len(self.providers)) * 30))

                result = self._translate_with_provider(text, source, target, provider, status_callback)

                if result and result.strip() and result.strip() != text.strip():
                    if progress_callback:
                        progress_callback(100)
                    if status_callback:
                        status_callback(f"Dich thanh cong voi {provider}")
                    return result

            except Exception as e:
                error_msg = f"{provider}: {str(e)[:100]}"
                errors.append(error_msg)
                print(f"[Translator] {error_msg}")
                continue

        # Tat ca provider loi
        if status_callback:
            status_callback("Tat ca provider deu loi!")
        raise Exception(f"Khong the dich van ban. Tat ca provider deu that bai. Kiem tra ket noi mang.\nChi tiet: {'; '.join(errors[:3])}")

    def _translate_with_provider(self, text: str, source: str, target: str,
                                  provider: str, status_callback=None) -> Optional[str]:
        """Dich voi provider cu the"""

        # Chia text thanh cac chunk nho
        MAX_CHUNK = 4500
        chunks = self._split_text(text, MAX_CHUNK)
        results = []

        for idx, chunk in enumerate(chunks):
            if status_callback and len(chunks) > 1:
                status_callback(f"{provider}: Doan {idx+1}/{len(chunks)}...")

            if provider == "google_free":
                result = self._translate_google_free(chunk, source, target)
            elif provider == "google_web":
                result = self._translate_google_web(chunk, source, target)
            elif provider == "mymemory":
                result = self._translate_mymemory(chunk, source, target)
            elif provider == "deep_google":
                result = self._translate_deep_google(chunk, source, target)
            else:
                raise ValueError(f"Provider khong hop le: {provider}")

            if result:
                results.append(result)

            # Delay nho giua cac chunk de tranh rate limit
            if idx < len(chunks) - 1:
                time.sleep(0.5)

        return " ".join(results) if results else None

    def _translate_google_free(self, text: str, source: str, target: str) -> Optional[str]:
        """Google Translate free API - PHUONG PHAP CHINH"""
        # Convert language codes
        src = source.replace("-CN", "").replace("-TW", "")  # zh-CN -> zh
        tgt = target

        # URL encode text
        encoded_text = urllib.parse.quote(text)

        # Google Translate API endpoint (free)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={tgt}&dt=t&q={encoded_text}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)

                # Extract translated text from response
                if result and isinstance(result, list) and result[0]:
                    translated_parts = []
                    for part in result[0]:
                        if part and len(part) > 0 and part[0]:
                            translated_parts.append(part[0])
                    return "".join(translated_parts)
        except Exception as e:
            raise Exception(f"Google Free API loi: {e}")

        return None

    def _translate_google_web(self, text: str, source: str, target: str) -> Optional[str]:
        """Google Translate qua web interface"""
        src = source.replace("-CN", "").replace("-TW", "")
        tgt = target

        # Gioi han do dai cho URL
        if len(text) > 2000:
            text = text[:2000]

        encoded_text = urllib.parse.quote(text)

        # Alternative Google endpoint
        url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={src}&tl={tgt}&q={encoded_text}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0')

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)

                # Format: [["translated text"]]
                if result and isinstance(result, list):
                    if isinstance(result[0], list):
                        return result[0][0]
                    elif isinstance(result[0], str):
                        return result[0]
        except Exception as e:
            raise Exception(f"Google Web loi: {e}")

        return None

    def _translate_mymemory(self, text: str, source: str, target: str) -> Optional[str]:
        """MyMemory Translation API (free, 1000 words/day)"""
        src = source.replace("-CN", "-HANS") if "zh" in source else source
        tgt = target

        # Gioi han 500 chars cho MyMemory free
        if len(text) > 500:
            text = text[:500]

        encoded_text = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={src}|{tgt}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)

                if result.get('responseStatus') == 200:
                    translated = result.get('responseData', {}).get('translatedText')
                    if translated and translated.upper() != text.upper():
                        return translated
        except Exception as e:
            raise Exception(f"MyMemory loi: {e}")

        return None

    def _translate_deep_google(self, text: str, source: str, target: str) -> Optional[str]:
        """Dung deep-translator library (backup)"""
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=source, target=target)
            result = translator.translate(text)
            return result
        except ImportError:
            raise Exception("deep-translator chua cai")
        except Exception as e:
            raise Exception(f"deep-translator loi: {e}")

    def _split_text(self, text: str, max_length: int) -> list:
        """Chia text thanh cac chunk theo cau"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        # Tach theo cac dau cham cau Trung va Viet
        # Giu nguyen dau cham trong chunk
        sentences = re.split(r'([。！？\.\!\?]+)', text)

        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            # Ket hop cau voi dau cham cua no
            if i + 1 < len(sentences) and re.match(r'^[。！？\.\!\?]+$', sentences[i + 1]):
                sentence += sentences[i + 1]
                i += 1

            if len(current_chunk) + len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence

            i += 1

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]
