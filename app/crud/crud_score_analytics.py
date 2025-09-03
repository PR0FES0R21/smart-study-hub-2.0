# ==============================================================================
# File: app/crud/crud_score_analytics.py
# Deskripsi: CRUD Analitik Nilai untuk Admin/Teacher/Student
# --- DITAMBAHKAN ---
# ==============================================================================
from typing import List, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.cache import get_cache, set_cache
from app.schemas.score_analytics import (
    AdminGlobalStats, AdminDashboard, ExamStatistics,
    TeacherDashboard, TeacherClassStats,
    StudentPersonalDashboard, StudentSubjectPerformance,
    ScoreDistribution
)


# --------------------------
# Cache Keys
# --------------------------
ADMIN_DASHBOARD_CACHE = "score_analytics:admin:dashboard:{period}"
TEACHER_DASHBOARD_CACHE = "score_analytics:teacher:{teacher}:{period}"
STUDENT_DASHBOARD_CACHE = "score_analytics:student:{student}:{period}"


def _build_score_distribution(scores: List[float]) -> List[Dict[str, Any]]:
    """Bangun distribusi skor dalam bucket standar."""
    buckets = [(0, 20), (21, 40), (41, 60), (61, 80), (81, 100)]
    total = len(scores) if scores else 0
    results: List[Dict[str, Any]] = []
    for low, high in buckets:
        count = sum(1 for s in scores if low <= s <= high)
        percentage = round((count / total) * 100, 2) if total > 0 else 0.0
        label = f"{low}-{high}"
        results.append({"range": label, "count": count, "percentage": percentage})
    return results


async def get_admin_dashboard(db: AsyncIOMotorDatabase, academic_period_id: str) -> Dict[str, Any]:
    """Admin dashboard ringkas: global stats + 5 ujian terbaru."""
    cache_key = ADMIN_DASHBOARD_CACHE.format(period=academic_period_id)
    cached = await get_cache(cache_key)
    if cached: return cached

    period_obj = ObjectId(academic_period_id)

    # Cari 5 ujian terbaru di periode ini
    exams_cursor = db["exams"].find({"academic_period_id": period_obj}).sort("updated_at", -1).limit(5)
    recent_exams = await exams_cursor.to_list(5)

    exam_stats: List[Dict[str, Any]] = []
    total_students_participated = 0
    sum_all_scores = 0.0
    sum_all_counts = 0

    for exam in recent_exams:
        sessions = await db["exam_sessions"].find({"exam_id": exam["_id"], "status": "graded"}).to_list(10000)
        scores = [s.get("score", 0) for s in sessions]
        participants = len(scores)
        total_students_participated += participants
        if participants > 0:
            avg = sum(scores) / participants
            hi = max(scores)
            lo = min(scores)
        else:
            avg, hi, lo = 0.0, 0.0, 0.0
        sum_all_scores += sum(scores)
        sum_all_counts += participants

        # Dapatkan subject_name via teaching_assignment -> subjects
        subject_name = ""
        assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
        if assignment:
            subject = await db["subjects"].find_one({"_id": assignment["subject_id"]})
            subject_name = subject.get("name") if subject else ""

        exam_stats.append({
            "exam_id": exam["_id"],
            "exam_title": exam.get("title", "-"),
            "exam_type": exam.get("exam_type", "-"),
            "subject_name": subject_name,
            "total_participants": participants,
            "average_score": round(avg, 2),
            "highest_score": round(hi, 2),
            "lowest_score": round(lo, 2),
            "score_distribution": _build_score_distribution(scores),
            "exam_date": exam.get("availability_start_time"),
        })

    school_wide_average = round((sum_all_scores / sum_all_counts), 2) if sum_all_counts > 0 else 0.0

    result = {
        "global_stats": {
            "total_exams_conducted": await db["exams"].count_documents({"academic_period_id": period_obj}),
            "total_students_participated": total_students_participated,
            "school_wide_average": school_wide_average,
        },
        "recent_exams": exam_stats,
    }

    await set_cache(cache_key, result, ttl=1800)
    return result


async def get_teacher_dashboard(db: AsyncIOMotorDatabase, teacher_id: ObjectId, academic_period_id: str) -> Dict[str, Any]:
    cache_key = TEACHER_DASHBOARD_CACHE.format(teacher=teacher_id, period=academic_period_id)
    cached = await get_cache(cache_key)
    if cached: return cached

    period_obj = ObjectId(academic_period_id)

    # Ambil teaching assignments milik guru ini pada periode terkait
    assignments = await db["teaching_assignments"].find({
        "teacher_id": teacher_id,
        "academic_period_id": period_obj
    }).to_list(1000)

    class_stats: List[Dict[str, Any]] = []

    for a in assignments:
        class_doc = await db["classes"].find_one({"_id": a["class_id"]})
        subject_doc = await db["subjects"].find_one({"_id": a["subject_id"]})
        class_name = f"{class_doc.get('grade_level')} {class_doc.get('name')}" if class_doc else "-"
        subject_name = subject_doc.get("name") if subject_doc else "-"

        # Cari exams untuk assignment ini
        exam_ids = [e["_id"] for e in await db["exams"].find({"teaching_assignment_id": a["_id"]}).to_list(1000)]
        sessions = []
        if exam_ids:
            sessions = await db["exam_sessions"].find({"exam_id": {"$in": exam_ids}, "status": "graded"}).to_list(100000)

        scores = [s.get("score", 0) for s in sessions]
        participants = len(scores)
        avg = (sum(scores) / participants) if participants > 0 else 0.0
        hi = max(scores) if participants > 0 else 0.0
        lo = min(scores) if participants > 0 else 0.0

        # Hitung total siswa kelas dari profiles
        total_students = await db["profiles"].count_documents({"class_id": a["class_id"]})
        completion_rate = round((participants / total_students) * 100, 2) if total_students > 0 else 0.0

        class_stats.append({
            "class_id": a["class_id"],
            "class_name": class_name,
            "subject_name": subject_name,
            "total_students": total_students,
            "average_score": round(avg, 2),
            "highest_score": round(hi, 2),
            "lowest_score": round(lo, 2),
            "completion_rate": completion_rate,
        })

    result = {
        "teacher_id": ObjectId(teacher_id),
        "class_statistics": class_stats
    }

    await set_cache(cache_key, result, ttl=1800)
    return result


