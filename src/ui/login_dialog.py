"""
Login Dialog for DouyinVoice Pro

Simple dialog to enter license key and login to server
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.ui.styles import DARK_STYLE
from src.core.api_client import APIClient
import uuid


class LoginDialog(QDialog):
    """Login dialog for license authentication"""

    def __init__(self, api_client: APIClient, parent=None):
        """
        Initialize LoginDialog

        Args:
            api_client: APIClient instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.api_client = api_client
        self.is_logged_in = False
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("DouyinVoice Pro - Đăng nhập")
        self.setFixedWidth(550)
        self.setStyleSheet(DARK_STYLE)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)

        # ===== TITLE =====
        title_label = QLabel("[LOGIN] DANG NHAP")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #89b4fa; margin: 10px;")
        main_layout.addWidget(title_label)

        # ===== SERVER STATUS =====
        server_group = QGroupBox("[SERVER] Trang thai Server")
        server_layout = QVBoxLayout()

        # Check server health
        is_healthy, health_data = self.api_client.health_check()

        if is_healthy:
            status_label = QLabel(f"[OK] Server dang hoat dong\n[URL] {self.api_client.server_url}")
            status_label.setStyleSheet("color: #a6e3a1; font-size: 13px;")
        else:
            status_label = QLabel(
                f"[X] Khong the ket noi server\n"
                f"[URL] {self.api_client.server_url}\n\n"
                f"Vui long kiem tra:\n"
                f"1. Server dang chay?\n"
                f"2. URL trong src/utils/config.py dung chua?\n"
                f"3. Co internet khong?"
            )
            status_label.setStyleSheet("color: #f38ba8; font-size: 12px;")

        status_label.setWordWrap(True)
        server_layout.addWidget(status_label)

        server_group.setLayout(server_layout)
        main_layout.addWidget(server_group)

        # ===== LICENSE INPUT =====
        license_group = QGroupBox("[KEY] Nhap License Key")
        license_layout = QVBoxLayout()

        instruction = QLabel(
            "Nhap license key de su dung DouyinVoice Pro.\n"
            "License key co dang: DVPRO-XXXX-XXXX-XXXX"
        )
        instruction.setWordWrap(True)
        instruction.setStyleSheet("font-size: 12px; padding: 5px;")
        license_layout.addWidget(instruction)

        # Input field
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("DVPRO-XXXX-XXXX-XXXX")
        self.license_input.setStyleSheet(
            "font-size: 14px; padding: 12px; font-family: 'Consolas', monospace;"
        )
        self.license_input.returnPressed.connect(self.do_login)
        license_layout.addWidget(self.license_input)

        license_group.setLayout(license_layout)
        main_layout.addWidget(license_group)

        # ===== PURCHASE INFO =====
        purchase_group = QGroupBox("[PRICE] Bang Gia")
        purchase_layout = QVBoxLayout()

        purchase_info = QLabel(
            "[INFO] GIA:\n"
            "   - Basic: 50.000d (100 videos/thang)\n"
            "   - Pro: 150.000d (500 videos/thang)\n"
            "   - VIP: 300.000d (Khong gioi han)\n\n"
            "[CONTACT] Lien he:\n"
            "   - Zalo: 0366468477\n"
            "   - Momo: 0366468477"
        )
        purchase_info.setStyleSheet("font-size: 12px;")
        purchase_layout.addWidget(purchase_info)

        purchase_group.setLayout(purchase_layout)
        main_layout.addWidget(purchase_group)

        # ===== BUTTONS =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Login button
        self.login_btn = QPushButton("[OK] DANG NHAP")
        self.login_btn.setStyleSheet(
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
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            """
        )
        self.login_btn.clicked.connect(self.do_login)
        self.login_btn.setEnabled(is_healthy)  # Only enable if server is up
        button_layout.addWidget(self.login_btn)

        # Cancel button
        self.cancel_btn = QPushButton("[X] HUY")
        self.cancel_btn.setStyleSheet(
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
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

        # ===== HELP TEXT =====
        help_label = QLabel(
            "[TIP] Chua co license? Lien he Zalo/Momo: 0366468477"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "font-size: 11px; color: #f9e2af; padding: 10px; "
            "background-color: #313244; border-radius: 6px;"
        )
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(help_label)

        self.setLayout(main_layout)

    def do_login(self):
        """Handle login button click"""
        license_key = self.license_input.text().strip()

        if not license_key:
            QMessageBox.warning(
                self,
                "Thieu thong tin",
                "Vui long nhap license key!"
            )
            return

        # Disable button during login
        self.login_btn.setEnabled(False)
        self.login_btn.setText("[LOADING] Dang dang nhap...")

        # Generate machine ID (simple UUID)
        machine_id = str(uuid.uuid4())

        # Attempt login
        success, message, license_data = self.api_client.login(license_key, machine_id)

        # Re-enable button
        self.login_btn.setEnabled(True)
        self.login_btn.setText("[OK] DANG NHAP")

        if success:
            # Show success message with tier info
            days_left = license_data.get("days_left", "N/A")
            tier = license_data.get("tier", "basic").upper()
            monthly_limit = license_data.get("monthly_limit", 100)
            videos_remaining = license_data.get("videos_remaining", monthly_limit)
            reset_date = license_data.get("reset_date", "N/A")

            # Format remaining videos
            if monthly_limit > 0:
                remaining_str = f"{videos_remaining}/{monthly_limit} videos"
            else:
                remaining_str = "Unlimited videos"

            QMessageBox.information(
                self,
                "Dang nhap thanh cong",
                f"[SUCCESS] Dang nhap thanh cong!\n\n"
                f"[PRODUCT] Goi: {tier}\n"
                f"[STATS] Con lai thang nay: {remaining_str}\n"
                f"[DATE] Reset: {reset_date}\n"
                f"[TIME] Het han: {days_left} ngay\n\n"
                f"Ban co the bat dau su dung DouyinVoice Pro!"
            )
            self.is_logged_in = True
            self.accept()
        else:
            # Show error
            QMessageBox.critical(
                self,
                "Dang nhap that bai",
                f"[X] Khong the dang nhap!\n\n"
                f"Loi: {message}\n\n"
                f"Vui long kiem tra lai license key hoac lien he:\n"
                f"Zalo/Momo: 0366468477"
            )

    def get_login_status(self) -> bool:
        """Get login status"""
        return self.is_logged_in
