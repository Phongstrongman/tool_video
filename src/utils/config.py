"""
Configuration for DouyinVoice Pro Client

Central configuration file for server URLs and settings
"""
import os

# Server URL - LOCAL DEVELOPMENT MODE
# Production server (uncomment when ready):
# SERVER_URL = os.getenv("SERVER_URL", "https://toolvideo-production.up.railway.app")

# Local development server (currently active):
SERVER_URL = "http://localhost:8000"

# Application settings
APP_NAME = "DouyinVoice Pro"
APP_VERSION = "3.0"

# Temp and output directories
TEMP_DIR = "temp"
OUTPUT_DIR = "output"
