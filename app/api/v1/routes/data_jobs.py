# ==============================================================================
# File: app/api/v1/routes/data_jobs.py
# Deskripsi: Endpoint untuk memulai dan memeriksa background jobs.
# --- DIUBAH --- (Template Excel diperbarui)
# ==============================================================================
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from celery.result import AsyncResult
import shutil
from pathlib import Path
import openpyxl
import io

from app.core.celery_app import celery_app
from app.api.v1 import deps
from app.schemas.task import TaskStatus
from app.schemas.export import ExportRequest

router = APIRouter()
TEMP_DIR = Path("./temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

@router.get("/users/import-template")
async def download_import_template(
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Menghasilkan dan menyajikan file Excel template untuk impor pengguna.
    """
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Template Import Pengguna"

    # --- PERBAIKAN: Header yang lebih komprehensif ---
    headers = [
        "login_id", "email", "full_name", "roles",
        "gender", "birth_date (YYYY-MM-DD)", "birth_place", "address", "phone_number",
        "class_id", "department_id", "start_year", "end_year"
    ]
    sheet.append(headers)

    # Tambahkan contoh data untuk siswa
    example_student = [
        "SISWA001", "siswa.baru@example.com", "Budi Siswanto", "student",
        "Laki-laki", "2008-05-10", "Jakarta", "Jl. Merdeka 1", "08123456789",
        "ID_KELAS_DISINI", "", 2024, 2027
    ]
    sheet.append(example_student)
    
    # Tambahkan contoh data untuk guru
    example_teacher = [
        "GURU005", "guru.baru@example.com", "Siti Nurbaya", "teacher",
        "Perempuan", "1990-01-15", "Bandung", "Jl. Pendidikan 2", "08987654321",
        "", "ID_JURUSAN_DISINI", "", ""
    ]
    sheet.append(example_teacher)
    
    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template_import_pengguna_lengkap.xlsx"}
    )

@router.post("/users/import", response_model=TaskStatus, status_code=202)
async def import_users_from_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(deps.get_current_active_admin)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an .xlsx file.")

    file_path = TEMP_DIR / f"import_{file.filename}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    task = celery_app.send_task("app.tasks.excel_tasks.import_users_task", args=[str(file_path)])
    
    return {"task_id": task.id, "status": "Processing"}

@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    task_result = AsyncResult(task_id, app=celery_app)
    result = task_result.result
    
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": result
    }

@router.post("/export", response_model=TaskStatus, status_code=202)
async def export_data_to_excel(
    export_request: ExportRequest,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """
    Memulai proses ekspor data dinamis di background.
    """
    task = celery_app.send_task("app.tasks.excel_tasks.export_data_task", args=[export_request.model_dump()])
    return {"task_id": task.id, "status": "Processing"}

@router.get("/tasks/{task_id}/download")
async def download_task_result(
    task_id: str,
    current_user: dict = Depends(deps.get_current_active_admin)
):
    """Mengunduh file hasil dari background task yang sudah selesai."""
    task_result = AsyncResult(task_id, app=celery_app)
    if not task_result.successful():
        raise HTTPException(status_code=404, detail="Task not completed or failed.")
    
    result = task_result.result
    file_path = result.get("file_path")
    
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Result file not found.")

    return FileResponse(path=file_path, filename=Path(file_path).name, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# @router.get("/tasks/{task_id}", response_model=TaskStatus)
# async def get_task_status(task_id: str, current_user: dict = Depends(deps.get_current_active_admin)):
#     # ... (kode tidak berubah) ...
#     task_result = AsyncResult(task_id, app=celery_app); result = task_result.result
#     return {"task_id": task_id, "status": task_result.status, "result": result}


