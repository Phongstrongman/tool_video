"""
Module dich van ban - Ho tro nhieu provider
"""
from typing import Optional


class Translator:
    """Dich van ban tu tieng Trung sang tieng Viet"""

    def __init__(self):
        self.providers = ["google", "mymemory", "microsoft"]

    def translate(self, text: str, source: str = "zh-CN", target: str = "vi",
                  progress_callback=None, status_callback=None) -> str:
        """
        Dich van ban

        Args:
            text: Van ban can dich
            source: Ngon ngu nguon (zh-CN)
            target: Ngon ngu dich (vi)
            progress_callback: Callback(progress: int)
            status_callback: Callback(status: str)

        Returns:
            Van ban da dich
        """
        if not text or not text.strip():
            return ""

        text = text.strip()

        if progress_callback:
            progress_callback(10)

        # Thu tung provider
        for provider in self.providers:
            try:
                if status_callback:
                    status_callback(f"Dang dich voi {provider}...")

                result = self._translate_with_provider(text, source, target, provider)

                if result and result.strip():
                    if progress_callback:
                        progress_callback(100)
                    return result

            except Exception as e:
                print(f"[Translator] {provider} loi: {e}")
                continue

        # Tat ca provider loi, tra ve text goc
        if progress_callback:
            progress_callback(100)
        return text

    def _translate_with_provider(self, text: str, source: str, target: str,
                                  provider: str) -> Optional[str]:
        """Dich voi provider cu the"""
        try:
            from deep_translator import GoogleTranslator, MyMemoryTranslator, MicrosoftTranslator
        except ImportError:
            raise Exception("deep-translator chua cai. Chay: pip install deep-translator")

        # Chia text thanh cac chunk nho (deep-translator co gioi han)
        MAX_CHUNK = 4500
        chunks = self._split_text(text, MAX_CHUNK)
        results = []

        for chunk in chunks:
            if provider == "google":
                translator = GoogleTranslator(source=source, target=target)
            elif provider == "mymemory":
                translator = MyMemoryTranslator(source=source, target=target)
            elif provider == "microsoft":
                translator = MicrosoftTranslator(source=source, target=target)
            else:
                raise ValueError(f"Provider khong hop le: {provider}")

            result = translator.translate(chunk)
            if result:
                results.append(result)

        return " ".join(results) if results else None

    def _split_text(self, text: str, max_length: int) -> list:
        """Chia text thanh cac chunk"""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        sentences = text.replace("。", "。\n").replace(".", ".\n").split("\n")

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]
