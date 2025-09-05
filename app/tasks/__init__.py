# ==============================================================================
# File: app/tasks/__init__.py
# Deskripsi: Package init for background tasks
# ==============================================================================

# Import all task modules to register them with Celery
from . import exam_analytics_tasks

__all__ = ['exam_analytics_tasks']
