"""
API Client for DouyinVoice Pro

Communicates with the license server for:
- Login/authentication
- Speech-to-Text
- Text-to-Speech
- Translation

All API keys are on the server, not in the client.
"""
import requests
from pathlib import Path
from typing import Tuple, Optional
import json
import sys

# Add src to path if not already there
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.config import SERVER_URL


class APIClient:
    """Client for communicating with DouyinVoice Pro server"""

    def __init__(self, server_url: str = None):
        """
        Initialize API client

        Args:
            server_url: Base URL of the server (default: from config.py)
        """
        # Use provided URL or default from config
        if server_url is None:
            server_url = SERVER_URL
        self.server_url = server_url.rstrip("/")
        self.token: Optional[str] = None
        self.token_file = Path(__file__).parent.parent / "utils" / ".token"

        # Load saved token if exists
        self._load_token()

    def _load_token(self):
        """Load token from file"""
        if self.token_file.exists():
            try:
                self.token = self.token_file.read_text(encoding='utf-8').strip()
            except Exception:
                pass

    def _save_token(self, token: str):
        """Save token to file"""
        try:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(token, encoding='utf-8')
            self.token = token
        except Exception as e:
            print(f"Warning: Could not save token: {e}")

    def _get_headers(self) -> dict:
        """Get headers with authorization token"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def login(self, license_key: str, machine_id: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
        """
        Login with license key

        Args:
            license_key: License key
            machine_id: Optional machine ID for binding

        Returns:
            Tuple of (success, message, license_data)
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/login",
                json={
                    "license_key": license_key,
                    "machine_id": machine_id
                },
                timeout=10
            )

            data = response.json()

            if data.get("success"):
                # Save token
                self._save_token(data["token"])
                return True, data["message"], data.get("license_data")
            else:
                return False, data["message"], None

        except requests.ConnectionError:
            return False, "Không thể kết nối server. Vui lòng kiểm tra:\n1. Server đang chạy?\n2. URL đúng không?\n3. Có internet không?", None
        except requests.Timeout:
            return False, "Timeout khi kết nối server", None
        except Exception as e:
            return False, f"Lỗi login: {str(e)}", None

    def logout(self) -> bool:
        """
        Logout and invalidate token

        Returns:
            True if successful
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/logout",
                headers=self._get_headers(),
                timeout=5
            )

            # Delete local token regardless of server response
            if self.token_file.exists():
                self.token_file.unlink()
            self.token = None

            return response.status_code == 200

        except Exception:
            # Delete local token anyway
            if self.token_file.exists():
                self.token_file.unlink()
            self.token = None
            return True

    def is_logged_in(self) -> bool:
        """Check if user is logged in (has token)"""
        return self.token is not None

    def speech_to_text(self, audio_file: str, language: str = "zh") -> Tuple[bool, Optional[str], str]:
        """
        Speech-to-Text via server

        Args:
            audio_file: Path to audio file
            language: Language code (default: "zh" for Chinese)

        Returns:
            Tuple of (success, transcribed_text, message)
        """
        if not self.is_logged_in():
            return False, None, "Chưa đăng nhập. Vui lòng đăng nhập trước."

        try:
            # Upload audio file
            with open(audio_file, 'rb') as f:
                files = {'file': f}
                data = {'language': language}

                response = requests.post(
                    f"{self.server_url}/api/speech-to-text",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=60  # STT can take a while
                )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return True, result.get("text"), result.get("message", "")
                else:
                    return False, None, result.get("message", "Unknown error")
            elif response.status_code == 401:
                self.token = None
                return False, None, "Token hết hạn. Vui lòng đăng nhập lại."
            else:
                return False, None, f"Server error: {response.status_code}"

        except requests.ConnectionError:
            return False, None, "Không thể kết nối server"
        except requests.Timeout:
            return False, None, "Timeout - file audio quá lớn hoặc server chậm"
        except Exception as e:
            return False, None, f"Lỗi STT: {str(e)}"

    def translate(self, text: str, source_lang: str = "zh-CN", target_lang: str = "vi") -> Tuple[bool, Optional[str], str]:
        """
        Translate text via server

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Tuple of (success, translated_text, message)
        """
        if not self.is_logged_in():
            return False, None, "Chưa đăng nhập. Vui lòng đăng nhập trước."

        try:
            response = requests.post(
                f"{self.server_url}/api/translate",
                json={
                    "text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                },
                headers=self._get_headers(),
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return True, result.get("translated_text"), result.get("message", "")
                else:
                    return False, None, result.get("message", "Unknown error")
            elif response.status_code == 401:
                self.token = None
                return False, None, "Token hết hạn. Vui lòng đăng nhập lại."
            else:
                return False, None, f"Server error: {response.status_code}"

        except requests.ConnectionError:
            return False, None, "Không thể kết nối server"
        except requests.Timeout:
            return False, None, "Timeout khi dịch"
        except Exception as e:
            return False, None, f"Lỗi dịch: {str(e)}"

    def health_check(self) -> Tuple[bool, Optional[dict]]:
        """
        Check if server is running

        Returns:
            Tuple of (is_healthy, health_data)
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, None

        except Exception:
            return False, None
