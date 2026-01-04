"""
DouyinVoice Pro - Main Window UI
PyQt6 GUI voi day du chuc nang
"""
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QProgressBar, QTabWidget, QGroupBox, QCheckBox,
    QSpinBox, QFileDialog, QMessageBox, QSlider,
    QFrame, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from src.ui.styles import DARK_STYLE
from src.workers.async_workers import (
    ExtractWorker, TranscribeWorker, TranslateWorker,
    TTSWorker, ExportWorker
)


class MainWindow(QMainWindow):
    """Cua so chinh cua ung dung"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DouyinVoice Pro v3.0 - Video Voice Changer")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(DARK_STYLE)

        # State
        self.video_path = None
        self.audio_path = None
        self.original_text = ""
        self.translated_text = ""
        self.tts_audio_path = None

        # Workers
        self.extract_worker = None
        self.transcribe_worker = None
        self.translate_worker = None
        self.tts_worker = None
        self.export_worker = None

        self._init_ui()

    def _init_ui(self):
        """Khoi tao giao dien"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Main content with tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3d3d3d; border-radius: 5px; }
            QTabBar::tab { padding: 10px 20px; margin-right: 5px; }
            QTabBar::tab:selected { background: #0d6efd; color: white; }
        """)

        # Tab 1: Main workflow
        tab_main = self._create_main_tab()
        tabs.addTab(tab_main, "Xu Ly Video")

        # Tab 2: Settings
        tab_settings = self._create_settings_tab()
        tabs.addTab(tab_settings, "Cai Dat")

        main_layout.addWidget(tabs, 1)

        # Footer
        footer = self._create_footer()
        main_layout.addWidget(footer)

    def _create_header(self) -> QWidget:
        """Tao header"""
        header = QFrame()
        header.setStyleSheet("background: #1a1a2e; border-radius: 10px; padding: 10px;")
        layout = QHBoxLayout(header)

        title = QLabel("DouyinVoice Pro v3.0")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d4ff;")
        layout.addWidget(title)

        layout.addStretch()

        subtitle = QLabel("Video Voice Changer Tool")
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)

        return header

    def _create_main_tab(self) -> QWidget:
        """Tao tab xu ly chinh"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setSpacing(15)

        # Left panel - Input
        left = self._create_input_panel()
        layout.addWidget(left, 1)

        # Right panel - Output
        right = self._create_output_panel()
        layout.addWidget(right, 1)

        return tab

    def _create_input_panel(self) -> QWidget:
        """Panel nhap lieu"""
        panel = QGroupBox("1. Nhap Video")
        panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #00d4ff;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Video input
        video_group = QFrame()
        video_layout = QHBoxLayout(video_group)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Chon file video hoac nhap URL...")
        self.video_input.setStyleSheet("padding: 10px; border-radius: 5px;")
        video_layout.addWidget(self.video_input, 1)

        btn_browse = QPushButton("Chon File")
        btn_browse.setStyleSheet("""
            QPushButton {
                background: #0d6efd;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #0b5ed7; }
        """)
        btn_browse.clicked.connect(self._browse_video)
        video_layout.addWidget(btn_browse)

        layout.addWidget(video_group)

        # Step 1: Extract audio
        step1 = QGroupBox("Buoc 1: Trich xuat audio")
        step1_layout = QVBoxLayout(step1)

        self.btn_extract = QPushButton("Trich Xuat Audio")
        self.btn_extract.setStyleSheet("""
            QPushButton {
                background: #198754;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #157347; }
            QPushButton:disabled { background: #555; }
        """)
        self.btn_extract.clicked.connect(self._extract_audio)
        step1_layout.addWidget(self.btn_extract)

        self.progress_extract = QProgressBar()
        self.progress_extract.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
                height: 8px;
            }
            QProgressBar::chunk { background: #198754; border-radius: 5px; }
        """)
        step1_layout.addWidget(self.progress_extract)

        self.label_extract_status = QLabel("San sang")
        self.label_extract_status.setStyleSheet("color: #888;")
        step1_layout.addWidget(self.label_extract_status)

        layout.addWidget(step1)

        # Step 2: Speech to text
        step2 = QGroupBox("Buoc 2: Chuyen giong noi thanh van ban")
        step2_layout = QVBoxLayout(step2)

        # STT Engine selection
        stt_row = QHBoxLayout()
        stt_row.addWidget(QLabel("Engine:"))
        self.combo_stt = QComboBox()
        self.combo_stt.addItems(["Groq (Whisper)", "AssemblyAI", "Local Whisper"])
        self.combo_stt.setStyleSheet("padding: 8px;")
        stt_row.addWidget(self.combo_stt, 1)
        step2_layout.addLayout(stt_row)

        self.btn_transcribe = QPushButton("Chuyen Thanh Van Ban")
        self.btn_transcribe.setStyleSheet("""
            QPushButton {
                background: #6f42c1;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5a32a3; }
            QPushButton:disabled { background: #555; }
        """)
        self.btn_transcribe.clicked.connect(self._transcribe_audio)
        self.btn_transcribe.setEnabled(False)
        step2_layout.addWidget(self.btn_transcribe)

        self.progress_transcribe = QProgressBar()
        self.progress_transcribe.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
                height: 8px;
            }
            QProgressBar::chunk { background: #6f42c1; border-radius: 5px; }
        """)
        step2_layout.addWidget(self.progress_transcribe)

        self.label_transcribe_status = QLabel("Cho trich xuat audio")
        self.label_transcribe_status.setStyleSheet("color: #888;")
        step2_layout.addWidget(self.label_transcribe_status)

        layout.addWidget(step2)

        # Original text
        text_group = QGroupBox("Van ban goc (Tieng Trung)")
        text_layout = QVBoxLayout(text_group)

        self.text_original = QTextEdit()
        self.text_original.setPlaceholderText("Van ban goc se hien thi o day...")
        self.text_original.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.text_original.setMinimumHeight(150)
        text_layout.addWidget(self.text_original)

        layout.addWidget(text_group)

        layout.addStretch()

        return panel

    def _create_output_panel(self) -> QWidget:
        """Panel xuat"""
        panel = QGroupBox("2. Xu Ly & Xuat Video")
        panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #00d4ff;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Step 3: Translate
        step3 = QGroupBox("Buoc 3: Dich sang tieng Viet")
        step3_layout = QVBoxLayout(step3)

        self.btn_translate = QPushButton("Dich Van Ban")
        self.btn_translate.setStyleSheet("""
            QPushButton {
                background: #fd7e14;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #e96b02; }
            QPushButton:disabled { background: #555; }
        """)
        self.btn_translate.clicked.connect(self._translate_text)
        self.btn_translate.setEnabled(False)
        step3_layout.addWidget(self.btn_translate)

        self.progress_translate = QProgressBar()
        self.progress_translate.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
                height: 8px;
            }
            QProgressBar::chunk { background: #fd7e14; border-radius: 5px; }
        """)
        step3_layout.addWidget(self.progress_translate)

        self.label_translate_status = QLabel("Cho chuyen thanh van ban")
        self.label_translate_status.setStyleSheet("color: #888;")
        step3_layout.addWidget(self.label_translate_status)

        layout.addWidget(step3)

        # Translated text
        text_group = QGroupBox("Van ban dich (Tieng Viet)")
        text_layout = QVBoxLayout(text_group)

        self.text_translated = QTextEdit()
        self.text_translated.setPlaceholderText("Van ban dich se hien thi o day...")
        self.text_translated.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.text_translated.setMinimumHeight(150)
        text_layout.addWidget(self.text_translated)

        layout.addWidget(text_group)

        # Step 4: TTS
        step4 = QGroupBox("Buoc 4: Tao giong noi")
        step4_layout = QVBoxLayout(step4)

        # TTS Engine
        tts_row = QHBoxLayout()
        tts_row.addWidget(QLabel("Engine:"))
        self.combo_tts = QComboBox()
        self.combo_tts.addItems(["Gemini TTS", "Edge TTS"])
        self.combo_tts.setStyleSheet("padding: 8px;")
        self.combo_tts.currentIndexChanged.connect(self._on_tts_engine_changed)
        tts_row.addWidget(self.combo_tts, 1)
        step4_layout.addLayout(tts_row)

        # Voice selection
        voice_row = QHBoxLayout()
        voice_row.addWidget(QLabel("Giong:"))
        self.combo_voice = QComboBox()
        self._update_voice_list()
        self.combo_voice.setStyleSheet("padding: 8px;")
        voice_row.addWidget(self.combo_voice, 1)
        step4_layout.addLayout(voice_row)

        # Speed control
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Toc do:"))
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(50)
        self.slider_speed.setMaximum(200)
        self.slider_speed.setValue(100)
        self.slider_speed.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_speed.setTickInterval(25)
        speed_row.addWidget(self.slider_speed, 1)
        self.label_speed = QLabel("1.0x")
        speed_row.addWidget(self.label_speed)
        self.slider_speed.valueChanged.connect(
            lambda v: self.label_speed.setText(f"{v/100:.1f}x")
        )
        step4_layout.addLayout(speed_row)

        self.btn_tts = QPushButton("Tao Giong Noi")
        self.btn_tts.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #bb2d3b; }
            QPushButton:disabled { background: #555; }
        """)
        self.btn_tts.clicked.connect(self._generate_tts)
        self.btn_tts.setEnabled(False)
        step4_layout.addWidget(self.btn_tts)

        self.progress_tts = QProgressBar()
        self.progress_tts.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
                height: 8px;
            }
            QProgressBar::chunk { background: #dc3545; border-radius: 5px; }
        """)
        step4_layout.addWidget(self.progress_tts)

        self.label_tts_status = QLabel("Cho dich van ban")
        self.label_tts_status.setStyleSheet("color: #888;")
        step4_layout.addWidget(self.label_tts_status)

        layout.addWidget(step4)

        # Step 5: Export
        step5 = QGroupBox("Buoc 5: Xuat video")
        step5_layout = QVBoxLayout(step5)

        # Output name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Ten file:"))
        self.input_output_name = QLineEdit()
        self.input_output_name.setPlaceholderText("Ten file xuat...")
        self.input_output_name.setStyleSheet("padding: 8px;")
        name_row.addWidget(self.input_output_name, 1)
        step5_layout.addLayout(name_row)

        # Options
        self.check_mix_audio = QCheckBox("Mix voi audio goc")
        step5_layout.addWidget(self.check_mix_audio)

        self.check_anti_copyright = QCheckBox("Ap dung hieu ung chong ban quyen")
        step5_layout.addWidget(self.check_anti_copyright)

        self.btn_export = QPushButton("XUAT VIDEO")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 15px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #764ba2, stop:1 #667eea);
            }
            QPushButton:disabled { background: #555; }
        """)
        self.btn_export.clicked.connect(self._export_video)
        self.btn_export.setEnabled(False)
        step5_layout.addWidget(self.btn_export)

        self.progress_export = QProgressBar()
        self.progress_export.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 5px;
            }
        """)
        step5_layout.addWidget(self.progress_export)

        self.label_export_status = QLabel("Cho tao giong noi")
        self.label_export_status.setStyleSheet("color: #888;")
        step5_layout.addWidget(self.label_export_status)

        layout.addWidget(step5)

        layout.addStretch()

        return panel

    def _create_settings_tab(self) -> QWidget:
        """Tab cai dat"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # API Keys
        api_group = QGroupBox("API Keys")
        api_layout = QVBoxLayout(api_group)

        # Groq API
        groq_row = QHBoxLayout()
        groq_row.addWidget(QLabel("Groq API Key:"))
        self.input_groq_key = QLineEdit()
        self.input_groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_groq_key.setPlaceholderText("Nhap Groq API key...")
        self.input_groq_key.setStyleSheet("padding: 8px;")
        groq_row.addWidget(self.input_groq_key, 1)
        api_layout.addLayout(groq_row)

        # AssemblyAI API
        assembly_row = QHBoxLayout()
        assembly_row.addWidget(QLabel("AssemblyAI Key:"))
        self.input_assembly_key = QLineEdit()
        self.input_assembly_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_assembly_key.setPlaceholderText("Nhap AssemblyAI API key...")
        self.input_assembly_key.setStyleSheet("padding: 8px;")
        assembly_row.addWidget(self.input_assembly_key, 1)
        api_layout.addLayout(assembly_row)

        # Gemini API
        gemini_row = QHBoxLayout()
        gemini_row.addWidget(QLabel("Gemini API Key:"))
        self.input_gemini_key = QLineEdit()
        self.input_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_gemini_key.setPlaceholderText("Nhap Gemini API key...")
        self.input_gemini_key.setStyleSheet("padding: 8px;")
        gemini_row.addWidget(self.input_gemini_key, 1)
        api_layout.addLayout(gemini_row)

        # Save button
        btn_save_api = QPushButton("Luu API Keys")
        btn_save_api.setStyleSheet("""
            QPushButton {
                background: #198754;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #157347; }
        """)
        btn_save_api.clicked.connect(self._save_api_keys)
        api_layout.addWidget(btn_save_api)

        layout.addWidget(api_group)

        # Anti-copyright settings
        ac_group = QGroupBox("Cai dat chong ban quyen")
        ac_layout = QVBoxLayout(ac_group)

        self.check_ac_flip = QCheckBox("Lat ngang video (Mirror)")
        self.check_ac_zoom = QCheckBox("Phong to nhe (Zoom 5%)")
        self.check_ac_effect = QCheckBox("Dieu chinh mau sac")
        self.check_ac_remove_text = QCheckBox("Cat phan text (10% duoi)")

        ac_layout.addWidget(self.check_ac_flip)
        ac_layout.addWidget(self.check_ac_zoom)
        ac_layout.addWidget(self.check_ac_effect)
        ac_layout.addWidget(self.check_ac_remove_text)

        layout.addWidget(ac_group)

        # Watermark settings
        wm_group = QGroupBox("Watermark")
        wm_layout = QVBoxLayout(wm_group)

        self.check_watermark = QCheckBox("Them watermark")
        wm_layout.addWidget(self.check_watermark)

        wm_text_row = QHBoxLayout()
        wm_text_row.addWidget(QLabel("Text:"))
        self.input_watermark = QLineEdit()
        self.input_watermark.setPlaceholderText("@YourChannel")
        self.input_watermark.setStyleSheet("padding: 8px;")
        wm_text_row.addWidget(self.input_watermark, 1)
        wm_layout.addLayout(wm_text_row)

        wm_pos_row = QHBoxLayout()
        wm_pos_row.addWidget(QLabel("Vi tri:"))
        self.combo_watermark_pos = QComboBox()
        self.combo_watermark_pos.addItems([
            "Tren-Phai", "Tren-Trai", "Duoi-Phai", "Duoi-Trai"
        ])
        self.combo_watermark_pos.setStyleSheet("padding: 8px;")
        wm_pos_row.addWidget(self.combo_watermark_pos, 1)
        wm_layout.addLayout(wm_pos_row)

        layout.addWidget(wm_group)

        layout.addStretch()

        # Load saved settings
        self._load_settings()

        return tab

    def _create_footer(self) -> QWidget:
        """Tao footer"""
        footer = QFrame()
        footer.setStyleSheet("background: #1a1a2e; border-radius: 5px; padding: 5px;")
        layout = QHBoxLayout(footer)

        self.label_status = QLabel("San sang")
        self.label_status.setStyleSheet("color: #888;")
        layout.addWidget(self.label_status)

        layout.addStretch()

        version = QLabel("v3.0 - Gemini TTS Edition")
        version.setStyleSheet("color: #555;")
        layout.addWidget(version)

        return footer

    def _update_voice_list(self):
        """Cap nhat danh sach giong theo engine"""
        self.combo_voice.clear()
        engine = self.combo_tts.currentText()

        if "Gemini" in engine:
            voices = [
                "Aoede (Nu - Sang)", "Charon (Nam - Tram)",
                "Fenrir (Nam - Trung)", "Kore (Nu - Tre)",
                "Puck (Nam - Vui)", "Zephyr (Nu - Nhe)",
                "Orbit (Nam - Ro)", "Lyra (Nu - Am)",
                "Nova (Nu - Pro)", "Solaris (Nam - Manh)",
                "Echo (Nam - Vang)", "Aurora (Nu - Trang)",
                "Titan (Nam - Sau)", "Luna (Nu - Diu)"
            ]
        else:
            voices = ["vi-VN-HoaiMyNeural (Nu)", "vi-VN-NamMinhNeural (Nam)"]

        self.combo_voice.addItems(voices)

    def _on_tts_engine_changed(self, index):
        """Xu ly khi doi TTS engine"""
        self._update_voice_list()

    def _browse_video(self):
        """Mo dialog chon video"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chon Video",
            str(Path.home()),
            "Video Files (*.mp4 *.avi *.mkv *.mov *.webm);;All Files (*)"
        )
        if file_path:
            self.video_input.setText(file_path)
            self.video_path = file_path

            # Auto set output name
            name = Path(file_path).stem
            self.input_output_name.setText(f"{name}_viet")

    def _extract_audio(self):
        """Trich xuat audio tu video"""
        video = self.video_input.text().strip()
        if not video:
            QMessageBox.warning(self, "Loi", "Vui long chon video truoc!")
            return

        self.video_path = video
        self.btn_extract.setEnabled(False)
        self.progress_extract.setValue(0)
        self.label_extract_status.setText("Dang trich xuat...")

        self.extract_worker = ExtractWorker(video)
        self.extract_worker.progress.connect(self.progress_extract.setValue)
        self.extract_worker.status.connect(self.label_extract_status.setText)
        self.extract_worker.finished.connect(self._on_extract_finished)
        self.extract_worker.error.connect(self._on_extract_error)
        self.extract_worker.start()

    def _on_extract_finished(self, audio_path: str):
        """Xu ly khi trich xuat xong"""
        self.audio_path = audio_path
        self.btn_extract.setEnabled(True)
        self.btn_transcribe.setEnabled(True)
        self.label_extract_status.setText("Hoan tat!")
        self.label_transcribe_status.setText("San sang")
        self.label_status.setText(f"Da trich xuat: {audio_path}")

    def _on_extract_error(self, error: str):
        """Xu ly loi trich xuat"""
        self.btn_extract.setEnabled(True)
        self.label_extract_status.setText(f"Loi: {error}")
        QMessageBox.critical(self, "Loi", f"Khong the trich xuat audio:\n{error}")

    def _transcribe_audio(self):
        """Chuyen giong noi thanh van ban"""
        if not self.audio_path:
            QMessageBox.warning(self, "Loi", "Chua co audio!")
            return

        engine = self.combo_stt.currentText()
        if "Groq" in engine:
            api_key = self.input_groq_key.text().strip()
            if not api_key:
                QMessageBox.warning(self, "Loi", "Vui long nhap Groq API key trong tab Cai Dat!")
                return
            engine_name = "groq"
        elif "AssemblyAI" in engine:
            api_key = self.input_assembly_key.text().strip()
            if not api_key:
                QMessageBox.warning(self, "Loi", "Vui long nhap AssemblyAI API key trong tab Cai Dat!")
                return
            engine_name = "assemblyai"
        else:
            api_key = None
            engine_name = "whisper"

        self.btn_transcribe.setEnabled(False)
        self.progress_transcribe.setValue(0)
        self.label_transcribe_status.setText("Dang xu ly...")

        self.transcribe_worker = TranscribeWorker(
            self.audio_path, engine_name, api_key
        )
        self.transcribe_worker.progress.connect(self.progress_transcribe.setValue)
        self.transcribe_worker.status.connect(self.label_transcribe_status.setText)
        self.transcribe_worker.finished.connect(self._on_transcribe_finished)
        self.transcribe_worker.error.connect(self._on_transcribe_error)
        self.transcribe_worker.start()

    def _on_transcribe_finished(self, text: str):
        """Xu ly khi transcribe xong"""
        self.original_text = text
        self.text_original.setPlainText(text)
        self.btn_transcribe.setEnabled(True)
        self.btn_translate.setEnabled(True)
        self.label_transcribe_status.setText("Hoan tat!")
        self.label_translate_status.setText("San sang")
        self.label_status.setText("Da chuyen thanh van ban")

    def _on_transcribe_error(self, error: str):
        """Xu ly loi transcribe"""
        self.btn_transcribe.setEnabled(True)
        self.label_transcribe_status.setText(f"Loi: {error}")
        QMessageBox.critical(self, "Loi", f"Khong the chuyen thanh van ban:\n{error}")

    def _translate_text(self):
        """Dich van ban"""
        text = self.text_original.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Loi", "Khong co van ban de dich!")
            return

        self.btn_translate.setEnabled(False)
        self.progress_translate.setValue(0)
        self.label_translate_status.setText("Dang dich...")

        self.translate_worker = TranslateWorker(text)
        self.translate_worker.progress.connect(self.progress_translate.setValue)
        self.translate_worker.status.connect(self.label_translate_status.setText)
        self.translate_worker.finished.connect(self._on_translate_finished)
        self.translate_worker.error.connect(self._on_translate_error)
        self.translate_worker.start()

    def _on_translate_finished(self, text: str):
        """Xu ly khi dich xong"""
        self.translated_text = text
        self.text_translated.setPlainText(text)
        self.btn_translate.setEnabled(True)
        self.btn_tts.setEnabled(True)
        self.label_translate_status.setText("Hoan tat!")
        self.label_tts_status.setText("San sang")
        self.label_status.setText("Da dich xong")

    def _on_translate_error(self, error: str):
        """Xu ly loi dich"""
        self.btn_translate.setEnabled(True)
        self.label_translate_status.setText(f"Loi: {error}")
        QMessageBox.critical(self, "Loi", f"Khong the dich:\n{error}")

    def _generate_tts(self):
        """Tao giong noi TTS"""
        text = self.text_translated.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Loi", "Khong co van ban!")
            return

        engine = self.combo_tts.currentText()
        voice = self.combo_voice.currentText()
        speed = self.slider_speed.value() / 100.0

        # Get API key for Gemini
        api_key = None
        if "Gemini" in engine:
            api_key = self.input_gemini_key.text().strip()
            if not api_key:
                QMessageBox.warning(self, "Loi", "Vui long nhap Gemini API key trong tab Cai Dat!")
                return

        self.btn_tts.setEnabled(False)
        self.progress_tts.setValue(0)
        self.label_tts_status.setText("Dang tao giong noi...")

        self.tts_worker = TTSWorker(text, engine, voice, speed, api_key)
        self.tts_worker.progress.connect(self.progress_tts.setValue)
        self.tts_worker.status.connect(self.label_tts_status.setText)
        self.tts_worker.finished.connect(self._on_tts_finished)
        self.tts_worker.error.connect(self._on_tts_error)
        self.tts_worker.start()

    def _on_tts_finished(self, audio_path: str):
        """Xu ly khi TTS xong"""
        self.tts_audio_path = audio_path
        self.btn_tts.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.label_tts_status.setText("Hoan tat!")
        self.label_export_status.setText("San sang")
        self.label_status.setText(f"Da tao audio: {audio_path}")

    def _on_tts_error(self, error: str):
        """Xu ly loi TTS"""
        self.btn_tts.setEnabled(True)
        self.label_tts_status.setText(f"Loi: {error}")
        QMessageBox.critical(self, "Loi", f"Khong the tao giong noi:\n{error}")

    def _export_video(self):
        """Xuat video cuoi cung"""
        if not self.video_path or not self.tts_audio_path:
            QMessageBox.warning(self, "Loi", "Thieu video hoac audio!")
            return

        output_name = self.input_output_name.text().strip()
        if not output_name:
            output_name = "output"

        # Build options
        anti_copyright = None
        if self.check_anti_copyright.isChecked():
            anti_copyright = {
                "flip": self.check_ac_flip.isChecked(),
                "zoom": self.check_ac_zoom.isChecked(),
                "effect": self.check_ac_effect.isChecked(),
                "remove_text": self.check_ac_remove_text.isChecked()
            }

        watermark = None
        if self.check_watermark.isChecked():
            watermark = {
                "enabled": True,
                "text": self.input_watermark.text().strip(),
                "position": self.combo_watermark_pos.currentText()
            }

        self.btn_export.setEnabled(False)
        self.progress_export.setValue(0)
        self.label_export_status.setText("Dang xuat video...")

        self.export_worker = ExportWorker(
            self.video_path,
            self.tts_audio_path,
            output_name,
            mix_original=self.check_mix_audio.isChecked(),
            anti_copyright=anti_copyright,
            watermark=watermark
        )
        self.export_worker.progress.connect(self.progress_export.setValue)
        self.export_worker.status.connect(self.label_export_status.setText)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.error.connect(self._on_export_error)
        self.export_worker.start()

    def _on_export_finished(self, output_path: str):
        """Xu ly khi xuat xong"""
        self.btn_export.setEnabled(True)
        self.label_export_status.setText("Hoan tat!")
        self.label_status.setText(f"Da xuat: {output_path}")

        QMessageBox.information(
            self, "Thanh Cong",
            f"Video da duoc xuat thanh cong!\n\nFile: {output_path}"
        )

        # Open folder
        folder = str(Path(output_path).parent)
        os.startfile(folder)

    def _on_export_error(self, error: str):
        """Xu ly loi xuat"""
        self.btn_export.setEnabled(True)
        self.label_export_status.setText(f"Loi: {error}")
        QMessageBox.critical(self, "Loi", f"Khong the xuat video:\n{error}")

    def _save_api_keys(self):
        """Luu API keys"""
        settings_file = Path(__file__).parent.parent.parent / "settings.json"

        import json
        settings = {
            "groq_api_key": self.input_groq_key.text().strip(),
            "assemblyai_api_key": self.input_assembly_key.text().strip(),
            "gemini_api_key": self.input_gemini_key.text().strip()
        }

        try:
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            QMessageBox.information(self, "Thanh Cong", "Da luu API keys!")
        except Exception as e:
            QMessageBox.critical(self, "Loi", f"Khong the luu settings: {e}")

    def _load_settings(self):
        """Load settings da luu"""
        settings_file = Path(__file__).parent.parent.parent / "settings.json"

        if not settings_file.exists():
            return

        import json
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)

            self.input_groq_key.setText(settings.get("groq_api_key", ""))
            self.input_assembly_key.setText(settings.get("assemblyai_api_key", ""))
            self.input_gemini_key.setText(settings.get("gemini_api_key", ""))
        except:
            pass
