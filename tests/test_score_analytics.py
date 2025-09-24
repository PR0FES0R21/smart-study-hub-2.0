#!/usr/bin/env python3
"""
Basic tests untuk modul score analytics (struktur dan import).
"""
import asyncio


async def test_imports_and_basic_calls():
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.core.config import settings
        from app.crud.crud_score_analytics import (
            get_admin_dashboard,
            get_teacher_dashboard,
            get_student_dashboard
        )

        client = AsyncIOMotorClient(settings.DATABASE_URL)
        db = client[settings.DATABASE_NAME]

        # Gunakan ID fiksi; fungsi harus handle tanpa error (mengembalikan struktur kosong/0)
        admin = await get_admin_dashboard(db, academic_period_id="507f1f77bcf86cd799439011")
        teacher = await get_teacher_dashboard(db, teacher_id="507f1f77bcf86cd799439012", academic_period_id="507f1f77bcf86cd799439011")
        student = await get_student_dashboard(db, student_id="507f1f77bcf86cd799439013", academic_period_id="507f1f77bcf86cd799439011")

        print("[OK] score analytics callable")
        assert isinstance(admin, dict)
        assert isinstance(teacher, dict)
        assert isinstance(student, dict)
    except Exception as e:
        print(f"[ERROR] score analytics import/call failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_imports_and_basic_calls())


