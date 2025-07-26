# ==============================================================================
# File: app/tasks/excel_tasks.py
# Deskripsi: Definisi background task untuk Celery (FULLY FIXED VERSION).
# --- DIPERBAIKI --- Event loop lifecycle dan database connection management
# ==============================================================================
import openpyxl
import asyncio
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid
from typing import Any, Dict
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.user import UserCreate, ProfileCreate
from app.crud.crud_users import create_user_and_profile
from app.core.export_engine import build_dynamic_pipeline, RELATIONSHIP_MAP

# Setup logging
logger = logging.getLogger(__name__)

TEMP_DIR = Path("./temp_uploads")

# --- PERBAIKAN 1: Event loop manager yang aman ---
class SafeEventLoopManager:
    """Manager untuk mengelola event loop dengan aman di Celery."""
    
    @staticmethod
    def run_async_task(coro, timeout=300):
        """
        Menjalankan coroutine dengan event loop yang aman.
        Menggunakan thread pool untuk menghindari konflik event loop.
        """
        def run_in_thread():
            # Buat event loop baru di thread terpisah
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                # Pastikan semua task selesai sebelum close
                try:
                    # Cancel semua pending tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    
                    # Tunggu semua task selesai
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                finally:
                    loop.close()
        
        # Jalankan di thread pool
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=timeout)

