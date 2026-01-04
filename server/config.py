"""
Server configuration

IMPORTANT: Set these environment variables in production!
- GROQ_API_KEY
- GEMINI_API_KEY
- SERVER_SECRET_KEY (for JWT token signing)
"""
import sys
import io

# FIX ENCODING FOR WINDOWS
if sys.platform == 'win32':
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# API Keys - Tier-based (MUST be set via environment variables in production)
GROQ_API_KEY_BASIC = os.getenv("GROQ_API_KEY_BASIC", "your_groq_api_key_here")
GEMINI_API_KEY_BASIC = os.getenv("GEMINI_API_KEY_BASIC", "your_gemini_api_key_here")

GROQ_API_KEY_PRO = os.getenv("GROQ_API_KEY_PRO", GROQ_API_KEY_BASIC)
GEMINI_API_KEY_PRO = os.getenv("GEMINI_API_KEY_PRO", GEMINI_API_KEY_BASIC)

GROQ_API_KEY_VIP = os.getenv("GROQ_API_KEY_VIP", GROQ_API_KEY_BASIC)
GEMINI_API_KEY_VIP = os.getenv("GEMINI_API_KEY_VIP", GEMINI_API_KEY_BASIC)

# Legacy support (backward compatibility)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", GROQ_API_KEY_BASIC)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY_BASIC)

# Server secret key for JWT token signing
SERVER_SECRET_KEY = os.getenv("SERVER_SECRET_KEY", "change-this-secret-key-in-production")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "licenses.db")

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# CORS settings (allow client to connect)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))

# License settings
DEFAULT_LICENSE_DURATION_DAYS = int(os.getenv("DEFAULT_LICENSE_DURATION_DAYS", 30))

# Tier configurations
TIERS = {
    "basic": {
        "name": "Basic",
        "price": 50000,  # 50k VND
        "monthly_limit": 100,
        "groq_api_key": GROQ_API_KEY_BASIC,
        "gemini_api_key": GEMINI_API_KEY_BASIC,
        "priority": "normal"
    },
    "pro": {
        "name": "Pro",
        "price": 150000,  # 150k VND
        "monthly_limit": 500,
        "groq_api_key": GROQ_API_KEY_PRO,
        "gemini_api_key": GEMINI_API_KEY_PRO,
        "priority": "high"
    },
    "vip": {
        "name": "VIP",
        "price": 300000,  # 300k VND
        "monthly_limit": -1,  # unlimited
        "groq_api_key": GROQ_API_KEY_VIP,
        "gemini_api_key": GEMINI_API_KEY_VIP,
        "priority": "highest"
    }
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def validate_config():
    """Validate configuration"""
    errors = []

    if GROQ_API_KEY_BASIC == "your_groq_api_key_here":
        errors.append("GROQ_API_KEY_BASIC not set! Set environment variable GROQ_API_KEY_BASIC")

    if GEMINI_API_KEY_BASIC == "your_gemini_api_key_here":
        errors.append("GEMINI_API_KEY_BASIC not set! Set environment variable GEMINI_API_KEY_BASIC")

    if SERVER_SECRET_KEY == "change-this-secret-key-in-production":
        errors.append("WARNING: Using default SERVER_SECRET_KEY. Change in production!")

    # Check tier API keys
    for tier_name, tier_config in TIERS.items():
        if tier_config["groq_api_key"] == "your_groq_api_key_here":
            errors.append(f"WARNING: {tier_name.upper()} tier using default Groq API key")
        if tier_config["gemini_api_key"] == "your_gemini_api_key_here":
            errors.append(f"WARNING: {tier_name.upper()} tier using default Gemini API key")

    return errors

def print_config():
    """Print configuration (without secrets)"""
    print("=" * 60)
    print("SERVER CONFIGURATION")
    print("=" * 60)
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Database: {DATABASE_PATH}")
    print(f"CORS Origins: {CORS_ORIGINS}")
    print(f"Rate Limit: {RATE_LIMIT_PER_MINUTE}/min")
    print(f"Secret Key: {'✅ Set' if SERVER_SECRET_KEY != 'change-this-secret-key-in-production' else '❌ Using default'}")
    print("\n" + "=" * 60)
    print("TIER CONFIGURATIONS")
    print("=" * 60)
    for tier_name, tier_config in TIERS.items():
        groq_set = tier_config["groq_api_key"] != "your_groq_api_key_here"
        gemini_set = tier_config["gemini_api_key"] != "your_gemini_api_key_here"
        print(f"{tier_name.upper()}: {tier_config['name']}")
        print(f"  Price: {tier_config['price']:,} VNĐ")
        print(f"  Monthly Limit: {tier_config['monthly_limit'] if tier_config['monthly_limit'] > 0 else 'Unlimited'}")
        print(f"  Groq API: {'✅ Set' if groq_set else '❌ Not set'}")
        print(f"  Gemini API: {'✅ Set' if gemini_set else '❌ Not set'}")
        print(f"  Priority: {tier_config['priority']}")
        print()
    print("=" * 60)

    # Validate and show errors
    errors = validate_config()
    if errors:
        print("\n⚠️  CONFIGURATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print()
