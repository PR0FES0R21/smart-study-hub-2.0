# ==============================================================================
# File: app/tasks/academic_cycle_tasks.py
# Deskripsi: Background task untuk siklus akhir tahun ajaran.
# --- DITAMBAHKAN ---
# ==============================================================================
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.websocket import manager
from app.crud import crud_users, crud_classes, crud_system_state

TASK_NAME = "end_of_year_cycle"

def get_db_connection():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    return client[settings.DATABASE_NAME]

@celery_app.task
def run_end_of_year_cycle_task(current_year: str, next_year: str):
    """
    Menjalankan seluruh proses akhir tahun ajaran secara bertahap dan aman.
    """
    async def process():
        db = get_db_connection()
        # Cek apakah tugas lain sedang berjalan
        current_state = await crud_system_state.get_task_state(db, TASK_NAME)
        if current_state and current_state.get("status") == "processing":
            print("Proses akhir tahun ajaran sudah berjalan. Dibatalkan.")
            return

        steps = [
            {"name": "Meluluskan Siswa Kelas 12", "function": crud_users.graduate_students_by_grade, "args": [12]},
            {"name": "Membuat Struktur Kelas Baru", "function": crud_classes.create_classes_for_next_year, "args": [current_year, next_year]},
            {"name": "Menaikkan Siswa Kelas 11 ke 12", "function": crud_users.promote_students, "args": [11, current_year, next_year]},
            {"name": "Menaikkan Siswa Kelas 10 ke 11", "function": crud_users.promote_students, "args": [10, current_year, next_year]},
        ]
        total_steps = len(steps)

        try:
            await crud_system_state.update_task_state(db, TASK_NAME, {"status": "processing", "last_run_at": datetime.utcnow()})

            for i, step in enumerate(steps):
                progress = int(((i + 1) / total_steps) * 100)
                state_update = {"current_step": step["name"], "progress": progress}
                await crud_system_state.update_task_state(db, TASK_NAME, state_update)
                await manager.broadcast_to_roles({"type": "academic_cycle_progress", "data": state_update}, ["admin"])

                result_count = await step["function"](db, *step["args"])
                print(f"Langkah '{step['name']}' selesai, memengaruhi {result_count} dokumen.")

            final_state = {"status": "completed", "progress": 100, "current_step": "Selesai", "last_success_at": datetime.utcnow()}
            await crud_system_state.update_task_state(db, TASK_NAME, final_state)
            await manager.broadcast_to_roles({"type": "academic_cycle_complete", "data": final_state}, ["admin"])

        except Exception as e:
            error_state = {"status": "failed", "error_details": str(e)}
            await crud_system_state.update_task_state(db, TASK_NAME, error_state)
            await manager.broadcast_to_roles({"type": "academic_cycle_failed", "data": error_state}, ["admin"])
            print(f"ERROR saat menjalankan siklus akhir tahun: {e}")

    asyncio.run(process())
    return {"status": "Task runner finished."}
