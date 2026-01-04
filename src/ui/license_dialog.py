"""
License Dialog - Dialog nhập license key

CHỨC NĂNG:
- Hiển thị form nhập license key
- Kiểm tra license với LicenseManager
- Hiển thị thông tin liên hệ mua license
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QTextEdit,
    QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.ui.styles import DARK_STYLE
from src.core.license_manager import LicenseManager


class LicenseDialog(QDialog):
    """Dialog nhập và kích hoạt license"""

    def __init__(self, license_manager: LicenseManager, parent=None):
        """
        Khởi tạo LicenseDialog

        Args:
            license_manager: LicenseManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.license_manager = license_manager
        self.is_activated = False
        self.init_ui()

    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("DouyinVoice Pro - Kích hoạt license")
        self.setFixedWidth(600)
        self.setStyleSheet(DARK_STYLE)

        # Layout chính
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)

        # ===== TIÊU ĐỀ =====
        title_label = QLabel("🔐 KÍCH HOẠT LICENSE")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #89b4fa; margin: 10px;")
        main_layout.addWidget(title_label)

        # ===== THÔNG TIN SẢN PHẨM =====
        product_group = QGroupBox("📦 Thông tin sản phẩm")
        product_layout = QVBoxLayout()

        product_info = QLabel(
            "DouyinVoice Pro - Tool chuyển đổi giọng video Douyin/TikTok\n"
            "✓ 3 Engine AI Speech-to-Text (Whisper, Groq, AssemblyAI)\n"
            "✓ Dịch tự động Trung → Việt\n"
            "✓ Giọng đọc AI tự nhiên (Nam/Nữ)\n"
            "✓ Xuất video chất lượng cao"
        )
        product_info.setWordWrap(True)
        product_info.setStyleSheet("font-size: 13px; padding: 5px;")
        product_layout.addWidget(product_info)

        product_group.setLayout(product_layout)
        main_layout.addWidget(product_group)

        # ===== GIÁ VÀ LIÊN HỆ =====
        contact_group = QGroupBox("💰 Giá và Liên hệ")
        contact_layout = QVBoxLayout()

        price_label = QLabel("📌 GIÁ: 50.000 VNĐ / tháng")
        price_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #a6e3a1; padding: 5px;"
        )
        contact_layout.addWidget(price_label)

        contact_info = QLabel(
            "📞 Zalo: 0366468477\n"
            "💳 Momo: 0366468477\n"
            "📧 Liên hệ để nhận license key"
        )
        contact_info.setWordWrap(True)
        contact_info.setStyleSheet("font-size: 13px; padding: 5px;")
        contact_layout.addWidget(contact_info)

        contact_group.setLayout(contact_layout)
        main_layout.addWidget(contact_group)

        # ===== NHẬP LICENSE KEY =====
        license_group = QGroupBox("🔑 Nhập License Key")
        license_layout = QVBoxLayout()

        instruction_label = QLabel(
            "Sau khi thanh toán, bạn sẽ nhận được license key.\n"
            "Nhập license key vào ô bên dưới và nhấn 'Kích hoạt':"
        )
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("font-size: 12px; padding: 5px;")
        license_layout.addWidget(instruction_label)

        # Ô nhập license key
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Nhập license key tại đây...")
        self.license_input.setStyleSheet(
            "font-size: 14px; padding: 12px; font-family: 'Consolas', monospace;"
        )

        # Auto-fill nếu đã có license đã lưu
        saved_license = self.license_manager.get_saved_license()
        if saved_license:
            self.license_input.setText(saved_license)

        license_layout.addWidget(self.license_input)

        license_group.setLayout(license_layout)
        main_layout.addWidget(license_group)

        # ===== NÚT HÀNH ĐỘNG =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Nút kích hoạt
        self.activate_btn = QPushButton("✅ KÍCH HOẠT")
        self.activate_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 30px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #b5f1b7;
            }
            QPushButton:pressed {
                background-color: #8bd98a;
            }
            """
        )
        self.activate_btn.clicked.connect(self.activate_license)
        button_layout.addWidget(self.activate_btn)

        # Nút đóng
        self.close_btn = QPushButton("❌ ĐÓNG")
        self.close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 30px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #f5a5bb;
            }
            QPushButton:pressed {
                background-color: #e77491;
            }
            """
        )
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)

        main_layout.addLayout(button_layout)

        # ===== HƯỚNG DẪN =====
        help_label = QLabel(
            "💡 Lưu ý: License key chỉ cần kích hoạt 1 lần.\n"
            "Sau khi kích hoạt thành công, bạn có thể sử dụng offline."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "font-size: 11px; color: #f9e2af; padding: 10px; "
            "background-color: #313244; border-radius: 6px;"
        )
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(help_label)

        self.setLayout(main_layout)

    def activate_license(self):
        """Xử lý kích hoạt license"""
        license_key = self.license_input.text().strip()

        if not license_key:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Vui lòng nhập license key!"
            )
            return

        # Disable button khi đang kiểm tra
        self.activate_btn.setEnabled(False)
        self.activate_btn.setText("⏳ Đang kiểm tra...")

        # Kiểm tra license
        is_valid, message = self.license_manager.validate_license(license_key)

        # Re-enable button
        self.activate_btn.setEnabled(True)
        self.activate_btn.setText("✅ KÍCH HOẠT")

        if is_valid:
            # License hợp lệ
            QMessageBox.information(
                self,
                "Thành công",
                f"🎉 Kích hoạt thành công!\n\n{message}\n\n"
                "Bạn có thể bắt đầu sử dụng ứng dụng."
            )
            self.is_activated = True
            self.accept()
        else:
            # License không hợp lệ
            QMessageBox.critical(
                self,
                "Kích hoạt thất bại",
                f"❌ Không thể kích hoạt license!\n\n"
                f"Lỗi: {message}\n\n"
                f"Vui lòng kiểm tra lại license key hoặc liên hệ:\n"
                f"Zalo/Momo: 0366468477"
            )

    def get_activation_status(self) -> bool:
        """
        Lấy trạng thái kích hoạt

        Returns:
            bool: True nếu đã kích hoạt thành công
        """
        return self.is_activated