async def get_student_dashboard(db: AsyncIOMotorDatabase, student_id: str, academic_period_id: str) -> Dict[str, Any]:
    cache_key = STUDENT_DASHBOARD_CACHE.format(student=student_id, period=academic_period_id)
    cached = await get_cache(cache_key)
    if cached: return cached

    student_obj = ObjectId(student_id)

    # Semua sesi ujian yang sudah dinilai untuk siswa ini pada periode ini
    exams_cursor = db["exams"].find({"academic_period_id": ObjectId(academic_period_id)})
    exam_ids = [e["_id"] for e in await exams_cursor.to_list(10000)]
    sessions = await db["exam_sessions"].find({
        "student_id": student_obj,
        "exam_id": {"$in": exam_ids},
        "status": "graded"
    }).to_list(100000)

    # Kelompokkan per mata pelajaran
    subject_scores: Dict[str, List[float]] = {}
    last_scores: Dict[str, float] = {}
    for s in sessions:
        exam = await db["exams"].find_one({"_id": s["exam_id"]})
        if not exam: 
            continue
        assignment = await db["teaching_assignments"].find_one({"_id": exam["teaching_assignment_id"]})
        if not assignment:
            continue
        subject = await db["subjects"].find_one({"_id": assignment["subject_id"]})
        if not subject:
            continue
        key = str(subject["_id"])
        subject_scores.setdefault(key, []).append(s.get("score", 0))
        last_scores[key] = s.get("score", 0)

    subject_performances: List[Dict[str, Any]] = []
    total_scores_flat: List[float] = []
    for subject_id_str, scores in subject_scores.items():
        subject_doc = await db["subjects"].find_one({"_id": ObjectId(subject_id_str)})
        if not subject_doc:
            continue
        exams_taken = len(scores)
        avg = sum(scores) / exams_taken if exams_taken > 0 else 0.0
        hi = max(scores) if exams_taken > 0 else 0.0
        lo = min(scores) if exams_taken > 0 else 0.0
        total_scores_flat.extend(scores)
        subject_performances.append({
            "subject_id": subject_doc["_id"],
            "subject_name": subject_doc.get("name", "-"),
            "exams_taken": exams_taken,
            "average_score": round(avg, 2),
            "highest_score": round(hi, 2),
            "lowest_score": round(lo, 2),
            "last_exam_score": round(last_scores.get(subject_id_str, 0.0), 2),
        })

    overall_average = round((sum(total_scores_flat) / len(total_scores_flat)), 2) if total_scores_flat else 0.0

    # Nama kelas siswa (opsional)
    profile = await db["profiles"].find_one({"user_id": student_obj})
    class_name = None
    if profile:
        class_doc = await db["classes"].find_one({"_id": profile.get("class_id")})
        if class_doc:
            class_name = f"{class_doc.get('grade_level')} {class_doc.get('name')}"

    result = {
        "student_id": student_obj,
        "class_name": class_name,
        "overall_average": overall_average,
        "total_exams_taken": len(total_scores_flat),
        "subject_performances": subject_performances,
    }

    await set_cache(cache_key, result, ttl=1800)
    return result

# ==============================================================================
# File: app/crud/crud_score_analytics.py
# Deskripsi: CRUD functions untuk analitik nilai (Admin, Teacher, Student).
# --- MODUL BARU ---
# ==============================================================================
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from bson import ObjectId
from app.core.cache import get_cache, set_cache
import pymongo
from collections import defaultdict


# ============================================================================
# CACHE KEYS
# ============================================================================
ADMIN_DASHBOARD_CACHE_KEY = "score_analytics:admin:dashboard"
TEACHER_DASHBOARD_CACHE_KEY = "score_analytics:teacher:dashboard"
STUDENT_DASHBOARD_CACHE_KEY = "score_analytics:student:dashboard"
SCORE_DISTRIBUTION_CACHE_KEY = "score_analytics:score_distribution"
SUBJECT_PERFORMANCE_CACHE_KEY = "score_analytics:subject_performance"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def calculate_score_distribution(scores: List[float]) -> List[Dict[str, Any]]:
    """Menghitung distribusi nilai berdasarkan rentang"""
    if not scores:
        return []
    
    ranges = [
        ("0-20", 0, 20),
        ("21-40", 21, 40),
        ("41-60", 41, 60),
        ("61-80", 61, 80),
        ("81-100", 81, 100)
    ]
    
    distribution = []
    total_scores = len(scores)
    
    for range_name, min_val, max_val in ranges:
        count = sum(1 for score in scores if min_val <= score <= max_val)
        percentage = (count / total_scores) * 100 if total_scores > 0 else 0
        distribution.append({
            "range": range_name,
            "count": count,
            "percentage": round(percentage, 2)
        })
    
    return distribution

def calculate_trend(score_history: List[Tuple[datetime, float]], window_size: int = 3) -> str:
    """Menghitung trend performa berdasarkan riwayat nilai"""
    if len(score_history) < 2:
        return "stable"
    
    # Ambil window_size nilai terakhir
    recent_scores = score_history[-window_size:] if len(score_history) >= window_size else score_history
    scores = [score for _, score in recent_scores]
    
    if len(scores) < 2:
        return "stable"
    
    # Hitung trend menggunakan simple linear regression
    n = len(scores)
    x_values = list(range(n))
    
    sum_x = sum(x_values)
    sum_y = sum(scores)
    sum_xy = sum(x * y for x, y in zip(x_values, scores))
    sum_x2 = sum(x * x for x in x_values)
    
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
    
    if slope > 1:
        return "improving"
    elif slope < -1:
        return "declining"
    else:
        return "stable"

def generate_cache_key(prefix: str, **kwargs) -> str:
    """Generate unique cache key"""
    key_parts = [prefix]
    for key, value in sorted(kwargs.items()):
        if value is not None:
            key_parts.append(f"{key}:{value}")
    return ":".join(key_parts)