# --- PERBAIKAN 2: Database manager dengan proper cleanup ---
class DatabaseManager:
    """Manager untuk koneksi database dengan proper cleanup."""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        self.db = self.client[settings.DATABASE_NAME]
        return self.db
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit dengan proper cleanup."""
        if self.client:
            # Tunggu sebentar untuk memastikan operasi selesai
            await asyncio.sleep(0.1)
            self.client.close()
            self.client = None
            self.db = None

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

# --- PERBAIKAN 3: Fungsi async dengan proper resource management ---
async def async_import_users_logic(file_path: str, task_instance=None):
    """
    Logic async untuk import users dengan proper resource management.
    
    Expected Excel columns (dalam urutan):
    1. login_id (WAJIB) - ID unik untuk login
    2. email (Optional) - akan generate default jika kosong: {login_id}@example.com
    3. full_name (Optional) - akan generate default jika kosong: "User {login_id}"
    4. roles (Optional) - comma-separated roles, default: "user"
    5. gender (Optional)
    6. birth_date (Optional) - format: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, atau YYYY/MM/DD
    7. birth_place (Optional)
    8. address (Optional)
    9. phone_number (Optional)
    10. class_id (Optional)
    11. department_id (Optional)
    12. start_year (Optional) - tahun mulai (1900-2100)
    13. end_year (Optional) - tahun selesai (1900-2100)
    
    Hanya login_id yang wajib diisi, semua field lainnya optional.
    """
    
    async with DatabaseManager() as db:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        
        success_count = 0
        failed_count = 0
        errors = []
        total_rows = sheet.max_row - 1

        for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True)):
            if not any(row): 
                continue

            try:
                # --- Membaca semua kolom dari template (semua optional kecuali login_id) ---
                row_data = list(row)
                # Extend dengan None untuk kolom yang kosong
                while len(row_data) < 12:
                    row_data.append(None)
                
                # Helper function untuk membersihkan dan validasi data
                def clean_value(value, default=None):
                    """Membersihkan nilai dari Excel, menangani berbagai tipe data."""
                    if value is None:
                        return default
                    if isinstance(value, str):
                        cleaned = value.strip()
                        return cleaned if cleaned else default
                    return value
                
                # Ekstrak data dengan cleaning
                login_id = clean_value(row_data[0])
                email = clean_value(row_data[1])
                full_name = clean_value(row_data[2])
                roles_str = clean_value(row_data[3])
                gender = clean_value(row_data[4])
                birth_date_str = clean_value(row_data[5])
                birth_place = clean_value(row_data[6])
                address = clean_value(row_data[7])
                phone_number = clean_value(row_data[8])
                class_id = clean_value(row_data[9])
                department_id = clean_value(row_data[10])
                start_year = clean_value(row_data[11])
                end_year = clean_value(row_data[12]) if len(row_data) > 12 else None

                # Validasi minimal: hanya login_id yang wajib
                if not login_id:
                    raise ValueError("login_id tidak boleh kosong")

                # Email default jika tidak diisi
                if not email:
                    email = f"{login_id}@example.com"  # Email default
                    logger.info(f"Generated default email for {login_id}: {email}")

                # Parsing roles - default ke 'user' jika kosong
                roles = []
                if roles_str:
                    roles = [r.strip() for r in str(roles_str).split(',') if r.strip()]
                if not roles:
                    roles = ['user']  # Default role
                
                # Konversi tanggal dengan handling yang lebih fleksibel
                birth_date = None
                if birth_date_str:
                    try:
                        if isinstance(birth_date_str, datetime):
                            birth_date = birth_date_str
                        else:
                            # Try multiple date formats
                            date_str = str(birth_date_str).strip()
                            for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                                try:
                                    birth_date = datetime.strptime(date_str, date_format)
                                    break
                                except ValueError:
                                    continue
                            
                            if not birth_date:
                                logger.warning(f"Could not parse date '{birth_date_str}' for row {i+2}")
                    except Exception as e:
                        logger.warning(f"Date parsing error for row {i+2}: {e}")

                # Helper untuk konversi year dengan validation
                def safe_int_convert(value, field_name):
                    """Safely convert value to int with validation."""
                    if not value:
                        return None
                    try:
                        if isinstance(value, (int, float)):
                            return int(value)
                        val_str = str(value).strip()
                        if val_str.isdigit():
                            year = int(val_str)
                            # Validasi tahun reasonable (1900-2100)
                            if 1900 <= year <= 2100:
                                return year
                            else:
                                logger.warning(f"Invalid {field_name} '{year}' for row {i+2}")
                                return None
                        return None
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert {field_name} '{value}' to integer for row {i+2}")
                        return None

                # Membuat objek ProfileCreate dengan semua field optional
                profile_in = ProfileCreate(
                    full_name=full_name or f"User {login_id}",  # Default name jika kosong
                    gender=gender,  # Optional
                    birth_date=birth_date,  # Optional
                    birth_place=birth_place,  # Optional
                    address=address,  # Optional
                    phone_number=phone_number,  # Optional
                    class_id=class_id,  # Optional
                    department_id=department_id,  # Optional
                    start_year=safe_int_convert(start_year, "start_year"),  # Optional
                    end_year=safe_int_convert(end_year, "end_year")  # Optional
                )
                
                user_in = UserCreate(
                    login_id=login_id,
                    email=email,
                    password=login_id,  # Default password = login_id
                    roles=roles,
                    profile=profile_in
                )
                
                await create_user_and_profile(db, user_in)
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                error_msg = f"Row {i+2}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Import error on row {i+2}: {e}")
            
            # Update progress jika task instance tersedia
            if task_instance:
                try:
                    task_instance.update_state(
                        state='PROGRESS', 
                        meta={
                            'current': i + 1, 
                            'total': total_rows,
                            'success_count': success_count,
                            'failed_count': failed_count
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to update task state: {e}")

        # Cleanup: hapus file setelah selesai
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete temp file {file_path}: {e}")

        return {
            "status": "Completed",
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors[:10]  # Limit errors untuk menghindari response terlalu besar
        }

# --- PERBAIKAN 4: Task dengan safe event loop manager ---
@celery_app.task(bind=True)
def import_users_task(self, file_path: str):
    """Background task untuk mengimpor user dari file Excel."""
    try:
        logger.info(f"Starting import task for file: {file_path}")
        
        # Validasi file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File tidak ditemukan: {file_path}")
        
        # SOLUSI UTAMA: Gunakan SafeEventLoopManager
        result = SafeEventLoopManager.run_async_task(
            async_import_users_logic(file_path, self),
            timeout=600  # 10 menit timeout
        )
        
        logger.info(f"Import task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Import task failed: {str(e)}")
        # Update state ke FAILURE dengan info error
        try:
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )
        except Exception as state_error:
            logger.error(f"Failed to update task state: {state_error}")
        
        raise e

# --- PERBAIKAN 5: Fungsi async untuk export dengan resource management ---
async def async_export_data_logic(export_request: dict, task_instance=None):
    """Logic async untuk export data dengan proper resource management."""
    
    async with DatabaseManager() as db:
        base_resource = export_request["base_resource"]
        projections = export_request["projections"]
        filters = export_request["filters"]

        if task_instance:
            task_instance.update_state(state='PROGRESS', meta={'stage': 'Building pipeline'})

        pipeline = build_dynamic_pipeline(base_resource, projections, filters)
        
        if task_instance:
            task_instance.update_state(state='PROGRESS', meta={'stage': 'Fetching data'})
        
        data_to_export = await db[base_resource].aggregate(pipeline).to_list(None)

        if not data_to_export:
            return {
                "status": "Completed", 
                "message": "No data found for the given criteria.", 
                "file_path": None
            }

        if task_instance:
            task_instance.update_state(
                state='PROGRESS', 
                meta={'stage': 'Creating Excel file', 'total_records': len(data_to_export)}
            )

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = f"Export {base_resource}"

        # --- Membuat header dan pemetaan kunci ---
        headers = []
        key_map = []

        # Tambahkan field dasar
        for field in projections.get("base", []):
            headers.append(field)
            key_map.append(field)

        # Tambahkan field dari 'includes'
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

        # --- Mengisi data ---
        for i, item in enumerate(data_to_export):
            row = [str(get_nested_value(item, key, default="")) for key in key_map]
            sheet.append(row)
            
            # Update progress setiap 100 records
            if task_instance and i % 100 == 0:
                try:
                    task_instance.update_state(
                        state='PROGRESS',
                        meta={
                            'stage': 'Writing Excel data',
                            'current': i,
                            'total': len(data_to_export)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to update export progress: {e}")

        # Pastikan direktori ada
        TEMP_DIR.mkdir(exist_ok=True)
        
        file_name = f"export_{base_resource}_{uuid.uuid4()}.xlsx"
        file_path = str(TEMP_DIR / file_name)
        
        workbook.save(file_path)

        return {
            "status": "Completed", 
            "message": "Export successful.", 
            "file_path": file_path,
            "total_records": len(data_to_export)
        }

# --- PERBAIKAN 6: Export task dengan safe event loop manager ---
@celery_app.task(bind=True)
def export_data_task(self, export_request: dict):
    """Background task untuk mengekspor data secara dinamis ke Excel."""
    try:
        logger.info(f"Starting export task for: {export_request.get('base_resource', 'unknown')}")
        
        # SOLUSI UTAMA: Gunakan SafeEventLoopManager
        result = SafeEventLoopManager.run_async_task(
            async_export_data_logic(export_request, self),
            timeout=1800  # 30 menit timeout untuk export besar
        )
        
        logger.info(f"Export task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Export task failed: {str(e)}")
        # Update state ke FAILURE dengan info error
        try:
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(e),
                    'stage': 'Failed',
                    'error_type': type(e).__name__
                }
            )
        except Exception as state_error:
            logger.error(f"Failed to update export task state: {state_error}")
        
        raise e

# --- BONUS: Task untuk cleanup file temporary ---
@celery_app.task
def cleanup_temp_files():
    """Task periodic untuk membersihkan file temporary yang sudah lama."""
    import time
    
    if not TEMP_DIR.exists():
        return {"status": "No temp directory found"}
    
    cleaned_count = 0
    current_time = time.time()
    
    for file_path in TEMP_DIR.glob("*.xlsx"):
        try:
            # Hapus file yang lebih dari 1 jam
            if current_time - file_path.stat().st_mtime > 3600:
                file_path.unlink()
                cleaned_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {file_path}: {e}")
    
    return {"status": "Completed", "cleaned_files": cleaned_count}

# --- BONUS: Task untuk generate template Excel ---
@celery_app.task
def generate_import_template():
    """
    Generate template Excel untuk import users.
    Returns path ke template file yang bisa di-download.
    """
    try:
        # Pastikan direktori ada
        TEMP_DIR.mkdir(exist_ok=True)
        
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "User Import Template"
        
        # Header dengan keterangan
        headers = [
            "login_id",      # WAJIB
            "email",         # Optional
            "full_name",     # Optional  
            "roles",         # Optional
            "gender",        # Optional
            "birth_date",    # Optional
            "birth_place",   # Optional
            "address",       # Optional
            "phone_number",  # Optional
            "class_id",      # Optional
            "department_id", # Optional
            "start_year",    # Optional
            "end_year"       # Optional
        ]
        
        # Tambahkan header
        sheet.append(headers)
        
        # Tambahkan contoh data
        example_data = [
            "johndoe",                    # login_id (WAJIB)
            "john.doe@example.com",       # email
            "John Doe",                   # full_name
            "user,student",               # roles (comma separated)
            "Male",                       # gender
            "1995-01-15",                 # birth_date (YYYY-MM-DD)
            "Jakarta",                    # birth_place
            "Jl. Contoh No. 123",         # address
            "081234567890",               # phone_number
            "CLASS001",                   # class_id
            "IT",                         # department_id
            "2020",                       # start_year
            "2024"                        # end_year
        ]
        sheet.append(example_data)
        
        # Styling untuk header
        from openpyxl.styles import Font, PatternFill
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        
        for cell in sheet[1]:
            cell.font = header_font
            cell.fill = header_fill
        
        # Auto-adjust column widths
        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            sheet.column_dimensions[column_letter].width = adjusted_width
        
        # Tambahkan instruksi di sheet terpisah
        instruction_sheet = workbook.create_sheet("Instruksi")
        instructions = [
            ["PANDUAN PENGGUNAAN TEMPLATE IMPORT USER"],
            [""],
            ["FIELD WAJIB:"],
            ["• login_id: ID unik untuk login user (TIDAK BOLEH KOSONG)"],
            [""],
            ["FIELD OPTIONAL:"],
            ["• email: Email user (jika kosong akan generate otomatis)"],
            ["• full_name: Nama lengkap user"],
            ["• roles: Role user, pisahkan dengan koma. Contoh: user,admin"],
            ["• gender: Jenis kelamin"],
            ["• birth_date: Tanggal lahir (format: YYYY-MM-DD, DD/MM/YYYY, atau DD-MM-YYYY)"],
            ["• birth_place: Tempat lahir"],
            ["• address: Alamat"],
            ["• phone_number: Nomor telepon"],
            ["• class_id: ID kelas"],
            ["• department_id: ID departemen"],
            ["• start_year: Tahun mulai (1900-2100)"],
            ["• end_year: Tahun selesai (1900-2100)"],
            [""],
            ["CATATAN:"],
            ["• Hanya login_id yang WAJIB diisi"],
            ["• Semua field lain boleh dikosongkan"],
            ["• Jika email kosong, sistem akan generate: {login_id}@example.com"],
            ["• Jika full_name kosong, sistem akan generate: User {login_id}"],
            ["• Jika roles kosong, default akan jadi 'user'"],
            ["• Password default sama dengan login_id"]
        ]
        
        for i, instruction in enumerate(instructions, 1):
            instruction_sheet.cell(row=i, column=1, value=instruction[0])
            if i == 1:  # Title
                instruction_sheet.cell(row=i, column=1).font = Font(bold=True, size=14)
        
        # Auto-adjust instruction sheet width
        instruction_sheet.column_dimensions['A'].width = 80
        
        # Save template
        template_name = f"user_import_template_{uuid.uuid4().hex[:8]}.xlsx"
        template_path = str(TEMP_DIR / template_name)
        workbook.save(template_path)
        
        return {
            "status": "Completed",
            "message": "Template berhasil dibuat",
            "file_path": template_path,
            "filename": template_name
        }
        
    except Exception as e:
        logger.error(f"Failed to generate template: {e}")
        return {
            "status": "Failed",
            "error": str(e)
        }