# 🚀 DouyinVoice Pro - License Server

Server-based license system and API proxy for DouyinVoice Pro.

## 📋 Features

- **License validation** with SQLite database
- **API proxying** for Groq (STT), Gemini (TTS), Translation
- **Token-based authentication** (JWT-like)
- **API keys protected** (server-side only, never exposed to client)
- **License checking** on every API request
- **Cannot be cracked** - no API keys in client

---

## 🛠️ Setup (Local Development)

### 1. Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your API keys:

```env
GROQ_API_KEY=gsk_your_actual_key_here
GEMINI_API_KEY=AIza_your_actual_key_here
SERVER_SECRET_KEY=your-random-secret-key-here
```

### 3. Initialize Database

The database is created automatically on first run.

### 4. Generate Test License

```bash
python generate_license.py generate --days 30 --count 1
```

Output:
```
✅ Created: DVPRO-A1B2-C3D4-E5F6
```

### 5. Run Server

```bash
python app.py
```

Or with uvicorn:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: `http://localhost:8000`

---

## 📡 API Endpoints

### Public Endpoints

#### `GET /`
Root endpoint with API info

#### `GET /health`
Health check

```json
{
  "status": "healthy",
  "timestamp": "2026-01-04T10:00:00",
  "database": "ok",
  "groq_api": "configured",
  "gemini_api": "configured"
}
```

#### `POST /api/login`
Login with license key

**Request:**
```json
{
  "license_key": "DVPRO-A1B2-C3D4-E5F6",
  "machine_id": "optional-machine-id"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "License hợp lệ (còn 29 ngày)",
  "license_data": {
    "license_key": "DVPRO-A1B2-C3D4-E5F6",
    "expiry_date": "2026-02-03",
    "status": "active",
    "days_left": 29
  }
}
```

### Protected Endpoints (Require Token)

All requests must include `Authorization: Bearer <token>` header.

#### `POST /api/speech-to-text`
Speech-to-Text via Groq

**Request:**
- Multipart form-data
- `file`: Audio file (WAV, MP3, etc.)
- `language`: Language code (default: "zh")

**Response:**
```json
{
  "success": true,
  "text": "Transcribed text here",
  "message": "Trich text thành công"
}
```

#### `POST /api/translate`
Translate text

**Request:**
```json
{
  "text": "你好",
  "source_lang": "zh-CN",
  "target_lang": "vi"
}
```

**Response:**
```json
{
  "success": true,
  "translated_text": "Xin chào",
  "message": "Dịch thành công"
}
```

#### `POST /api/logout`
Logout and invalidate token

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Đăng xuất thành công"
}
```

---

## 🔑 License Management

### Generate New Licenses

```bash
# Generate 1 license valid for 30 days
python generate_license.py generate --days 30 --count 1

# Generate 10 licenses valid for 365 days
python generate_license.py generate --days 365 --count 10
```

### List All Licenses

```bash
# List all licenses
python generate_license.py list

# List only active licenses
python generate_license.py list --status active
```

### Update License Status

```bash
# Deactivate a license
python generate_license.py update DVPRO-XXXX-XXXX-XXXX --status inactive

# Reactivate a license
python generate_license.py update DVPRO-XXXX-XXXX-XXXX --status active

# Suspend a license
python generate_license.py update DVPRO-XXXX-XXXX-XXXX --status suspended
```

### Extend License

```bash
# Extend by 30 days
python generate_license.py extend DVPRO-XXXX-XXXX-XXXX --days 30
```

---

## 🐳 Deployment (Railway.app)

### 1. Push to GitHub

```bash
git add server/
git commit -m "Add license server"
git push origin main
```

### 2. Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-detects `Dockerfile`

### 3. Set Environment Variables

In Railway dashboard, add:

```
GROQ_API_KEY=gsk_your_actual_key
GEMINI_API_KEY=AIza_your_actual_key
SERVER_SECRET_KEY=your-random-secret
PORT=8000
```

### 4. Deploy

Railway automatically deploys. Your server URL will be:
```
https://your-app-name.railway.app
```

### 5. Test Deployment

```bash
curl https://your-app-name.railway.app/health
```

---

## 🔒 Security

### API Keys Protection

- ✅ All API keys stored server-side only
- ✅ Client never sees Groq/Gemini keys
- ✅ Cannot extract keys from client .exe
- ✅ Server validates license on every request

### Token System

- Tokens expire after 7 days
- Each token tied to license + machine ID
- Token invalidated on logout
- License re-validated on each API call

### Rate Limiting

Configure in `config.py`:
```python
RATE_LIMIT_PER_MINUTE = 60
```

---

## 📊 Database Schema

### `licenses` Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| license_key | TEXT | Unique license key |
| expiry_date | TEXT | Expiry date (YYYY-MM-DD) |
| status | TEXT | active/inactive/suspended |
| machine_id | TEXT | Bound machine ID (nullable) |
| created_at | TEXT | Creation timestamp |
| last_used | TEXT | Last usage timestamp |
| notes | TEXT | Optional notes |

### `login_sessions` Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| license_key | TEXT | Associated license |
| token | TEXT | Unique session token |
| created_at | TEXT | Session creation time |
| expires_at | TEXT | Token expiry time |
| machine_id | TEXT | Machine ID |

---

## 🧪 Testing

### Test Login

```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"license_key":"DVPRO-XXXX-XXXX-XXXX"}'
```

### Test Protected Endpoint

```bash
curl -X POST http://localhost:8000/api/translate \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"text":"你好","source_lang":"zh-CN","target_lang":"vi"}'
```

---

## 📝 Contact Info (Displayed in Client)

- **Zalo:** 0366468477
- **Momo:** 0366468477
- **Price:** 50.000đ/tháng

---

## 🔧 Troubleshooting

### "GROQ_API_KEY not set"

Set environment variable:
```bash
export GROQ_API_KEY=gsk_your_key
# Or edit .env file
```

### Database locked error

Make sure only one server instance is running.

### Token expired

Client needs to login again:
```python
# In client
api_client.login("DVPRO-XXXX-XXXX-XXXX")
```

---

## 📄 License

Proprietary - DouyinVoice Pro