# ============================================================================
# ADMIN ANALYTICS FUNCTIONS
# ============================================================================
async def get_admin_global_statistics(db: AsyncIOMotorDatabase, academic_period_id: str) -> Dict[str, Any]:
    """Mendapatkan statistik global untuk admin"""
    cache_key = generate_cache_key("admin_global_stats", period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    period_obj_id = ObjectId(academic_period_id)
    
    # Pipeline untuk mendapatkan statistik global
    pipeline = [
        # Match exam sessions yang sudah dinilai
        {"$match": {"status": "graded", "score": {"$ne": None}}},
        
        # Lookup ke exams untuk filter periode akademik
        {"$lookup": {
            "from": "exams",
            "localField": "exam_id",
            "foreignField": "_id",
            "as": "exam_info"
        }},
        {"$unwind": "$exam_info"},
        
        # Filter berdasarkan periode akademik
        {"$match": {"exam_info.academic_period_id": period_obj_id}},
        
        # Group untuk statistik
        {"$group": {
            "_id": None,
            "total_exams": {"$addToSet": "$exam_id"},
            "total_students": {"$addToSet": "$student_id"},
            "total_scores": {"$push": "$score"},
            "total_questions": {"$sum": {"$size": "$answers"}}
        }},
        
        # Project hasil akhir
        {"$project": {
            "_id": 0,
            "total_exams_conducted": {"$size": "$total_exams"},
            "total_students_participated": {"$size": "$total_students"},
            "school_wide_average": {"$avg": "$total_scores"},
            "total_questions_answered": "$total_questions"
        }}
    ]
    
    result = await db["exam_sessions"].aggregate(pipeline).to_list(1)
    
    if not result:
        stats = {
            "total_exams_conducted": 0,
            "total_students_participated": 0,
            "school_wide_average": 0.0,
            "total_questions_answered": 0,
            "active_teachers": 0,
            "active_classes": 0
        }
    else:
        stats = result[0]
        # Tambahkan data teacher dan kelas aktif
        stats["active_teachers"] = await db["teaching_assignments"].distinct("teacher_id", {"academic_period_id": period_obj_id})
        stats["active_classes"] = await db["teaching_assignments"].distinct("class_id", {"academic_period_id": period_obj_id})
        stats["active_teachers"] = len(stats["active_teachers"])
        stats["active_classes"] = len(stats["active_classes"])
        stats["school_wide_average"] = round(stats.get("school_wide_average", 0), 2)
    
    await set_cache(cache_key, stats, ttl=3600)  # Cache 1 jam
    return stats

async def get_admin_grade_performances(db: AsyncIOMotorDatabase, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan performa per tingkat kelas"""
    cache_key = generate_cache_key("admin_grade_performance", period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    period_obj_id = ObjectId(academic_period_id)
    
    pipeline = [
        {"$match": {"status": "graded", "score": {"$ne": None}}},
        
        # Lookup ke exams, teaching_assignments, classes
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "classes", "localField": "assignment.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        # Group berdasarkan grade level dan subject
        {"$group": {
            "_id": {
                "grade_level": "$class.grade_level",
                "subject_name": "$subject.name"
            },
            "average_score": {"$avg": "$score"},
            "exam_count": {"$sum": 1}
        }},
        
        # Group ulang untuk mendapatkan best/worst subject per grade
        {"$group": {
            "_id": "$_id.grade_level",
            "subjects": {"$push": {
                "subject_name": "$_id.subject_name",
                "average_score": "$average_score",
                "exam_count": "$exam_count"
            }},
            "overall_average": {"$avg": "$average_score"},
            "total_exams": {"$sum": "$exam_count"}
        }},
        
        {"$sort": {"_id": 1}}
    ]
    
    results = await db["exam_sessions"].aggregate(pipeline).to_list(100)
    
    performances = []
    for result in results:
        subjects = result["subjects"]
        if subjects:
            best_subject = max(subjects, key=lambda x: x["average_score"])["subject_name"]
            worst_subject = min(subjects, key=lambda x: x["average_score"])["subject_name"]
        else:
            best_subject = "N/A"
            worst_subject = "N/A"
        
        # Hitung total siswa di grade ini
        total_students = await db["profiles"].count_documents({
            "class_id": {"$in": await db["classes"].distinct("_id", {"grade_level": result["_id"]})}
        })
        
        performances.append({
            "grade_level": result["_id"],
            "total_students": total_students,
            "average_score": round(result["overall_average"], 2),
            "total_exams": result["total_exams"],
            "best_subject": best_subject,
            "worst_subject": worst_subject,
            "improvement_trend": "stable"  # TODO: Implement trend calculation
        })
    
    await set_cache(cache_key, performances, ttl=3600)
    return performances

async def get_admin_major_performances(db: AsyncIOMotorDatabase, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan performa per jurusan"""
    cache_key = generate_cache_key("admin_major_performance", period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    period_obj_id = ObjectId(academic_period_id)
    
    pipeline = [
        {"$match": {"status": "graded", "score": {"$ne": None}}},
        
        # Lookup ke exams, teaching_assignments, classes, expertise_programs
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "classes", "localField": "assignment.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        
        {"$lookup": {"from": "expertise_programs", "localField": "class.expertise_id", "foreignField": "_id", "as": "major"}},
        {"$unwind": "$major"},
        
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        # Group berdasarkan major dan grade, subject
        {"$group": {
            "_id": {
                "major_id": "$major._id",
                "major_name": "$major.name",
                "major_abbreviation": "$major.abbreviation",
                "grade_level": "$class.grade_level",
                "subject_name": "$subject.name"
            },
            "average_score": {"$avg": "$score"},
            "student_count": {"$addToSet": "$student_id"}
        }},
        
        # Group ulang berdasarkan major saja
        {"$group": {
            "_id": {
                "major_id": "$_id.major_id",
                "major_name": "$_id.major_name",
                "major_abbreviation": "$_id.major_abbreviation"
            },
            "overall_average": {"$avg": "$average_score"},
            "grade_breakdown": {"$push": {
                "grade_level": "$_id.grade_level",
                "average_score": "$average_score"
            }},
            "subjects": {"$push": {
                "subject_name": "$_id.subject_name",
                "average_score": "$average_score"
            }},
            "total_students": {"$addToSet": "$student_count"}
        }}
    ]
    
    results = await db["exam_sessions"].aggregate(pipeline).to_list(100)
    
    performances = []
    for result in results:
        # Proses grade breakdown
        grade_breakdown = {}
        for item in result["grade_breakdown"]:
            grade_str = str(item["grade_level"])
            if grade_str not in grade_breakdown:
                grade_breakdown[grade_str] = []
            grade_breakdown[grade_str].append(item["average_score"])
        
        # Rata-ratakan per grade
        for grade in grade_breakdown:
            grade_breakdown[grade] = round(sum(grade_breakdown[grade]) / len(grade_breakdown[grade]), 2)
        
        # Cari strongest dan weakest subject
        subjects = result["subjects"]
        if subjects:
            subject_averages = defaultdict(list)
            for subj in subjects:
                subject_averages[subj["subject_name"]].append(subj["average_score"])
            
            # Rata-ratakan per subject
            for subj_name in subject_averages:
                subject_averages[subj_name] = sum(subject_averages[subj_name]) / len(subject_averages[subj_name])
            
            strongest_subject = max(subject_averages.items(), key=lambda x: x[1])[0] if subject_averages else "N/A"
            weakest_subject = min(subject_averages.items(), key=lambda x: x[1])[0] if subject_averages else "N/A"
        else:
            strongest_subject = "N/A"
            weakest_subject = "N/A"
        
        # Hitung total siswa unik
        all_students = set()
        for student_group in result["total_students"]:
            all_students.update(student_group)
        
        performances.append({
            "major_id": result["_id"]["major_id"],
            "major_name": result["_id"]["major_name"],
            "major_abbreviation": result["_id"]["major_abbreviation"],
            "total_students": len(all_students),
            "average_score": round(result["overall_average"], 2),
            "grade_breakdown": grade_breakdown,
            "strongest_subject": strongest_subject,
            "weakest_subject": weakest_subject
        })
    
    await set_cache(cache_key, performances, ttl=3600)
    return performances

async def get_admin_subject_rankings(db: AsyncIOMotorDatabase, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan ranking mata pelajaran"""
    cache_key = generate_cache_key("admin_subject_ranking", period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    period_obj_id = ObjectId(academic_period_id)
    
    pipeline = [
        {"$match": {"status": "graded", "score": {"$ne": None}}},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        {"$group": {
            "_id": {
                "subject_id": "$subject._id",
                "subject_name": "$subject.name"
            },
            "school_average": {"$avg": "$score"},
            "total_exams": {"$sum": 1},
            "total_participants": {"$addToSet": "$student_id"},
            "all_scores": {"$push": "$score"}
        }},
        
        {"$project": {
            "_id": 0,
            "subject_id": "$_id.subject_id",
            "subject_name": "$_id.subject_name",
            "school_average": {"$round": ["$school_average", 2]},
            "total_exams": 1,
            "total_participants": {"$size": "$total_participants"},
            "all_scores": 1
        }},
        
        {"$sort": {"school_average": -1}}
    ]
    
    results = await db["exam_sessions"].aggregate(pipeline).to_list(100)
    
    # Tambahkan ranking dan difficulty rating
    for i, result in enumerate(results):
        result["rank"] = i + 1
        avg_score = result["school_average"]
        
        if avg_score >= 80:
            result["difficulty_rating"] = "Easy"
        elif avg_score >= 60:
            result["difficulty_rating"] = "Medium"
        else:
            result["difficulty_rating"] = "Hard"
    
    await set_cache(cache_key, results, ttl=3600)
    return results

async def get_admin_score_trends(db: AsyncIOMotorDatabase, academic_period_id: str, months: int = 6) -> List[Dict[str, Any]]:
    """Mendapatkan trend nilai dari waktu ke waktu"""
    cache_key = generate_cache_key("admin_score_trends", period=academic_period_id, months=months)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    period_obj_id = ObjectId(academic_period_id)
    
    # Hitung tanggal mulai
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=months * 30)
    
    pipeline = [
        {"$match": {
            "status": "graded",
            "score": {"$ne": None},
            "submitted_at": {"$gte": start_date, "$lte": end_date}
        }},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$project": {
            "score": 1,
            "submitted_at": 1,
            "student_id": 1,
            "year_month": {
                "$dateToString": {
                    "format": "%Y-%m",
                    "date": "$submitted_at"
                }
            }
        }},
        
        {"$group": {
            "_id": "$year_month",
            "average_score": {"$avg": "$score"},
            "total_exams": {"$sum": 1},
            "total_participants": {"$addToSet": "$student_id"}
        }},
        
        {"$project": {
            "_id": 0,
            "period": "$_id",
            "average_score": {"$round": ["$average_score", 2]},
            "total_exams": 1,
            "total_participants": {"$size": "$total_participants"}
        }},
        
        {"$sort": {"period": 1}}
    ]
    
    trends = await db["exam_sessions"].aggregate(pipeline).to_list(100)
    
    await set_cache(cache_key, trends, ttl=3600)
    return trends

async def get_admin_dashboard(db: AsyncIOMotorDatabase, academic_period_id: str) -> Dict[str, Any]:
    """Mendapatkan dashboard lengkap untuk admin"""
    cache_key = generate_cache_key("admin_full_dashboard", period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    # Jalankan semua fungsi secara parallel (conceptually)
    global_stats = await get_admin_global_statistics(db, academic_period_id)
    grade_performances = await get_admin_grade_performances(db, academic_period_id)
    major_performances = await get_admin_major_performances(db, academic_period_id)
    subject_rankings = await get_admin_subject_rankings(db, academic_period_id)
    score_trends = await get_admin_score_trends(db, academic_period_id)
    
    # Ambil ujian terbaru
    recent_exams_pipeline = [
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": ObjectId(academic_period_id)}},
        {"$match": {"status": "graded"}},
        {"$sort": {"submitted_at": -1}},
        {"$limit": 10},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        {"$lookup": {"from": "classes", "localField": "assignment.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        {"$lookup": {"from": "expertise_programs", "localField": "class.expertise_id", "foreignField": "_id", "as": "major"}},
        {"$unwind": "$major"},
        
        {"$group": {
            "_id": "$exam_id",
            "exam_title": {"$first": "$exam.title"},
            "exam_type": {"$first": "$exam.exam_type"},
            "subject_name": {"$first": "$subject.name"},
            "class_name": {"$first": {"$concat": [{"$toString": "$class.grade_level"}, " ", "$major.abbreviation", " ", "$class.name"]}},
            "scores": {"$push": "$score"},
            "exam_date": {"$first": "$submitted_at"},
            "total_participants": {"$sum": 1}
        }},
        
        {"$project": {
            "_id": 0,
            "exam_id": "$_id",
            "exam_title": 1,
            "exam_type": 1,
            "subject_name": 1,
            "class_name": 1,
            "total_participants": 1,
            "average_score": {"$round": [{"$avg": "$scores"}, 2]},
            "highest_score": {"$max": "$scores"},
            "lowest_score": {"$min": "$scores"},
            "exam_date": 1,
            "completion_rate": 100  # TODO: Calculate based on class size
        }}
    ]
    
    recent_exams = await db["exam_sessions"].aggregate(recent_exams_pipeline).to_list(10)
    
    dashboard = {
        "global_stats": global_stats,
        "recent_exams": recent_exams,
        "grade_performances": grade_performances,
        "major_performances": major_performances,
        "subject_rankings": subject_rankings,
        "score_trends": score_trends,
        "generated_at": datetime.utcnow()
    }
    
    await set_cache(cache_key, dashboard, ttl=1800)  # Cache 30 menit
    return dashboard


# ============================================================================
# TEACHER ANALYTICS FUNCTIONS
# ============================================================================
async def get_teacher_class_statistics(db: AsyncIOMotorDatabase, teacher_id: str, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan statistik kelas yang diajar guru"""
    cache_key = generate_cache_key("teacher_class_stats", teacher=teacher_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    teacher_obj_id = ObjectId(teacher_id)
    period_obj_id = ObjectId(academic_period_id)
    
    # Ambil teaching assignments guru
    assignments = await db["teaching_assignments"].find({
        "teacher_id": teacher_obj_id,
        "academic_period_id": period_obj_id
    }).to_list(100)
    
    if not assignments:
        return []
    
    assignment_ids = [a["_id"] for a in assignments]
    
    pipeline = [
        {"$match": {"status": "graded", "score": {"$ne": None}}},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.teaching_assignment_id": {"$in": assignment_ids}}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "classes", "localField": "assignment.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        {"$lookup": {"from": "expertise_programs", "localField": "class.expertise_id", "foreignField": "_id", "as": "major"}},
        {"$unwind": "$major"},
        
        {"$group": {
            "_id": {
                "class_id": "$class._id",
                "subject_id": "$subject._id"
            },
            "class_name": {"$first": {"$concat": [{"$toString": "$class.grade_level"}, " ", "$major.abbreviation", " ", "$class.name"]}},
            "subject_name": {"$first": "$subject.name"},
            "scores": {"$push": "$score"},
            "student_ids": {"$addToSet": "$student_id"}
        }},
        
        {"$project": {
            "_id": 0,
            "class_id": "$_id.class_id",
            "class_name": 1,
            "subject_name": 1,
            "total_students": {"$size": "$student_ids"},
            "average_score": {"$round": [{"$avg": "$scores"}, 2]},
            "highest_score": {"$max": "$scores"},
            "lowest_score": {"$min": "$scores"},
            "completion_rate": 100,  # TODO: Calculate based on actual class size
            "needs_attention_count": {
                "$size": {
                    "$filter": {
                        "input": "$scores",
                        "cond": {"$lt": ["$$this", 60]}
                    }
                }
            }
        }}
    ]
    
    class_stats = await db["exam_sessions"].aggregate(pipeline).to_list(100)
    
    await set_cache(cache_key, class_stats, ttl=3600)
    return class_stats

async def get_teacher_student_performances(db: AsyncIOMotorDatabase, teacher_id: str, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan performa individual siswa untuk guru"""
    cache_key = generate_cache_key("teacher_student_performance", teacher=teacher_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    teacher_obj_id = ObjectId(teacher_id)
    period_obj_id = ObjectId(academic_period_id)
    
    # Ambil teaching assignments guru
    assignments = await db["teaching_assignments"].find({
        "teacher_id": teacher_obj_id,
        "academic_period_id": period_obj_id
    }).to_list(100)
    
    if not assignments:
        return []
    
    assignment_ids = [a["_id"] for a in assignments]
    
    pipeline = [
        {"$match": {"status": "graded", "score": {"$ne": None}}},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.teaching_assignment_id": {"$in": assignment_ids}}},
        
        {"$lookup": {"from": "users", "localField": "student_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        
        {"$lookup": {"from": "profiles", "localField": "user.profile_id", "foreignField": "_id", "as": "profile"}},
        {"$unwind": "$profile"},
        
        {"$lookup": {"from": "classes", "localField": "profile.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        
        {"$lookup": {"from": "expertise_programs", "localField": "class.expertise_id", "foreignField": "_id", "as": "major"}},
        {"$unwind": "$major"},
        
        {"$group": {
            "_id": "$student_id",
            "student_name": {"$first": "$profile.full_name"},
            "class_name": {"$first": {"$concat": [{"$toString": "$class.grade_level"}, " ", "$major.abbreviation", " ", "$class.name"]}},
            "scores": {"$push": {"score": "$score", "date": "$submitted_at"}},
            "total_exams": {"$sum": 1}
        }},
        
        {"$project": {
            "_id": 0,
            "student_id": "$_id",
            "student_name": 1,
            "class_name": 1,
            "total_exams_taken": "$total_exams",
            "average_score": {"$round": [{"$avg": "$scores.score"}, 2]},
            "last_exam_score": {"$arrayElemAt": [{"$slice": [{"$map": {"input": {"$sortArray": {"input": "$scores", "sortBy": {"date": -1}}}, "as": "s", "in": "$$s.score"}}, 1]}, 0]},
            "subject_specific_average": {"$round": [{"$avg": "$scores.score"}, 2]},
            "needs_attention": {"$lt": [{"$avg": "$scores.score"}, 60]},
            "trend": "stable"  # TODO: Calculate actual trend
        }}
    ]
    
    student_performances = await db["exam_sessions"].aggregate(pipeline).to_list(1000)
    
    await set_cache(cache_key, student_performances, ttl=3600)
    return student_performances

async def get_teacher_exam_analysis(db: AsyncIOMotorDatabase, exam_id: str) -> Dict[str, Any]:
    """Mendapatkan analisis mendalam untuk satu ujian"""
    cache_key = generate_cache_key("teacher_exam_analysis", exam=exam_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    exam_obj_id = ObjectId(exam_id)
    
    # Analisis dasar ujian
    pipeline = [
        {"$match": {"exam_id": exam_obj_id, "status": "graded"}},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "classes", "localField": "assignment.class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        
        {"$lookup": {"from": "expertise_programs", "localField": "class.expertise_id", "foreignField": "_id", "as": "major"}},
        {"$unwind": "$major"},
        
        {"$lookup": {"from": "users", "localField": "student_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        
        {"$lookup": {"from": "profiles", "localField": "user.profile_id", "foreignField": "_id", "as": "profile"}},
        {"$unwind": "$profile"},
        
        {"$group": {
            "_id": "$exam_id",
            "exam_title": {"$first": "$exam.title"},
            "class_name": {"$first": {"$concat": [{"$toString": "$class.grade_level"}, " ", "$major.abbreviation", " ", "$class.name"]}},
            "participants": {"$sum": 1},
            "average_score": {"$avg": "$score"},
            "scores": {"$push": "$score"},
            "students": {"$push": {
                "name": "$profile.full_name",
                "score": "$score"
            }},
            "answers": {"$push": "$answers"}
        }},
        
        {"$project": {
            "_id": 0,
            "exam_id": "$_id",
            "exam_title": 1,
            "class_name": 1,
            "participants": 1,
            "average_score": {"$round": ["$average_score", 2]},
            "scores": 1,
            "students": 1,
            "answers": 1
        }}
    ]
    
    result = await db["exam_sessions"].aggregate(pipeline).to_list(1)
    
    if not result:
        return {}
    
    exam_analysis = result[0]
    
    # Urutkan siswa berdasarkan score
    students = sorted(exam_analysis["students"], key=lambda x: x["score"], reverse=True)
    
    # Ambil top dan low performers
    exam_analysis["top_performers"] = [s["name"] for s in students[:3]]
    exam_analysis["low_performers"] = [s["name"] for s in students if s["score"] < 60]
    
    # TODO: Implementasi question analytics yang lebih detail
    exam_analysis["question_analytics"] = []
    exam_analysis["difficult_questions"] = []
    
    await set_cache(cache_key, exam_analysis, ttl=3600)
    return exam_analysis

async def get_teacher_dashboard(db: AsyncIOMotorDatabase, teacher_id: str, academic_period_id: str) -> Dict[str, Any]:
    """Mendapatkan dashboard lengkap untuk guru"""
    cache_key = generate_cache_key("teacher_full_dashboard", teacher=teacher_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    # Ambil data teacher
    teacher = await db["users"].find_one({"_id": ObjectId(teacher_id)})
    if not teacher:
        return {}
    
    teacher_profile = await db["profiles"].find_one({"_id": teacher["profile_id"]})
    teacher_name = teacher_profile["full_name"] if teacher_profile else "Unknown"
    
    # Jalankan fungsi analytics
    class_statistics = await get_teacher_class_statistics(db, teacher_id, academic_period_id)
    student_performances = await get_teacher_student_performances(db, teacher_id, academic_period_id)
    
    # Ambil subject summaries
    teacher_obj_id = ObjectId(teacher_id)
    period_obj_id = ObjectId(academic_period_id)
    
    subject_pipeline = [
        {"$match": {"teacher_id": teacher_obj_id, "academic_period_id": period_obj_id}},
        
        {"$lookup": {"from": "subjects", "localField": "subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        {"$lookup": {"from": "classes", "localField": "class_id", "foreignField": "_id", "as": "class"}},
        {"$unwind": "$class"},
        
        {"$lookup": {"from": "expertise_programs", "localField": "class.expertise_id", "foreignField": "_id", "as": "major"}},
        {"$unwind": "$major"},
        
        {"$group": {
            "_id": "$subject_id",
            "subject_name": {"$first": "$subject.name"},
            "classes": {"$push": {"$concat": [{"$toString": "$class.grade_level"}, " ", "$major.abbreviation", " ", "$class.name"]}},
            "class_ids": {"$addToSet": "$class_id"}
        }},
        
        {"$project": {
            "_id": 0,
            "subject_id": "$_id",
            "subject_name": 1,
            "total_classes": {"$size": "$classes"},
            "total_students": 0,  # TODO: Calculate from profiles
            "overall_average": 0,  # TODO: Calculate from exam_sessions
            "best_class": {"$arrayElemAt": ["$classes", 0]},
            "challenging_class": {"$arrayElemAt": ["$classes", -1]}
        }}
    ]
    
    subject_summaries = await db["teaching_assignments"].aggregate(subject_pipeline).to_list(100)
    
    # Filter students yang perlu perhatian
    students_need_attention = [s for s in student_performances if s.get("needs_attention", False)]
    
    dashboard = {
        "teacher_id": ObjectId(teacher_id),
        "teacher_name": teacher_name,
        "subject_summaries": subject_summaries,
        "class_statistics": class_statistics,
        "recent_exam_analyses": [],  # TODO: Implement
        "students_need_attention": students_need_attention,
        "generated_at": datetime.utcnow()
    }
    
    await set_cache(cache_key, dashboard, ttl=1800)
    return dashboard


# ============================================================================
# STUDENT ANALYTICS FUNCTIONS
# ============================================================================
async def get_student_subject_performances(db: AsyncIOMotorDatabase, student_id: str, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan performa siswa per mata pelajaran"""
    cache_key = generate_cache_key("student_subject_performance", student=student_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    student_obj_id = ObjectId(student_id)
    period_obj_id = ObjectId(academic_period_id)
    
    pipeline = [
        {"$match": {"student_id": student_obj_id, "status": "graded", "score": {"$ne": None}}},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        {"$lookup": {"from": "users", "localField": "assignment.teacher_id", "foreignField": "_id", "as": "teacher_user"}},
        {"$unwind": "$teacher_user"},
        
        {"$lookup": {"from": "profiles", "localField": "teacher_user.profile_id", "foreignField": "_id", "as": "teacher_profile"}},
        {"$unwind": "$teacher_profile"},
        
        {"$group": {
            "_id": "$subject._id",
            "subject_name": {"$first": "$subject.name"},
            "teacher_name": {"$first": "$teacher_profile.full_name"},
            "scores": {"$push": {"score": "$score", "date": "$submitted_at"}},
            "exams_taken": {"$sum": 1}
        }},
        
        {"$project": {
            "_id": 0,
            "subject_id": "$_id",
            "subject_name": 1,
            "teacher_name": 1,
            "exams_taken": 1,
            "average_score": {"$round": [{"$avg": "$scores.score"}, 2]},
            "highest_score": {"$max": "$scores.score"},
            "lowest_score": {"$min": "$scores.score"},
            "last_exam_score": {"$arrayElemAt": [{"$slice": [{"$map": {"input": {"$sortArray": {"input": "$scores", "sortBy": {"date": -1}}}, "as": "s", "in": "$$s.score"}}, 1]}, 0]},
            "class_average": {"$literal": 0},
            "improvement_trend": {"$literal": "stable"}
        }}
    ]
    
    subject_performances = await db["exam_sessions"].aggregate(pipeline).to_list(100)
    
    await set_cache(cache_key, subject_performances, ttl=3600)
    return subject_performances

async def get_student_exam_history(db: AsyncIOMotorDatabase, student_id: str, academic_period_id: str) -> List[Dict[str, Any]]:
    """Mendapatkan riwayat ujian siswa"""
    cache_key = generate_cache_key("student_exam_history", student=student_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    student_obj_id = ObjectId(student_id)
    period_obj_id = ObjectId(academic_period_id)
    
    pipeline = [
        {"$match": {"student_id": student_obj_id, "status": "graded", "score": {"$ne": None}}},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$lookup": {"from": "teaching_assignments", "localField": "exam.teaching_assignment_id", "foreignField": "_id", "as": "assignment"}},
        {"$unwind": "$assignment"},
        
        {"$lookup": {"from": "subjects", "localField": "assignment.subject_id", "foreignField": "_id", "as": "subject"}},
        {"$unwind": "$subject"},
        
        {"$lookup": {"from": "users", "localField": "assignment.teacher_id", "foreignField": "_id", "as": "teacher_user"}},
        {"$unwind": "$teacher_user"},
        
        {"$lookup": {"from": "profiles", "localField": "teacher_user.profile_id", "foreignField": "_id", "as": "teacher_profile"}},
        {"$unwind": "$teacher_profile"},
        
        {"$project": {
            "_id": 0,
            "exam_id": "$exam_id",
            "exam_title": "$exam.title",
            "subject_name": "$subject.name",
            "teacher_name": "$teacher_profile.full_name",
            "score": 1,
            "exam_date": "$submitted_at",
            "exam_type": "$exam.exam_type",
            "class_average": {"$literal": 0},
            "ranking_in_class": {"$literal": 0},
            "total_classmates": {"$literal": 0},
            "time_spent": {
                "$round": [
                    {"$divide": [
                        {"$subtract": ["$submitted_at", "$started_at"]},
                        60000  # Convert to minutes
                    ]}, 0
                ]
            }
        }},
        
        {"$sort": {"exam_date": -1}}
    ]
    
    exam_history = await db["exam_sessions"].aggregate(pipeline).to_list(1000)
    
    await set_cache(cache_key, exam_history, ttl=3600)
    return exam_history

async def get_student_class_comparison(db: AsyncIOMotorDatabase, student_id: str, academic_period_id: str) -> Dict[str, Any]:
    """Mendapatkan perbandingan siswa dengan teman sekelas"""
    cache_key = generate_cache_key("student_class_comparison", student=student_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    student_obj_id = ObjectId(student_id)
    period_obj_id = ObjectId(academic_period_id)
    
    # Ambil class_id siswa
    student_user = await db["users"].find_one({"_id": student_obj_id})
    if not student_user:
        return {}
    
    student_profile = await db["profiles"].find_one({"_id": student_user["profile_id"]})
    if not student_profile:
        return {}
    
    class_id = student_profile["class_id"]
    
    # Ambil semua siswa di kelas yang sama
    classmates_pipeline = [
        {"$match": {"class_id": class_id}},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$match": {"user.roles": "student"}},
        {"$project": {"user_id": "$user._id"}}
    ]
    
    classmates = await db["profiles"].aggregate(classmates_pipeline).to_list(1000)
    classmate_ids = [c["user_id"] for c in classmates]
    
    # Hitung rata-rata kelas dan ranking siswa
    class_scores_pipeline = [
        {"$match": {
            "student_id": {"$in": classmate_ids},
            "status": "graded",
            "score": {"$ne": None}
        }},
        
        {"$lookup": {"from": "exams", "localField": "exam_id", "foreignField": "_id", "as": "exam"}},
        {"$unwind": "$exam"},
        {"$match": {"exam.academic_period_id": period_obj_id}},
        
        {"$group": {
            "_id": "$student_id",
            "average_score": {"$avg": "$score"}
        }},
        
        {"$sort": {"average_score": -1}}
    ]
    
    class_averages = await db["exam_sessions"].aggregate(class_scores_pipeline).to_list(1000)
    
    # Cari posisi siswa
    student_ranking = 0
    student_average = 0
    class_total_average = 0
    
    for i, student_data in enumerate(class_averages):
        if student_data["_id"] == student_obj_id:
            student_ranking = i + 1
            student_average = student_data["average_score"]
            break
    
    if class_averages:
        class_total_average = sum(s["average_score"] for s in class_averages) / len(class_averages)
    
    # Hitung persentil
    total_classmates = len(class_averages)
    percentile = ((total_classmates - student_ranking + 1) / total_classmates) * 100 if total_classmates > 0 else 0
    
    comparison = {
        "student_average": round(student_average, 2),
        "class_average": round(class_total_average, 2),
        "student_ranking": student_ranking,
        "total_classmates": total_classmates,
        "percentile": round(percentile, 2),
        "subjects_above_average": [],  # TODO: Calculate per subject
        "subjects_below_average": []   # TODO: Calculate per subject
    }
    
    await set_cache(cache_key, comparison, ttl=3600)
    return comparison

async def get_student_dashboard(db: AsyncIOMotorDatabase, student_id: str, academic_period_id: str) -> Dict[str, Any]:
    """Mendapatkan dashboard personal untuk siswa"""
    cache_key = generate_cache_key("student_full_dashboard", student=student_id, period=academic_period_id)
    cached_data = await get_cache(cache_key)
    if cached_data:
        return cached_data
    
    # Ambil data siswa
    student = await db["users"].find_one({"_id": ObjectId(student_id)})
    if not student:
        return {}
    
    student_profile = await db["profiles"].find_one({"_id": student["profile_id"]})
    if not student_profile:
        return {}
    
    # Ambil nama kelas
    student_class = await db["classes"].find_one({"_id": student_profile["class_id"]})
    if student_class:
        major = await db["expertise_programs"].find_one({"_id": student_class["expertise_id"]})
        class_name = f"{student_class['grade_level']} {major['abbreviation'] if major else ''} {student_class['name']}"
    else:
        class_name = "Unknown"
    
    # Ambil periode akademik
    period = await db["academic_periods"].find_one({"_id": ObjectId(academic_period_id)})
    academic_period_name = f"{period['year']} {period['semester']}" if period else "Unknown"
    
    # Jalankan fungsi analytics
    subject_performances = await get_student_subject_performances(db, student_id, academic_period_id)
    exam_history = await get_student_exam_history(db, student_id, academic_period_id)
    class_comparison = await get_student_class_comparison(db, student_id, academic_period_id)
    
    # Hitung statistik keseluruhan
    if exam_history:
        overall_average = sum(e["score"] for e in exam_history) / len(exam_history)
        total_exams = len(exam_history)
    else:
        overall_average = 0
        total_exams = 0
    
    # Analisis kekuatan dan kelemahan
    if subject_performances:
        sorted_subjects = sorted(subject_performances, key=lambda x: x["average_score"], reverse=True)
        strongest_subjects = [s["subject_name"] for s in sorted_subjects[:3]]
        weakest_subjects = [s["subject_name"] for s in sorted_subjects[-3:]]
    else:
        strongest_subjects = []
        weakest_subjects = []
    
    strength_weakness = {
        "strongest_subjects": strongest_subjects,
        "weakest_subjects": weakest_subjects,
        "most_improved_subject": None,  # TODO: Calculate
        "needs_focus_subjects": [s["subject_name"] for s in subject_performances if s["average_score"] < 60],
        "consistency_rating": "Consistent"  # TODO: Calculate
    }
    
    # Generate improvement suggestions
    improvement_suggestions = []
    if weakest_subjects:
        improvement_suggestions.append(f"Fokus lebih pada mata pelajaran: {', '.join(weakest_subjects[:2])}")
    if overall_average < 75:
        improvement_suggestions.append("Tingkatkan waktu belajar dan latihan soal")
    if class_comparison.get("student_ranking", 0) > class_comparison.get("total_classmates", 1) * 0.5:
        improvement_suggestions.append("Bergabung dengan kelompok belajar untuk meningkatkan performa")
    
    dashboard = {
        "student_id": ObjectId(student_id),
        "student_name": student_profile["full_name"],
        "class_name": class_name,
        "academic_period": academic_period_name,
        "overall_statistics": {
            "total_exams_taken": total_exams,
            "overall_average": round(overall_average, 2),
            "best_score": max((e["score"] for e in exam_history), default=0),
            "latest_score": exam_history[0]["score"] if exam_history else 0
        },
        "subject_performances": subject_performances,
        "exam_history": exam_history[:10],  # Limit to 10 most recent
        "class_comparison": class_comparison,
        "strength_weakness": strength_weakness,
        "goal_tracking": None,  # TODO: Implement goal tracking
        "improvement_suggestions": improvement_suggestions,
        "generated_at": datetime.utcnow()
    }
    
    await set_cache(cache_key, dashboard, ttl=1800)
    return dashboard


# ============================================================================
# ADDITIONAL UTILITY FUNCTIONS
# ============================================================================
async def get_class_ranking(db: AsyncIOMotorDatabase, student_id: str, class_id: str, academic_period_id: str) -> Tuple[int, int]:
    """Mendapatkan ranking siswa dalam kelas"""
    # TODO: Implement detailed ranking calculation
    return (0, 0)

async def generate_improvement_suggestions(db: AsyncIOMotorDatabase, student_id: str) -> List[str]:
    """Generate saran perbaikan untuk siswa"""
    # TODO: Implement AI-based suggestions
    return [
        "Tingkatkan konsistensi belajar harian",
        "Fokus pada pemahaman konsep dasar",
        "Latihan soal lebih banyak pada mata pelajaran yang lemah"
    ]

async def invalidate_score_analytics_cache(academic_period_id: str, student_id: Optional[str] = None, teacher_id: Optional[str] = None):
    """Invalidate cache when new scores are added"""
    # TODO: Implement cache invalidation logic
    pass
