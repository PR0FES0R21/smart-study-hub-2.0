# ==============================================================================
# File: app/api/v1/routes/academic_actions.py
# --- DIUBAH TOTAL ---
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1 import deps
from app.crud import crud_system_state
from app.schemas.academic_actions import AcademicYearRequest
from app.schemas.system_state import SystemTaskState
from app.tasks.academic_cycle_tasks import run_end_of_year_cycle_task

router = APIRouter()

@router.post("/start-end-of-year-cycle", response_model=SystemTaskState)
async def start_end_of_year_cycle(
    years: AcademicYearRequest,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memulai proses siklus akhir tahun ajaran (lulus, buat kelas, naik kelas)
    di latar belakang.
    """
    current_state = await crud_system_state.get_task_state(db, "end_of_year_cycle")
    if current_state and current_state.get("status") == "processing":
        raise HTTPException(status_code=409, detail="Proses akhir tahun ajaran sudah sedang berjalan.")
    
    # Picu background task
    run_end_of_year_cycle_task.delay(
        current_year=years.current_academic_year,
        next_year=years.next_academic_year
    )
    
    # Kembalikan status saat ini (atau status baru 'processing')
    new_state = await crud_system_state.get_task_state(db, "end_of_year_cycle")
    if not new_state: # Jika ini pertama kali dijalankan
        return {"task_name": "end_of_year_cycle", "status": "processing", "current_step": "Memulai..."}
    return new_state

@router.get("/end-of-year-cycle/status", response_model=SystemTaskState)
async def get_end_of_year_cycle_status(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Mengambil status terkini dari proses siklus akhir tahun ajaran."""
    state = await crud_system_state.get_task_state(db, "end_of_year_cycle")
    if not state:
        return {"task_name": "end_of_year_cycle", "status": "idle"}
    return state