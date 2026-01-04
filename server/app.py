"""
DouyinVoice Pro - License Server API

FastAPI server that:
1. Validates license keys
2. Proxies API calls to Groq (STT), Gemini (TTS), Translation
3. Protects API keys (stored server-side only)
4. Checks license on every request

Run:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime
import uuid

# Import server modules
from database import Database
from config import (
    GROQ_API_KEY, GEMINI_API_KEY, SERVER_SECRET_KEY,
    CORS_ORIGINS, LOG_LEVEL, print_config, TIERS
)

# Import API clients
from groq import Groq
import google.generativeai as genai
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="DouyinVoice Pro API",
    description="License server and API proxy for DouyinVoice Pro",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = Database()

# Initialize API clients
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ===== Pydantic Models =====

class LoginRequest(BaseModel):
    license_key: str
    machine_id: Optional[str] = None


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str
    license_data: Optional[dict] = None


class SpeechToTextRequest(BaseModel):
    audio_path: str  # Path on client side (will upload content)
    language: str = "zh"  # Default Chinese
    model: str = "whisper-large-v3"


class SpeechToTextResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    message: str


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "vi-VN-HoaiMyNeural"  # Vietnamese voice
    rate: float = 1.0


class TextToSpeechResponse(BaseModel):
    success: bool
    audio_content: Optional[bytes] = None
    message: str


class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "zh-CN"
    target_lang: str = "vi"


class TranslateResponse(BaseModel):
    success: bool
    translated_text: Optional[str] = None
    message: str


# ===== Dependency: Verify Token =====

async def verify_token_header(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> tuple:
    """
    Verify token from Authorization header and track IP usage

    Returns:
        tuple (license_key, license_data) if valid

    Raises:
        HTTPException if invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    # Verify token with database
    is_valid, license_key = db.verify_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify license is still valid
    valid, message, license_data = db.verify_license(license_key)
    if not valid:
        raise HTTPException(status_code=403, detail=f"License invalid: {message}")

    # Extract IP address
    client_ip = request.client.host if request.client else "unknown"

    # Check for proxy headers
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]

    # Track IP usage and detect suspicious activity
    is_suspicious, sus_message = db.track_ip_usage(license_key, client_ip)

    if is_suspicious:
        logger.warning(f"SUSPICIOUS ACTIVITY: {license_key} - {sus_message} (IP: {client_ip})")

    logger.info(f"Request from license: {license_key} (tier: {license_data.get('tier', 'basic')}, IP: {client_ip})")
    return license_key, license_data


# ===== API Endpoints =====

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DouyinVoice Pro API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "login": "POST /api/login",
            "speech_to_text": "POST /api/speech-to-text",
            "text_to_speech": "POST /api/text-to-speech",
            "translate": "POST /api/translate"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "ok",
        "groq_api": "configured" if GROQ_API_KEY != "your_groq_api_key_here" else "not_set",
        "gemini_api": "configured" if GEMINI_API_KEY != "your_gemini_api_key_here" else "not_set"
    }


