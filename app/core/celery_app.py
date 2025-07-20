# ==============================================================================
# File: app/core/celery_app.py
# Deskripsi: Konfigurasi instance Celery.
# --- DITAMBAHKAN ---
# ==============================================================================
from celery import Celery
from .config import settings

# Membuat instance Celery
# Broker: Tempat Celery mendapatkan tugas (kita pakai Redis)
# Backend: Tempat Celery menyimpan hasil tugas (kita pakai Redis juga)
celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Konfigurasi Celery
celery_app.conf.update(
    task_track_started=True,
    # Menemukan semua file tasks.py secara otomatis
    imports=('app.tasks.excel_tasks', 'app.tasks.analytics_tasks', 'app.tasks.bulk_operations_tasks',) 
)