from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import pytz
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def get_wib_timezone():
    """Get WIB (UTC+7) timezone object"""
    return pytz.timezone('Asia/Jakarta')

def utc_to_wib(utc_datetime):
    """Convert UTC datetime to WIB"""
    if utc_datetime.tzinfo is None:
        # Assume it's UTC if no timezone info
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    wib_tz = get_wib_timezone()
    return utc_datetime.astimezone(wib_tz)

def get_current_wib_time():
    """Get current time in WIB timezone"""
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    return utc_to_wib(utc_now)


async def validate_exam_duration(db: AsyncIOMotorDatabase, session: dict, exam: dict) -> dict:
    """
    Validasi durasi ujian dengan timezone awareness
    """
    if not session.get("started_at"):
        return {"valid": True, "message": "Session belum dimulai"}
    
    # Convert to WIB for calculation
    session_start_wib = utc_to_wib(session["started_at"])
    current_wib = get_current_wib_time()
    
    elapsed_minutes = (current_wib - session_start_wib).total_seconds() / 60
    duration_limit = exam.get("duration_minutes", 0)
    grace_period = 5  # 5 menit toleransi
    
    if elapsed_minutes > (duration_limit + grace_period):
        return {
            "valid": False,
            "message": f"Waktu ujian telah habis. Durasi: {duration_limit} menit, Elapsed: {elapsed_minutes:.1f} menit",
            "should_auto_submit": True
        }
    elif elapsed_minutes > duration_limit:
        return {
            "valid": True,
            "message": f"Dalam periode toleransi. Sisa waktu: {grace_period - (elapsed_minutes - duration_limit):.1f} menit",
            "warning": True
        }
    else:
        remaining_minutes = duration_limit - elapsed_minutes
        return {
            "valid": True,
            "message": f"Sisa waktu: {remaining_minutes:.1f} menit",
            "remaining_minutes": remaining_minutes
        }