@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with license key

    Returns JWT token if valid
    """
    logger.info(f"Login attempt: {request.license_key}")

    # Verify license
    is_valid, message, license_data = db.verify_license(
        request.license_key,
        request.machine_id
    )

    if not is_valid:
        logger.warning(f"Login failed: {message}")
        return LoginResponse(
            success=False,
            message=message
        )

    # Create session and get token
    token = db.create_session(request.license_key, request.machine_id)

    if not token:
        logger.error(f"Failed to create session for {request.license_key}")
        return LoginResponse(
            success=False,
            message="Không thể tạo session. Vui lòng thử lại."
        )

    logger.info(f"Login successful: {request.license_key}")
    return LoginResponse(
        success=True,
        token=token,
        message=message,
        license_data=license_data
    )


@app.post("/api/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = "zh",
    auth_data: tuple = Depends(verify_token_header)
):
    """
    Speech-to-Text using Groq API

    Requires valid token in Authorization header
    Tracks video usage per tier
    """
    license_key, license_data = auth_data
    tier = license_data.get("tier", "basic")

    logger.info(f"STT request from {license_key} (tier: {tier})")

    # Check usage limit before processing
    monthly_limit = license_data.get("monthly_limit", 100)
    videos_used = license_data.get("videos_used", 0)

    if monthly_limit > 0 and videos_used >= monthly_limit:
        logger.warning(f"License {license_key} exceeded monthly limit ({videos_used}/{monthly_limit})")
        raise HTTPException(
            status_code=403,
            detail=f"Đã hết quota tháng này ({videos_used}/{monthly_limit}). Vui lòng nâng cấp gói hoặc chờ reset."
        )

    try:
        # Get tier-based API key
        tier_config = TIERS.get(tier, TIERS["basic"])
        tier_groq_key = tier_config["groq_api_key"]

        # Initialize tier-specific Groq client
        tier_groq_client = Groq(api_key=tier_groq_key)

        # Read audio file
        audio_content = await file.read()

        # Save temporarily
        temp_file = f"/tmp/audio_{uuid.uuid4()}.wav"
        with open(temp_file, "wb") as f:
            f.write(audio_content)

        # Call Groq API with tier-specific key
        with open(temp_file, "rb") as audio_file:
            transcription = tier_groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                language=language
            )

        # Clean up
        import os
        os.remove(temp_file)

        # Increment video usage
        success, usage_msg = db.increment_video_usage(license_key)
        if success:
            logger.info(f"Usage incremented: {usage_msg}")
        else:
            logger.warning(f"Usage increment failed: {usage_msg}")

        logger.info(f"STT success for {license_key} ({tier})")
        return {
            "success": True,
            "text": transcription.text,
            "message": "Trích text thành công",
            "usage": usage_msg
        }

    except Exception as e:
        logger.error(f"STT error for {license_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi STT: {str(e)}")


@app.post("/api/text-to-speech")
async def text_to_speech(
    request: TextToSpeechRequest,
    license_key: str = Depends(verify_token_header)
):
    """
    Text-to-Speech using Gemini API

    Requires valid token in Authorization header
    """
    logger.info(f"TTS request from {license_key}")

    try:
        # Use Gemini for TTS
        model = genai.GenerativeModel('gemini-pro')

        # Note: Gemini doesn't have native TTS, we'll use a workaround
        # In production, you might want to use Google Cloud TTS instead
        # For now, return a message
        raise HTTPException(
            status_code=501,
            detail="TTS via Gemini not implemented. Use Edge TTS client-side."
        )

    except Exception as e:
        logger.error(f"TTS error for {license_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi TTS: {str(e)}")


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(
    request: TranslateRequest,
    auth_data: tuple = Depends(verify_token_header)
):
    """
    Translate text

    Requires valid token in Authorization header
    """
    license_key, license_data = auth_data
    tier = license_data.get("tier", "basic")

    logger.info(f"Translate request from {license_key} (tier: {tier})")

    try:
        # Use Google Translator (free)
        translator = GoogleTranslator(source=request.source_lang, target=request.target_lang)
        translated = translator.translate(request.text)

        logger.info(f"Translation success for {license_key}")
        return TranslateResponse(
            success=True,
            translated_text=translated,
            message="Dịch thành công"
        )

    except Exception as e:
        logger.error(f"Translation error for {license_key}: {str(e)}")
        return TranslateResponse(
            success=False,
            message=f"Lỗi dịch: {str(e)}"
        )


@app.get("/api/usage")
async def get_usage(auth_data: tuple = Depends(verify_token_header)):
    """
    Get current usage information

    Returns remaining videos, tier info, reset date
    """
    license_key, license_data = auth_data

    usage_info = db.get_usage_info(license_key)
    if not usage_info:
        raise HTTPException(status_code=404, detail="License not found")

    tier = usage_info.get("tier", "basic")
    tier_config = TIERS.get(tier, TIERS["basic"])

    return {
        "success": True,
        "tier": tier,
        "tier_name": tier_config["name"],
        "monthly_limit": usage_info["monthly_limit"],
        "videos_used": usage_info["videos_used"],
        "videos_remaining": usage_info["videos_remaining"],
        "reset_date": usage_info["reset_date"],
        "price": tier_config["price"]
    }


@app.post("/api/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token to logout")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid scheme")

        # Delete session
        deleted = db.delete_session(token)
        if deleted:
            return {"success": True, "message": "Đăng xuất thành công"}
        else:
            return {"success": False, "message": "Token không tồn tại"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== Admin Endpoints (Optional - protect with admin key) =====

@app.get("/admin/licenses")
async def list_licenses(admin_key: str):
    """List all licenses (admin only)"""
    if admin_key != SERVER_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    licenses = db.list_licenses()
    return {"licenses": licenses}


@app.get("/api/admin/suspicious")
async def get_suspicious_licenses(admin_key: str = None):
    """
    Get list of licenses with suspicious activity

    Detection rules:
    - IP changes > 5 times in 24 hours
    - Usage > 50 videos in one day
    - Machine ID mismatch (handled separately)

    Query params:
        admin_key: Server admin key for authentication
    """
    if admin_key != SERVER_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    suspicious = db.get_suspicious_licenses()

    return {
        "success": True,
        "count": len(suspicious),
        "suspicious_licenses": suspicious,
        "message": f"Found {len(suspicious)} suspicious license(s)"
    }


@app.post("/api/admin/clear-suspicious/{license_key}")
async def clear_suspicious_flag(license_key: str, admin_key: str):
    """Clear suspicious flag from a license (admin only)"""
    if admin_key != SERVER_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    success = db.clear_suspicious_flag(license_key)

    if success:
        return {
            "success": True,
            "message": f"Cleared suspicious flag for {license_key}"
        }
    else:
        raise HTTPException(status_code=404, detail="License not found")


# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """Run on server startup"""
    print_config()
    logger.info("DouyinVoice Pro API server started")


# ===== Run Server =====

if __name__ == "__main__":
    import os
    import uvicorn
    from config import LOG_LEVEL

    print_config()

    # Railway sets PORT via environment variable
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(app, host="0.0.0.0", port=port, log_level=LOG_LEVEL.lower())
