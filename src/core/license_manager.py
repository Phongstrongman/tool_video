"""
License Manager - Kiểm tra license từ Google Sheets

CHỨC NĂNG:
- Tải danh sách license từ Google Sheets (CSV)
- Kiểm tra license key hợp lệ
- Lưu license key vào file local
- Hỗ trợ offline mode nếu có license.key
"""
import csv
import requests
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional


class LicenseManager:
    """Quản lý license cho ứng dụng"""

    def __init__(self, sheet_url: str):
        """
        Khởi tạo LicenseManager

        Args:
            sheet_url: URL Google Sheets CSV export
        """
        self.sheet_url = sheet_url
        self.license_file = Path(__file__).parent.parent / "utils" / "license.key"

    def validate_license(self, license_key: str) -> Tuple[bool, str]:
        """
        Kiểm tra license key có hợp lệ không

        Args:
            license_key: License key cần kiểm tra

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        # Thử kiểm tra online trước
        online_result = self._validate_online(license_key)
        if online_result[0]:
            # License hợp lệ online -> lưu vào file
            self._save_license(license_key)
            return online_result

        # Nếu online fail, thử kiểm tra offline
        if not online_result[0] and "internet" in online_result[1].lower():
            offline_result = self._validate_offline(license_key)
            if offline_result[0]:
                return offline_result

        return online_result

    def _validate_online(self, license_key: str) -> Tuple[bool, str]:
        """
        Kiểm tra license online từ Google Sheets

        Args:
            license_key: License key cần kiểm tra

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Tải CSV từ Google Sheets
            response = requests.get(self.sheet_url, timeout=10)
            response.raise_for_status()

            # Parse CSV
            csv_data = response.text.splitlines()
            reader = csv.reader(csv_data)

            # Bỏ qua header (nếu có)
            next(reader, None)

            # Tìm license key
            for row in reader:
                if len(row) < 3:
                    continue

                db_key = row[0].strip()
                expiry_date = row[1].strip()
                status = row[2].strip().lower()

                if db_key == license_key:
                    # Tìm thấy license key
                    if status != "active":
                        return False, f"License không hoạt động (status: {status})"

                    # Kiểm tra ngày hết hạn
                    try:
                        expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
                        if expiry < datetime.now():
                            return False, f"License đã hết hạn ({expiry_date})"

                        days_left = (expiry - datetime.now()).days
                        return True, f"License hợp lệ (còn {days_left} ngày)"
                    except ValueError:
                        return False, "Định dạng ngày hết hạn không hợp lệ"

            # Không tìm thấy license key
            return False, "License key không tồn tại"

        except requests.ConnectionError:
            return False, "Không thể kết nối internet. Đang thử chế độ offline..."
        except requests.Timeout:
            return False, "Timeout khi kết nối. Đang thử chế độ offline..."
        except Exception as e:
            return False, f"Lỗi kiểm tra online: {str(e)}"

    def _validate_offline(self, license_key: str) -> Tuple[bool, str]:
        """
        Kiểm tra license offline (từ file đã lưu)

        Args:
            license_key: License key cần kiểm tra

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        if not self.license_file.exists():
            return False, "Không có license offline. Cần kết nối internet để kích hoạt."

        try:
            saved_key = self.license_file.read_text(encoding='utf-8').strip()
            if saved_key == license_key:
                return True, "License hợp lệ (chế độ offline)"
            else:
                return False, "License key không khớp với license đã lưu"
        except Exception as e:
            return False, f"Lỗi đọc license offline: {str(e)}"

    def _save_license(self, license_key: str):
        """
        Lưu license key vào file

        Args:
            license_key: License key cần lưu
        """
        try:
            self.license_file.parent.mkdir(parents=True, exist_ok=True)
            self.license_file.write_text(license_key, encoding='utf-8')
        except Exception as e:
            print(f"Cảnh báo: Không thể lưu license: {e}")

    def get_saved_license(self) -> Optional[str]:
        """
        Lấy license key đã lưu

        Returns:
            str hoặc None: License key đã lưu
        """
        if self.license_file.exists():
            try:
                return self.license_file.read_text(encoding='utf-8').strip()
            except Exception:
                return None
        return None

    def has_valid_offline_license(self) -> bool:
        """
        Kiểm tra có license offline hợp lệ không (không check online)

        Returns:
            bool: True nếu có license.key
        """
        return self.license_file.exists()