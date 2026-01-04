"""
Database module for license management

Uses SQLite to store license information
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import hashlib
import secrets


class Database:
    """SQLite database for license management"""

    def __init__(self, db_path: str = "licenses.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create licenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE NOT NULL,
                expiry_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active', 'inactive', 'suspended')),
                machine_id TEXT,
                created_at TEXT NOT NULL,
                last_used TEXT,
                notes TEXT,
                tier TEXT NOT NULL DEFAULT 'basic' CHECK(tier IN ('basic', 'pro', 'vip')),
                monthly_limit INTEGER NOT NULL DEFAULT 100,
                videos_used INTEGER NOT NULL DEFAULT 0,
                reset_date TEXT NOT NULL,
                last_ip TEXT,
                ip_changes INTEGER NOT NULL DEFAULT 0,
                last_ip_change TEXT,
                daily_usage INTEGER NOT NULL DEFAULT 0,
                daily_usage_date TEXT,
                is_suspicious INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Create login_sessions table for token management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                machine_id TEXT,
                FOREIGN KEY (license_key) REFERENCES licenses(license_key)
            )
        """)

        conn.commit()
        conn.close()

    def generate_license_key(self) -> str:
        """Generate a unique license key"""
        # Format: DVPRO-XXXX-XXXX-XXXX
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        part3 = secrets.token_hex(2).upper()
        return f"DVPRO-{part1}-{part2}-{part3}"

    def create_license(
        self,
        expiry_days: int = 30,
        status: str = "active",
        notes: str = "",
        tier: str = "basic"
    ) -> Dict:
        """
        Create a new license

        Args:
            expiry_days: Number of days until expiry
            status: License status (active/inactive/suspended)
            notes: Optional notes
            tier: License tier (basic/pro/vip)

        Returns:
            Dict with license info
        """
        # Tier limits
        tier_limits = {
            "basic": 100,
            "pro": 500,
            "vip": -1  # unlimited
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        license_key = self.generate_license_key()
        created_at = datetime.now().isoformat()
        expiry_date = (datetime.now() + timedelta(days=expiry_days)).date().isoformat()
        monthly_limit = tier_limits.get(tier, 100)
        reset_date = (datetime.now() + timedelta(days=30)).date().isoformat()

        cursor.execute("""
            INSERT INTO licenses (license_key, expiry_date, status, created_at, notes, tier, monthly_limit, videos_used, reset_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (license_key, expiry_date, status, created_at, notes, tier, monthly_limit, 0, reset_date))

        conn.commit()
        conn.close()

        return {
            "license_key": license_key,
            "expiry_date": expiry_date,
            "status": status,
            "created_at": created_at,
            "tier": tier,
            "monthly_limit": monthly_limit
        }

    def verify_license(self, license_key: str, machine_id: str = None) -> tuple[bool, str, Optional[Dict]]:
        """
        Verify if license is valid

        Args:
            license_key: License key to verify
            machine_id: Optional machine ID for binding

        Returns:
            Tuple of (is_valid, message, license_data)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT license_key, expiry_date, status, machine_id, last_used, tier, monthly_limit, videos_used, reset_date
            FROM licenses
            WHERE license_key = ?
        """, (license_key,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, "License key không tồn tại", None

        db_key, expiry_date, status, db_machine_id, last_used, tier, monthly_limit, videos_used, reset_date = result

        # Check status
        if status != "active":
            conn.close()
            return False, f"License không hoạt động (status: {status})", None

        # Check expiry
        expiry = datetime.fromisoformat(expiry_date)
        if expiry < datetime.now():
            conn.close()
            return False, f"License đã hết hạn ({expiry_date})", None

        # Check and reset monthly usage if needed
        reset = datetime.fromisoformat(reset_date)
        if reset < datetime.now():
            # Reset monthly counter
            new_reset_date = (datetime.now() + timedelta(days=30)).date().isoformat()
            cursor.execute("""
                UPDATE licenses
                SET videos_used = 0, reset_date = ?
                WHERE license_key = ?
            """, (new_reset_date, license_key))
            conn.commit()
            videos_used = 0
            reset_date = new_reset_date

        # Check machine binding (if machine_id provided)
        if machine_id:
            if db_machine_id and db_machine_id != machine_id:
                conn.close()
                return False, "License đã được kích hoạt trên máy khác", None

            # Update machine_id if not set
            if not db_machine_id:
                cursor.execute("""
                    UPDATE licenses
                    SET machine_id = ?, last_used = ?
                    WHERE license_key = ?
                """, (machine_id, datetime.now().isoformat(), license_key))
                conn.commit()

        # Update last_used
        cursor.execute("""
            UPDATE licenses
            SET last_used = ?
            WHERE license_key = ?
        """, (datetime.now().isoformat(), license_key))
        conn.commit()

        conn.close()

        days_left = (expiry - datetime.now()).days
        videos_remaining = monthly_limit - videos_used if monthly_limit > 0 else -1  # -1 means unlimited

        return True, f"License hợp lệ (còn {days_left} ngày)", {
            "license_key": db_key,
            "expiry_date": expiry_date,
            "status": status,
            "days_left": days_left,
            "tier": tier,
            "monthly_limit": monthly_limit,
            "videos_used": videos_used,
            "videos_remaining": videos_remaining,
            "reset_date": reset_date
        }

    def get_license(self, license_key: str) -> Optional[Dict]:
        """Get license information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT license_key, expiry_date, status, machine_id, created_at, last_used, notes, tier, monthly_limit, videos_used, reset_date
            FROM licenses
            WHERE license_key = ?
        """, (license_key,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        return {
            "license_key": result[0],
            "expiry_date": result[1],
            "status": result[2],
            "machine_id": result[3],
            "created_at": result[4],
            "last_used": result[5],
            "notes": result[6],
            "tier": result[7],
            "monthly_limit": result[8],
            "videos_used": result[9],
            "reset_date": result[10]
        }

    def list_licenses(self, status: Optional[str] = None) -> List[Dict]:
        """List all licenses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT license_key, expiry_date, status, machine_id, created_at, last_used, tier, monthly_limit, videos_used, reset_date
                FROM licenses
                WHERE status = ?
                ORDER BY created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT license_key, expiry_date, status, machine_id, created_at, last_used, tier, monthly_limit, videos_used, reset_date
                FROM licenses
                ORDER BY created_at DESC
            """)

        results = cursor.fetchall()
        conn.close()

        licenses = []
        for row in results:
            licenses.append({
                "license_key": row[0],
                "expiry_date": row[1],
                "status": row[2],
                "machine_id": row[3],
                "created_at": row[4],
                "last_used": row[5],
                "tier": row[6],
                "monthly_limit": row[7],
                "videos_used": row[8],
                "reset_date": row[9]
            })

        return licenses

    def update_license_status(self, license_key: str, status: str) -> bool:
        """Update license status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE licenses
            SET status = ?
            WHERE license_key = ?
        """, (status, license_key))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated

    def extend_license(self, license_key: str, days: int) -> bool:
        """Extend license expiry date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT expiry_date FROM licenses WHERE license_key = ?
        """, (license_key,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return False

        current_expiry = datetime.fromisoformat(result[0])
        new_expiry = (current_expiry + timedelta(days=days)).date().isoformat()

        cursor.execute("""
            UPDATE licenses
            SET expiry_date = ?
            WHERE license_key = ?
        """, (new_expiry, license_key))

        conn.commit()
        conn.close()

        return True

    def create_session(self, license_key: str, machine_id: str = None) -> Optional[str]:
        """Create a login session and return token"""
        # Verify license first
        is_valid, message, license_data = self.verify_license(license_key, machine_id)
        if not is_valid:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generate token
        token = secrets.token_urlsafe(32)
        created_at = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()  # Token valid for 7 days

        cursor.execute("""
            INSERT INTO login_sessions (license_key, token, created_at, expires_at, machine_id)
            VALUES (?, ?, ?, ?, ?)
        """, (license_key, token, created_at, expires_at, machine_id))

        conn.commit()
        conn.close()

        return token

    def verify_token(self, token: str) -> tuple[bool, Optional[str]]:
        """
        Verify if token is valid

        Returns:
            Tuple of (is_valid, license_key)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT license_key, expires_at
            FROM login_sessions
            WHERE token = ?
        """, (token,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, None

        license_key, expires_at = result

        # Check if token expired
        if datetime.fromisoformat(expires_at) < datetime.now():
            conn.close()
            return False, None

        # Verify license is still valid
        is_valid, message, license_data = self.verify_license(license_key)
        conn.close()

        if not is_valid:
            return False, None

        return True, license_key

    def delete_session(self, token: str) -> bool:
        """Delete a session (logout)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM login_sessions WHERE token = ?", (token,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def increment_video_usage(self, license_key: str) -> tuple[bool, str]:
        """
        Increment video usage counter for a license

        Returns:
            Tuple of (success, message)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tier, monthly_limit, videos_used, reset_date
            FROM licenses
            WHERE license_key = ?
        """, (license_key,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "License không tồn tại"

        tier, monthly_limit, videos_used, reset_date = result

        # Check if reset needed
        reset = datetime.fromisoformat(reset_date)
        if reset < datetime.now():
            # Reset counter
            new_reset_date = (datetime.now() + timedelta(days=30)).date().isoformat()
            cursor.execute("""
                UPDATE licenses
                SET videos_used = 1, reset_date = ?
                WHERE license_key = ?
            """, (new_reset_date, license_key))
            conn.commit()
            conn.close()
            return True, "Đã reset và sử dụng 1 video"

        # Check limit (skip for VIP unlimited)
        if monthly_limit > 0 and videos_used >= monthly_limit:
            conn.close()
            return False, f"Đã hết quota tháng này ({videos_used}/{monthly_limit})"

        # Increment counter
        cursor.execute("""
            UPDATE licenses
            SET videos_used = videos_used + 1
            WHERE license_key = ?
        """, (license_key,))

        conn.commit()
        conn.close()

        return True, f"Đã sử dụng {videos_used + 1}/{monthly_limit if monthly_limit > 0 else 'unlimited'} video"

    def get_usage_info(self, license_key: str) -> Optional[Dict]:
        """Get usage information for a license"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tier, monthly_limit, videos_used, reset_date
            FROM licenses
            WHERE license_key = ?
        """, (license_key,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        tier, monthly_limit, videos_used, reset_date = result
        videos_remaining = monthly_limit - videos_used if monthly_limit > 0 else -1

        return {
            "tier": tier,
            "monthly_limit": monthly_limit,
            "videos_used": videos_used,
            "videos_remaining": videos_remaining,
            "reset_date": reset_date
        }

    def track_ip_usage(self, license_key: str, ip_address: str) -> tuple[bool, str]:
        """
        Track IP address usage and detect suspicious activity

        Returns:
            Tuple of (is_suspicious, message)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current IP tracking data
        cursor.execute("""
            SELECT last_ip, ip_changes, last_ip_change, daily_usage, daily_usage_date
            FROM licenses
            WHERE license_key = ?
        """, (license_key,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "License not found"

        last_ip, ip_changes, last_ip_change, daily_usage, daily_usage_date = result
        now = datetime.now()
        is_suspicious = False
        message = "OK"

        # Reset daily usage if new day
        if daily_usage_date:
            last_date = datetime.fromisoformat(daily_usage_date).date()
            if last_date < now.date():
                daily_usage = 0
                daily_usage_date = now.isoformat()
        else:
            daily_usage_date = now.isoformat()

        # Increment daily usage
        daily_usage += 1

        # Check for suspicious daily usage (> 50 videos in one day)
        if daily_usage > 50:
            is_suspicious = True
            message = f"Suspicious: {daily_usage} videos in one day"

        # Track IP changes
        if last_ip and last_ip != ip_address:
            # IP changed - check if within 24 hours
            if last_ip_change:
                last_change = datetime.fromisoformat(last_ip_change)
                hours_since_change = (now - last_change).total_seconds() / 3600

                if hours_since_change < 24:
                    # Within 24 hours - increment counter
                    ip_changes += 1

                    # Check if too many changes
                    if ip_changes > 5:
                        is_suspicious = True
                        message = f"Suspicious: IP changed {ip_changes} times in 24 hours"
                else:
                    # More than 24 hours - reset counter
                    ip_changes = 1
            else:
                # First IP change
                ip_changes = 1

            last_ip_change = now.isoformat()
            last_ip = ip_address

        elif not last_ip:
            # First time using - set IP
            last_ip = ip_address
            last_ip_change = now.isoformat()
            ip_changes = 0

        # Update database
        cursor.execute("""
            UPDATE licenses
            SET last_ip = ?,
                ip_changes = ?,
                last_ip_change = ?,
                daily_usage = ?,
                daily_usage_date = ?,
                is_suspicious = ?
            WHERE license_key = ?
        """, (last_ip, ip_changes, last_ip_change, daily_usage, daily_usage_date,
              1 if is_suspicious else 0, license_key))

        conn.commit()
        conn.close()

        return is_suspicious, message

    def get_suspicious_licenses(self) -> List[Dict]:
        """Get all licenses flagged as suspicious"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT license_key, last_ip, ip_changes, daily_usage,
                   daily_usage_date, last_ip_change, tier, status
            FROM licenses
            WHERE is_suspicious = 1
            ORDER BY daily_usage DESC, ip_changes DESC
        """)

        results = cursor.fetchall()
        conn.close()

        licenses = []
        for row in results:
            licenses.append({
                "license_key": row[0],
                "last_ip": row[1],
                "ip_changes": row[2],
                "daily_usage": row[3],
                "daily_usage_date": row[4],
                "last_ip_change": row[5],
                "tier": row[6],
                "status": row[7]
            })

        return licenses

    def clear_suspicious_flag(self, license_key: str) -> bool:
        """Clear suspicious flag from a license"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE licenses
            SET is_suspicious = 0,
                ip_changes = 0,
                daily_usage = 0
            WHERE license_key = ?
        """, (license_key,))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated
