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
    QFileDialog, QMessageBox, QSlider,
    QFrame, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEvent
from PyQt6.QtGui import QFont, QIcon

from src.ui.styles import DARK_STYLE
from src.workers.async_workers import (
    ExtractWorker, TranscribeWorker, TranslateWorker,
    TTSWorker, ExportWorker, TurboTranscribeWorker, TurboTTSWorker
)
from src.core.intro_generator import IntroGenerator


class NoScrollComboBox(QComboBox):
    """ComboBox khong thay doi khi scroll chuot"""
    def wheelEvent(self, event):
        # Bo qua scroll event, chuyen cho parent xu ly
        event.ignore()


class NoScrollSlider(QSlider):
    """Slider khong thay doi khi scroll chuot"""
    def wheelEvent(self, event):
        # Bo qua scroll event, chuyen cho parent xu ly
        event.ignore()


class MainWindow(QMainWindow):
    """Cua so chinh cua ung dung"""

    # Signals for thread-safe UI updates
    status_update_signal = pyqtSignal(str)
    progress_update_signal = pyqtSignal(int)
    export_finished_signal = pyqtSignal(str)
    export_error_signal = pyqtSignal(str)

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
        self.turbo_mode = False  # TURBO mode TAT MAC DINH - tranh chia qua nhieu chunks

        # Workers
        self.extract_worker = None
        self.transcribe_worker = None
        self.translate_worker = None
        self.tts_worker = None
        self.export_worker = None

        # Intro generator
        self.intro_generator = IntroGenerator()

        self._init_ui()

        # Connect signals for thread-safe UI updates
        self.status_update_signal.connect(self._update_status_slot)
        self.progress_update_signal.connect(self._update_progress_slot)
        self.export_finished_signal.connect(self._on_export_finished)
        self.export_error_signal.connect(self._on_export_error)

    def _update_status_slot(self, text: str):
        """Slot to update export status label"""
        self.label_export_status.setText(text)

    def _update_progress_slot(self, value: int):
        """Slot to update export progress bar"""
        self.progress_export.setValue(value)

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
        """Tao tab xu ly chinh - tat ca cac buoc trong 1 panel cuon"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Single panel with all steps
        panel = self._create_workflow_panel()
        main_layout.addWidget(panel)

        return tab

    def _create_workflow_panel(self) -> QWidget:
        """Panel chua tat ca cac buoc xu ly voi scroll chung"""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # Scroll area cho tat ca noi dung
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #2d2d2d;
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                border-radius: 6px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: #2d2d2d;
            }
        """)

        # Container widget cho tat ca noi dung
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content.setObjectName("scrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 20, 10)  # Extra right margin for scrollbar
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Style chung cho tat ca GroupBox
        groupbox_style = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 12px;
                padding: 15px 10px 10px 10px;
                background: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 8px;
                color: #00d4ff;
                background: #252525;
            }
        """

        # === NHAP VIDEO ===
        video_group = QGroupBox("Nhap Video")
        video_group.setStyleSheet(groupbox_style)
        video_layout = QVBoxLayout(video_group)
        video_layout.setSpacing(10)
        video_layout.setContentsMargins(10, 15, 10, 10)

        # Video input row
        video_row = QHBoxLayout()
        video_row.setSpacing(10)
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Chon file video hoac nhap URL...")
        self.video_input.setStyleSheet("padding: 10px; border-radius: 5px;")
        video_row.addWidget(self.video_input, 1)

        btn_browse = QPushButton("Chon File")
        btn_browse.setFixedHeight(40)
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
        video_row.addWidget(btn_browse)
        video_layout.addLayout(video_row)

        layout.addWidget(video_group)

        # === BUOC 1: TRICH XUAT AUDIO ===
        step1 = QGroupBox("Buoc 1: Trich xuat audio")
        step1.setStyleSheet(groupbox_style)
        step1_layout = QVBoxLayout(step1)
        step1_layout.setSpacing(10)
        step1_layout.setContentsMargins(10, 15, 10, 10)

        self.btn_extract = QPushButton("Trich Xuat Audio")
        self.btn_extract.setFixedHeight(40)
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
        self.progress_extract.setFixedHeight(20)
        self.progress_extract.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
            }
            QProgressBar::chunk { background: #198754; border-radius: 5px; }
        """)
        step1_layout.addWidget(self.progress_extract)

        self.label_extract_status = QLabel("San sang")
        self.label_extract_status.setStyleSheet("""
            color: #81c784;
            font-size: 11px;
            background: #1a2e1a;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 5px;
        """)
        step1_layout.addWidget(self.label_extract_status)

        layout.addWidget(step1)

        # === BUOC 2: CHUYEN GIONG NOI THANH VAN BAN ===
        step2 = QGroupBox("Buoc 2: Chuyen giong noi thanh van ban")
        step2.setStyleSheet(groupbox_style)
        step2_layout = QVBoxLayout(step2)
        step2_layout.setSpacing(8)
        step2_layout.setContentsMargins(15, 20, 15, 10)

        # STT Engine selection
        stt_row = QHBoxLayout()
        stt_row.setSpacing(10)
        lbl_stt_engine = QLabel("Engine:")
        lbl_stt_engine.setFixedWidth(55)
        stt_row.addWidget(lbl_stt_engine)
        self.combo_stt = NoScrollComboBox()
        self.combo_stt.addItems(["Groq (Whisper)", "AssemblyAI", "Local Whisper"])
        self.combo_stt.setFixedHeight(32)
        self.combo_stt.setStyleSheet("padding: 5px;")
        stt_row.addWidget(self.combo_stt, 1)
        step2_layout.addLayout(stt_row)

        self.btn_transcribe = QPushButton("Chuyen Thanh Van Ban")
        self.btn_transcribe.setFixedHeight(38)
        self.btn_transcribe.setStyleSheet("""
            QPushButton {
                background: #6f42c1;
                color: white;
                padding: 8px;
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
        self.progress_transcribe.setFixedHeight(15)
        self.progress_transcribe.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
            }
            QProgressBar::chunk { background: #6f42c1; border-radius: 5px; }
        """)
        step2_layout.addWidget(self.progress_transcribe)

        self.label_transcribe_status = QLabel("Cho trich xuat audio")
        self.label_transcribe_status.setStyleSheet("""
            color: #4fc3f7;
            font-size: 11px;
            background: #1a1a2e;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 5px;
        """)
        self.label_transcribe_status.setWordWrap(True)
        step2_layout.addWidget(self.label_transcribe_status)

        layout.addWidget(step2)

        # Original text
        text_group = QGroupBox("Van ban goc (Tieng Trung)")
        text_group.setStyleSheet(groupbox_style)
        text_layout = QVBoxLayout(text_group)
        text_layout.setSpacing(15)
        text_layout.setContentsMargins(10, 10, 10, 10)

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

        # Step 3: Translate
        step3 = QGroupBox("Buoc 3: Dich sang tieng Viet")
        step3.setStyleSheet(groupbox_style)
        step3_layout = QVBoxLayout(step3)
        step3_layout.setSpacing(15)
        step3_layout.setContentsMargins(10, 10, 10, 10)

        self.btn_translate = QPushButton("Dich Van Ban")
        self.btn_translate.setFixedHeight(40)
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
        self.progress_translate.setFixedHeight(20)
        self.progress_translate.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
            }
            QProgressBar::chunk { background: #fd7e14; border-radius: 5px; }
        """)
        step3_layout.addWidget(self.progress_translate)

        self.label_translate_status = QLabel("Cho chuyen thanh van ban")
        self.label_translate_status.setStyleSheet("""
            color: #ffb74d;
            font-size: 11px;
            background: #2e2a1a;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 5px;
        """)
        step3_layout.addWidget(self.label_translate_status)

        layout.addWidget(step3)

        # Translated text
        text_group2 = QGroupBox("Van ban dich (Tieng Viet)")
        text_group2.setStyleSheet(groupbox_style)
        text_layout2 = QVBoxLayout(text_group2)
        text_layout2.setSpacing(15)
        text_layout2.setContentsMargins(10, 15, 10, 10)

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
        self.text_translated.setMinimumHeight(120)
        text_layout2.addWidget(self.text_translated)

        layout.addWidget(text_group2)

        # Step 4: TTS
        step4 = QGroupBox("Buoc 4: Tao giong noi")
        step4.setStyleSheet(groupbox_style)
        step4_layout = QVBoxLayout(step4)
        step4_layout.setSpacing(12)
        step4_layout.setContentsMargins(10, 15, 10, 10)

        # TTS Engine
        tts_row = QHBoxLayout()
        tts_row.setSpacing(15)
        lbl_engine = QLabel("Engine:")
        lbl_engine.setFixedSize(70, 35)
        tts_row.addWidget(lbl_engine)
        self.combo_tts = NoScrollComboBox()
        self.combo_tts.addItems(["Gemini TTS", "Edge TTS"])
        self.combo_tts.setFixedHeight(35)
        self.combo_tts.setStyleSheet("""
            QComboBox {
                padding: 8px;
                background: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background: #2d2d2d;
                border: 1px solid #444;
                selection-background-color: #0d6efd;
            }
        """)
        self.combo_tts.currentIndexChanged.connect(self._on_tts_engine_changed)
        tts_row.addWidget(self.combo_tts, 1)
        step4_layout.addLayout(tts_row)

        # Voice selection
        voice_row = QHBoxLayout()
        voice_row.setSpacing(15)
        lbl_voice = QLabel("Giong:")
        lbl_voice.setFixedSize(70, 35)
        voice_row.addWidget(lbl_voice)
        self.combo_voice = NoScrollComboBox()
        self.combo_voice.setFixedHeight(35)
        self.combo_voice.setStyleSheet("""
            QComboBox {
                padding: 8px;
                background: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background: #2d2d2d;
                border: 1px solid #444;
                selection-background-color: #0d6efd;
            }
        """)
        self._update_voice_list()
        voice_row.addWidget(self.combo_voice, 1)
        step4_layout.addLayout(voice_row)

        # Speed control
        speed_row = QHBoxLayout()
        speed_row.setSpacing(15)
        lbl_speed = QLabel("Toc do:")
        lbl_speed.setFixedSize(70, 35)
        speed_row.addWidget(lbl_speed)
        self.slider_speed = NoScrollSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setFixedHeight(35)
        self.slider_speed.setMinimum(50)
        self.slider_speed.setMaximum(200)
        self.slider_speed.setValue(100)
        self.slider_speed.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_speed.setTickInterval(25)
        speed_row.addWidget(self.slider_speed, 1)
        self.label_speed = QLabel("1.0x")
        self.label_speed.setFixedSize(50, 35)
        speed_row.addWidget(self.label_speed)
        self.slider_speed.valueChanged.connect(
            lambda v: self.label_speed.setText(f"{v/100:.1f}x")
        )
        step4_layout.addLayout(speed_row)

        self.btn_tts = QPushButton("Tao Giong Noi")
        self.btn_tts.setFixedHeight(40)
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
        self.progress_tts.setFixedHeight(20)
        self.progress_tts.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
            }
            QProgressBar::chunk { background: #dc3545; border-radius: 5px; }
        """)
        step4_layout.addWidget(self.progress_tts)

        self.label_tts_status = QLabel("Cho dich van ban")
        self.label_tts_status.setStyleSheet("""
            color: #f48fb1;
            font-size: 11px;
            background: #2e1a2a;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 5px;
        """)
        self.label_tts_status.setWordWrap(True)
        step4_layout.addWidget(self.label_tts_status)

        layout.addWidget(step4)

        # Intro Video Section (truoc buoc xuat video)
        intro_group = QGroupBox("Intro Video")
        intro_group.setStyleSheet(groupbox_style)
        intro_layout = QVBoxLayout(intro_group)
        intro_layout.setSpacing(15)
        intro_layout.setContentsMargins(10, 15, 10, 10)

        # Enable intro checkbox
        self.check_enable_intro = QCheckBox("Them intro vao dau video")
        self.check_enable_intro.stateChanged.connect(self._on_intro_toggled)
        intro_layout.addWidget(self.check_enable_intro)

        # Intro text input
        intro_text_label = QLabel("Noi dung intro (text se duoc doc bang TTS):")
        intro_text_label.setStyleSheet("color: #888; font-size: 11px;")
        intro_layout.addWidget(intro_text_label)

        self.text_intro = QTextEdit()
        self.text_intro.setPlaceholderText("Nhap text cho intro (se duoc doc bang giong AI)")
        self.text_intro.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.text_intro.setMinimumHeight(80)
        self.text_intro.setEnabled(False)
        self.text_intro.textChanged.connect(self._on_intro_text_changed)
        intro_layout.addWidget(self.text_intro)

        # Duration label
        self.label_intro_duration = QLabel("Do dai intro: 0.0s (Min: 3s, Max: 30s)")
        self.label_intro_duration.setStyleSheet("color: #00d4ff; font-weight: bold;")
        intro_layout.addWidget(self.label_intro_duration)

        layout.addWidget(intro_group)

        # Step 5: Export (cuoi cung)
        step5 = QGroupBox("Buoc 5: Xuat video")
        step5.setStyleSheet(groupbox_style)
        step5_layout = QVBoxLayout(step5)
        step5_layout.setSpacing(12)
        step5_layout.setContentsMargins(10, 15, 10, 10)

        # Output folder
        folder_row = QHBoxLayout()
        folder_row.setSpacing(15)
        lbl_folder = QLabel("Thu muc:")
        lbl_folder.setFixedWidth(70)
        folder_row.addWidget(lbl_folder)
        self.input_output_folder = QLineEdit()
        self.input_output_folder.setFixedHeight(35)
        self.input_output_folder.setPlaceholderText("Chon thu muc luu file...")
        self.input_output_folder.setStyleSheet("padding: 8px;")
        self.input_output_folder.setReadOnly(True)
        # Mac dinh la thu muc Downloads
        self.input_output_folder.setText(str(Path.home() / "Downloads"))
        folder_row.addWidget(self.input_output_folder, 1)
        self.btn_browse_folder = QPushButton("Chon...")
        self.btn_browse_folder.setFixedHeight(35)
        self.btn_browse_folder.setFixedWidth(80)
        self.btn_browse_folder.setStyleSheet("""
            QPushButton {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #4d4d4d;
            }
        """)
        self.btn_browse_folder.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(self.btn_browse_folder)
        step5_layout.addLayout(folder_row)

        # Output name
        name_row = QHBoxLayout()
        name_row.setSpacing(15)
        lbl_filename = QLabel("Ten file:")
        lbl_filename.setFixedWidth(70)
        name_row.addWidget(lbl_filename)
        self.input_output_name = QLineEdit()
        self.input_output_name.setFixedHeight(35)
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
        self.btn_export.setFixedHeight(40)
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
        self.progress_export.setFixedHeight(20)
        self.progress_export.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #2d2d2d;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 5px;
            }
        """)
        step5_layout.addWidget(self.progress_export)

        self.label_export_status = QLabel("Cho tao giong noi")
        self.label_export_status.setStyleSheet("""
            color: #80deea;
            font-size: 11px;
            background: #1a2e2e;
            padding: 4px 8px;
            border-radius: 4px;
            margin-top: 5px;
        """)
        self.label_export_status.setWordWrap(True)
        step5_layout.addWidget(self.label_export_status)

        layout.addWidget(step5)

        # Spacer cuoi cung
        layout.addSpacing(20)

        # Set content vao scroll area
        scroll.setWidget(content)

        # Add scroll vao panel
        panel_layout.addWidget(scroll)

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
        self.check_ac_remove_text = QCheckBox("Cat phan text (10% duoi - Xoa chu Trung)")
        self.check_ac_remove_watermark = QCheckBox("Cat watermark (5% tren + 5% duoi)")
        self.check_ac_remove_metadata = QCheckBox("Xoa metadata ban quyen (Douyin/TikTok)")

        ac_layout.addWidget(self.check_ac_flip)
        ac_layout.addWidget(self.check_ac_zoom)
        ac_layout.addWidget(self.check_ac_effect)
        ac_layout.addWidget(self.check_ac_remove_text)
        ac_layout.addWidget(self.check_ac_remove_watermark)
        ac_layout.addWidget(self.check_ac_remove_metadata)

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
        self.combo_watermark_pos = NoScrollComboBox()
        self.combo_watermark_pos.addItems([
            "Tren-Phai", "Tren-Trai", "Duoi-Phai", "Duoi-Trai"
        ])
        self.combo_watermark_pos.setStyleSheet("padding: 8px;")
        wm_pos_row.addWidget(self.combo_watermark_pos, 1)
        wm_layout.addLayout(wm_pos_row)

        layout.addWidget(wm_group)

        # Language settings - Loc text tieng Trung
        lang_group = QGroupBox("Cai dat ngon ngu")
        lang_layout = QVBoxLayout(lang_group)

        self.check_remove_chinese = QCheckBox("Loc bo tat ca text tieng Trung (Ky tu Han)")
        self.check_remove_chinese.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.check_remove_chinese.setToolTip("Tu dong loai bo tat ca ky tu tieng Trung khoi ket qua STT")
        lang_layout.addWidget(self.check_remove_chinese)

        lang_note = QLabel("Luu y: Chi loai bo ky tu Han (U+4E00-U+9FFF), giu lai cac ky tu khac")
        lang_note.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        lang_note.setWordWrap(True)
        lang_layout.addWidget(lang_note)

        layout.addWidget(lang_group)

        # Performance settings - TOI UU CHO EDGE TTS
        # Edge TTS: Khong co rate limit, dung 10 threads de xu ly NHANH NHAT
        self._use_parallel = True
        self._num_threads = 10
        self._turbo_mode_enabled = True

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

    def _browse_output_folder(self):
        """Mo dialog chon thu muc luu video"""
        current_folder = self.input_output_folder.text().strip()
        if not current_folder:
            # Mac dinh la thu muc Downloads
            current_folder = str(Path.home() / "Downloads")

        folder_path = QFileDialog.getExistingDirectory(
            self, "Chon thu muc luu video",
            current_folder,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder_path:
            self.input_output_folder.setText(folder_path)

    def _filter_chinese_text(self, text: str) -> str:
        """
        Loc bo tat ca ky tu tieng Trung (Han tu) khoi text

        Args:
            text: Van ban can loc

        Returns:
            Van ban da duoc loc bo ky tu Trung
        """
        import re

        # Loai bo tat ca ky tu Han (CJK Unified Ideographs)
        # Range: U+4E00 to U+9FFF (Han tu chinh)
        # Them ca: U+3400-U+4DBF (Extension A), U+F900-U+FAFF (Compatibility)
        filtered = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+', '', text)

        # Loai bo khoang trang thua
        filtered = re.sub(r'\s+', ' ', filtered).strip()

        return filtered

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
            engine_name = "local"

        self.btn_transcribe.setEnabled(False)
        self.progress_transcribe.setValue(0)
        self.label_transcribe_status.setText("Dang xu ly...")

        # === TURBO MODE ===
        if self.turbo_mode:
            # TURBO mode: Use TurboTranscribeWorker (only Groq supported)
            if engine_name != "groq":
                QMessageBox.warning(
                    self, "Loi",
                    "TURBO mode chi ho tro Groq API!\nVui long chon 'Groq (Whisper)' lam engine."
                )
                self.btn_transcribe.setEnabled(True)
                return

            self.label_transcribe_status.setText("[TURBO] Khoi tao...")

            self.transcribe_worker = TurboTranscribeWorker(
                self.audio_path, api_key
            )
            self.transcribe_worker.progress.connect(self.progress_transcribe.setValue)
            self.transcribe_worker.status.connect(self.label_transcribe_status.setText)
            self.transcribe_worker.finished.connect(self._on_transcribe_finished)
            self.transcribe_worker.error.connect(self._on_transcribe_error)

            # Connect turbo-specific signals
            if hasattr(self.transcribe_worker, 'detailed_progress'):
                self.transcribe_worker.detailed_progress.connect(
                    lambda completed, total, msg:
                        self.label_transcribe_status.setText(f"[TURBO] {msg}")
                )

            if hasattr(self.transcribe_worker, 'speedup_info'):
                self.transcribe_worker.speedup_info.connect(
                    lambda time_taken, speedup:
                        self.label_status.setText(
                            f"[TURBO] STT: {time_taken:.1f}s ({speedup:.1f}x faster!)"
                        )
                )

        # === NORMAL MODE ===
        else:
            self.transcribe_worker = TranscribeWorker(
                audio_path=self.audio_path,
                engine=engine_name,
                api_key=api_key,
                model="small"
            )
            self.transcribe_worker.progress.connect(self.progress_transcribe.setValue)
            self.transcribe_worker.status.connect(self.label_transcribe_status.setText)
            self.transcribe_worker.finished.connect(self._on_transcribe_finished)
            self.transcribe_worker.error.connect(self._on_transcribe_error)

        self.transcribe_worker.start()

    def _on_transcribe_finished(self, text: str):
        """Xu ly khi transcribe xong"""
        # Ap dung filter text tieng Trung neu duoc bat
        if hasattr(self, 'check_remove_chinese') and self.check_remove_chinese.isChecked():
            original_length = len(text)
            text = self._filter_chinese_text(text)
            filtered_length = len(text)
            removed_count = original_length - filtered_length
            if removed_count > 0:
                self.label_transcribe_status.setText(f"Hoan tat! (Da loc {removed_count} ky tu Trung)")

        self.original_text = text
        self.text_original.setPlainText(text)
        self.btn_transcribe.setEnabled(True)
        self.btn_translate.setEnabled(True)
        if not hasattr(self, 'check_remove_chinese') or not self.check_remove_chinese.isChecked():
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

        # === TURBO MODE ===
        if self.turbo_mode:
            # TURBO mode: Use TurboTTSWorker (Edge-TTS only for now)
            if "Gemini" in engine:
                QMessageBox.warning(
                    self, "Thong bao",
                    "TURBO mode dang chi ho tro Edge-TTS!\n" +
                    "Gemini TTS se duoc ho tro trong phien ban sau.\n" +
                    "Tu dong chuyen sang Edge-TTS..."
                )
                # Auto-switch to Edge-TTS
                self.combo_tts.setCurrentIndex(1)  # Edge TTS
                voice = self.combo_voice.currentText()

            self.label_tts_status.setText("[TURBO] Khoi tao...")

            self.tts_worker = TurboTTSWorker(text, voice, speed)
            self.tts_worker.progress.connect(self.progress_tts.setValue)
            self.tts_worker.status.connect(self.label_tts_status.setText)
            self.tts_worker.finished.connect(self._on_tts_finished)
            self.tts_worker.error.connect(self._on_tts_error)

            # Connect turbo-specific signals
            if hasattr(self.tts_worker, 'detailed_progress'):
                self.tts_worker.detailed_progress.connect(
                    lambda completed, total, msg:
                        self.label_tts_status.setText(f"[TURBO] {msg}")
                )

            if hasattr(self.tts_worker, 'speedup_info'):
                self.tts_worker.speedup_info.connect(
                    lambda time_taken, speedup:
                        self.label_status.setText(
                            f"[TURBO] TTS: {time_taken:.1f}s ({speedup:.1f}x faster!)"
                        )
                )

        # === NORMAL MODE ===
        else:
            # Use hardcoded parallel processing settings for optimal performance
            use_parallel = self._use_parallel
            num_threads = self._num_threads

            self.tts_worker = TTSWorker(
                text, voice, speed,
                use_parallel=use_parallel,
                num_threads=num_threads
            )
            self.tts_worker.progress.connect(self.progress_tts.setValue)
            self.tts_worker.status.connect(self.label_tts_status.setText)
            self.tts_worker.finished.connect(self._on_tts_finished)
            self.tts_worker.error.connect(self._on_tts_error)

            # Connect detailed progress if available
            if hasattr(self.tts_worker, 'detailed_progress'):
                self.tts_worker.detailed_progress.connect(
                    lambda completed, total, segment_id:
                        self.label_tts_status.setText(f"Dang tao {completed}/{total} segments...")
                )

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
        import logging
        import traceback

        try:
            logging.basicConfig(level=logging.DEBUG)
            logger = logging.getLogger(__name__)

            logger.debug(f"_export_video called")
            logger.debug(f"  video_path: {self.video_path}")
            logger.debug(f"  tts_audio_path: {self.tts_audio_path}")

            # Validate inputs
            if not self.video_path or not self.tts_audio_path:
                QMessageBox.warning(self, "Loi", "Thieu video hoac audio!")
                return

            if not os.path.exists(self.video_path):
                QMessageBox.warning(self, "Loi", f"Video khong ton tai:\n{self.video_path}")
                return

            if not os.path.exists(self.tts_audio_path):
                QMessageBox.warning(self, "Loi", f"Audio khong ton tai:\n{self.tts_audio_path}")
                return

            output_name = self.input_output_name.text().strip()
            if not output_name:
                output_name = "output"

            logger.debug(f"  output_name: {output_name}")

            # Check if intro is enabled
            if self.check_enable_intro.isChecked():
                intro_text = self.text_intro.toPlainText().strip()
                if not intro_text:
                    QMessageBox.warning(self, "Loi", "Vui long nhap noi dung intro!")
                    return
                logger.debug("Exporting with intro...")
                # Generate intro first, then export
                self._export_with_intro(output_name)
            else:
                logger.debug("Exporting without intro...")
                # Normal export without intro
                self._export_without_intro(output_name)

        except Exception as e:
            error_details = f"{str(e)}\n\nChi tiet:\n{traceback.format_exc()}"
            print(f"[ERROR] _export_video failed:\n{error_details}")
            QMessageBox.critical(
                self, "Loi",
                f"Khong the xuat video:\n{str(e)}\n\nVui long kiem tra log de biet them chi tiet."
            )

    def _export_without_intro(self, output_name: str):
        """Xuat video khong co intro"""
        # Get output folder
        output_folder = self.input_output_folder.text().strip()
        if not output_folder:
            output_folder = str(Path.home() / "Downloads")

        # Build options
        anti_copyright = None
        if self.check_anti_copyright.isChecked():
            anti_copyright = {
                "flip": self.check_ac_flip.isChecked(),
                "zoom": self.check_ac_zoom.isChecked(),
                "effect": self.check_ac_effect.isChecked(),
                "remove_text": self.check_ac_remove_text.isChecked(),
                "remove_watermark": self.check_ac_remove_watermark.isChecked(),
                "remove_metadata": self.check_ac_remove_metadata.isChecked()
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
            watermark=watermark,
            output_folder=output_folder
        )
        self.export_worker.progress.connect(self.progress_export.setValue)
        self.export_worker.status.connect(self.label_export_status.setText)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.error.connect(self._on_export_error)
        self.export_worker.start()

    def _export_with_intro(self, output_name: str):
        """Xuat video co intro"""
        import threading

        # Get output folder
        output_folder = self.input_output_folder.text().strip()
        if not output_folder:
            output_folder = str(Path.home() / "Downloads")

        self.btn_export.setEnabled(False)
        self.progress_export.setValue(0)
        self.label_export_status.setText("Dang tao intro...")

        # Helper functions for thread-safe UI updates
        def update_status(text):
            self.status_update_signal.emit(text)

        def update_progress(value):
            self.progress_update_signal.emit(value)

        def generate_intro_thread():
            try:
                intro_text = self.text_intro.toPlainText().strip()

                # Ap dung filter text tieng Trung neu duoc bat
                if hasattr(self, 'check_remove_chinese') and self.check_remove_chinese.isChecked():
                    intro_text = self._filter_chinese_text(intro_text)
                    update_status(f"Dang tao intro (da loc text Trung)...")

                temp_dir = "temp"
                os.makedirs(temp_dir, exist_ok=True)

                # Get voice and speed settings from UI
                voice = self.combo_voice.currentText()
                speed = self.slider_speed.value() / 100.0

                # Step 1: Generate intro video WITH TTS audio
                update_status("Dang tao intro video voi TTS audio...")
                update_progress(20)

                intro_path = os.path.join(temp_dir, "intro.mp4")
                success = self.intro_generator.generate_intro(
                    self.video_path,
                    intro_text,
                    intro_path,
                    temp_dir,
                    voice=voice,
                    speed=speed,
                    progress_callback=update_progress
                )

                if not success:
                    raise Exception("Khong the tao intro video")

                # Step 2: Export main video with new audio first
                update_status("Dang xuat video chinh...")
                update_progress(40)

                # Build options
                anti_copyright = None
                if self.check_anti_copyright.isChecked():
                    anti_copyright = {
                        "flip": self.check_ac_flip.isChecked(),
                        "zoom": self.check_ac_zoom.isChecked(),
                        "effect": self.check_ac_effect.isChecked(),
                        "remove_text": self.check_ac_remove_text.isChecked(),
                        "remove_watermark": self.check_ac_remove_watermark.isChecked(),
                        "remove_metadata": self.check_ac_remove_metadata.isChecked()
                    }

                watermark = None
                if self.check_watermark.isChecked():
                    watermark = {
                        "enabled": True,
                        "text": self.input_watermark.text().strip(),
                        "position": self.combo_watermark_pos.currentText()
                    }

                # Export main video to temp file
                main_video_temp = os.path.join(temp_dir, f"{output_name}_main.mp4")

                # Use VideoMerger synchronously (we're already in a thread)
                from src.core.video_merger import VideoMerger
                merger = VideoMerger(output_dir=Path(temp_dir))

                # FIX: Use merge() not merge_video() - that method doesn't exist!
                merger.merge(
                    video_path=self.video_path,
                    audio_path=self.tts_audio_path,
                    output_name=f"{output_name}_main",
                    mix_original=self.check_mix_audio.isChecked(),
                    anti_copyright=anti_copyright,
                    watermark=watermark
                )

                # Step 3: Merge intro with main video
                update_status("Dang ket hop intro + video...")
                update_progress(70)

                # Use output_folder from user selection
                output_path = os.path.join(output_folder, f"{output_name}.mp4")
                os.makedirs(output_folder, exist_ok=True)

                success = self.intro_generator.merge_intro_with_main(
                    intro_path,
                    main_video_temp,
                    output_path,
                    temp_dir
                )

                if not success:
                    raise Exception("Khong the ket hop intro voi video")

                # Cleanup temp files
                if os.path.exists(intro_path):
                    os.remove(intro_path)
                if os.path.exists(main_video_temp):
                    os.remove(main_video_temp)

                # Success - use thread-safe callback
                update_progress(100)
                update_status("Hoan tat!")

                # Call finished handler in main thread
                self.export_finished_signal.emit(output_path)

            except Exception as e:
                import traceback
                error_details = f"{str(e)}\n\nChi tiet:\n{traceback.format_exc()}"
                print(f"[ERROR] Export with intro failed:\n{error_details}")

                # Call error handler in main thread
                self.export_error_signal.emit(error_details)

        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=generate_intro_thread)
        thread.start()

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

    def _get_settings_path(self) -> Path:
        """Lay duong dan file settings.json"""
        # Thu muc goc cua project (noi chua main.py)
        import sys
        if getattr(sys, 'frozen', False):
            # Neu chay tu file .exe
            base_dir = Path(sys.executable).parent
        else:
            # Neu chay tu Python script
            base_dir = Path(__file__).parent.parent.parent
        return base_dir / "settings.json"

    def _save_api_keys(self):
        """Luu API keys va settings"""
        settings_file = self._get_settings_path()

        import json
        settings = {
            "groq_api_key": self.input_groq_key.text().strip(),
            "assemblyai_api_key": self.input_assembly_key.text().strip(),
            "gemini_api_key": self.input_gemini_key.text().strip(),
            "remove_chinese_text": self.check_remove_chinese.isChecked() if hasattr(self, 'check_remove_chinese') else False
        }

        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            print(f"[Settings] Saved to: {settings_file}")
            QMessageBox.information(self, "Thanh Cong", "Da luu cai dat!")
        except Exception as e:
            print(f"[Settings] Error saving: {e}")
            QMessageBox.critical(self, "Loi", f"Khong the luu settings: {e}")

    def _load_settings(self):
        """Load settings da luu"""
        settings_file = self._get_settings_path()

        print(f"[Settings] Loading from: {settings_file}")
        print(f"[Settings] File exists: {settings_file.exists()}")

        if not settings_file.exists():
            print("[Settings] File not found, skipping")
            return

        import json
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)

            groq_key = settings.get("groq_api_key", "")
            assembly_key = settings.get("assemblyai_api_key", "")
            gemini_key = settings.get("gemini_api_key", "")
            remove_chinese = settings.get("remove_chinese_text", False)

            self.input_groq_key.setText(groq_key)
            self.input_assembly_key.setText(assembly_key)
            self.input_gemini_key.setText(gemini_key)

            # Load checkbox state
            if hasattr(self, 'check_remove_chinese'):
                self.check_remove_chinese.setChecked(remove_chinese)

            print(f"[Settings] Loaded: groq={len(groq_key)>0}, assembly={len(assembly_key)>0}, gemini={len(gemini_key)>0}, remove_chinese={remove_chinese}")
        except Exception as e:
            print(f"[Settings] Error loading: {e}")

    def _on_intro_toggled(self, state):
        """Xu ly khi checkbox intro duoc bat/tat"""
        enabled = state == Qt.CheckState.Checked.value
        self.text_intro.setEnabled(enabled)
        if not enabled:
            self.label_intro_duration.setText("Do dai intro: 0.0s (Min: 3s, Max: 30s)")

    def _on_intro_text_changed(self):
        """Xu ly khi text intro thay doi - cap nhat do dai intro"""
        if not self.check_enable_intro.isChecked():
            return

        text = self.text_intro.toPlainText()
        duration = self.intro_generator.calculate_intro_duration(text)
        self.label_intro_duration.setText(
            f"Do dai intro: {duration:.1f}s (Min: 3s, Max: 30s)"
        )

