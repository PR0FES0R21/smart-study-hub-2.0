# ==============================================================================
# File: app/tasks/excel_tasks.py
# Deskripsi: Definisi background task untuk Celery.
# --- DIUBAH --- (Logika impor disesuaikan dengan template baru)
# ==============================================================================
import openpyxl
import asyncio
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
from typing import Any, Dict
import json

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.user import UserCreate, ProfileCreate
from app.crud.crud_users import create_user_and_profile
from app.core.export_engine import build_dynamic_pipeline, RELATIONSHIP_MAP

TEMP_DIR = Path("./temp_uploads")

def get_db_connection():
    client = AsyncIOMotorClient(settings.DATABASE_URL)
    return client[settings.DATABASE_NAME]

# --- DITAMBAHKAN: Fungsi helper untuk mengambil nilai bersarang ---
def get_nested_value(d: Dict, key: str, default: Any = None) -> Any:
    """Mengambil nilai dari dictionary bersarang menggunakan dot notation."""
    keys = key.split('.')
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d

@celery_app.task(bind=True)
def import_users_task(self, file_path: str):
    """Background task untuk mengimpor user dari file Excel."""
    loop = asyncio.get_event_loop()
    db = get_db_connection()
    
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    
    success_count = 0
    failed_count = 0
    errors = []

    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True)):
        if not any(row): continue

        try:
            # --- PERBAIKAN: Membaca semua kolom dari template baru ---
            (
                login_id, email, full_name, roles_str,
                gender, birth_date_str, birth_place, address, phone_number,
                class_id, department_id, start_year, end_year
            ) = row

            roles = [r.strip() for r in roles_str.split(',')]
            
            # Konversi tanggal jika ada
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d') if birth_date_str else None

            # Membuat objek ProfileCreate dengan data lengkap
            profile_in = ProfileCreate(
                full_name=full_name,
                gender=gender,
                birth_date=birth_date,
                birth_place=birth_place,
                address=address,
                phone_number=phone_number,
                class_id=class_id,
                department_id=department_id,
                start_year=start_year,
                end_year=end_year
            )
            
            user_in = UserCreate(
                login_id=login_id,
                email=email,
                password=login_id,
                roles=roles,
                profile=profile_in
            )
            
            loop.run_until_complete(create_user_and_profile(db, user_in))
            success_count += 1
        except Exception as e:
            failed_count += 1
            errors.append(f"Row {i+2}: {str(e)}")
        
        self.update_state(state='PROGRESS', meta={'current': i, 'total': sheet.max_row - 1})

    Path(file_path).unlink()

    return {
        "status": "Completed",
        "success_count": success_count,
        "failed_count": failed_count,
        "errors": errors
    }


@celery_app.task(bind=True)
def export_data_task(self, export_request: dict):
    """Background task untuk mengekspor data secara dinamis ke Excel."""
    loop = asyncio.get_event_loop()
    db = get_db_connection()
    
    base_resource = export_request["base_resource"]
    projections = export_request["projections"]
    filters = export_request["filters"]

    pipeline = build_dynamic_pipeline(base_resource, projections, filters)
    data_to_export = loop.run_until_complete(db[base_resource].aggregate(pipeline).to_list(None))

    if not data_to_export:
        return {"status": "Completed", "message": "No data found for the given criteria.", "file_path": None}

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"Export {base_resource}"

    # --- PERBAIKAN: Membuat header dan pemetaan kunci dengan benar ---
    headers = []
    key_map = [] # Menyimpan path dot notation yang benar untuk setiap header

    # Tambahkan field dasar
    for field in projections.get("base", []):
        headers.append(field)
        key_map.append(field)

    # Tambahkan field dari 'includes'
    current_resource = base_resource
    for include in projections.get("includes", []):
        collection_name = include["collection"]
        
        relation = None
        for res, relations in RELATIONSHIP_MAP.items():
            if collection_name in relations:
                relation = relations[collection_name]
                break
        
        if relation:
            prefix = relation['as']
            for field in include["fields"]:
                headers.append(f"{collection_name}.{field}")
                key_map.append(f"{prefix}.{field}")
    
    sheet.append(headers)

    # --- PERBAIKAN: Mengisi data menggunakan key_map yang sudah benar ---
    for item in data_to_export:
        row = [str(get_nested_value(item, key, default="")) for key in key_map]
        sheet.append(row)

    file_name = f"export_{base_resource}_{uuid.uuid4()}.xlsx"
    file_path = str(TEMP_DIR / file_name)
    workbook.save(file_path)

    return {"status": "Completed", "message": "Export successful.", "file_path": file_path}
