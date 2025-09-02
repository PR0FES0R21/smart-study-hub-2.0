# ==============================================================================
# File: app/api/v1/routes/question_banks.py (IMPROVED VERSION)
# ==============================================================================
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.api.v1 import deps
from app.crud import crud_question_banks, crud_coordination_assignments, crud_question_submissions
from app.schemas.question_bank import (
    QuestionBankCreate, QuestionBankUpdate, QuestionBankPublic, 
    QuestionIdsList, PaginatedQuestionBankResponse
)
from app.schemas.question_submission import QuestionSubmissionCreate

router = APIRouter()

# ===== BASIC CRUD OPERATIONS =====

@router.post("/", response_model=QuestionBankPublic, status_code=status.HTTP_201_CREATED)
async def create_new_question(
    *,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    question_in: QuestionBankCreate,
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """Membuat soal baru di bank soal. Hanya bisa diakses oleh guru."""
    if question_in.created_by_teacher_id != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Cannot create question for another teacher")
    
    return await crud_question_banks.create_question(db=db, question=question_in)

@router.put("/{question_id}", response_model=QuestionBankPublic)
async def update_existing_question(
    question_id: str,
    question_in: QuestionBankUpdate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """Memperbarui soal. Guru hanya bisa memperbarui soal miliknya sendiri."""
    question = await crud_question_banks.get_question_by_id(db, question_id=question_id)
    if not question or question["created_by_teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Question not found or not owned by user")
    
    return await crud_question_banks.update_question(db=db, question_id=question_id, question_update=question_in)

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_question(
    question_id: str,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher)
):
    """Menghapus soal. Guru hanya bisa menghapus soal miliknya sendiri."""
    question = await crud_question_banks.get_question_by_id(db, question_id=question_id)
    if not question or question["created_by_teacher_id"] != current_user["_id"]:
        raise HTTPException(status_code=404, detail="Question not found or not owned by user")
        
    await crud_question_banks.delete_question(db=db, question_id=question_id)
    return

# ===== COLLABORATION & ACCESS ENDPOINTS =====

@router.get("/my-questions", response_model=PaginatedQuestionBankResponse)
async def get_my_questions(
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    question_type: Optional[str] = Query(None, description="Filter by question type (multiple_choice/essay)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (easy/medium/hard)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in question text, subject name, or tags"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    Mengambil daftar soal yang dibuat oleh guru yang sedang login dengan sistem pagination,
    filtering, dan pencarian. Menggunakan strategi caching untuk performa yang lebih baik.
    """
    teacher_id = str(current_user["_id"])
    skip = (page - 1) * limit
    
    # Build filters dict
    filters = {
        "teacher_id": teacher_id,
        "subject_id": subject_id,
        "question_type": question_type,
        "difficulty": difficulty,
        "status": status
    }
    active_filters = {k: v for k, v in filters.items() if v is not None}
    
    if search:
        # Jika ada pencarian, bypass cache dan query langsung ke DB dengan filter
        result = await crud_question_banks.search_questions_with_details(
            db, 
            search=search, 
            skip=skip, 
            limit=limit,
            filters=active_filters
        )
        data = result["data"]
        total_items = result["total_items"]
    else:
        # Jika tidak ada pencarian, gunakan strategi cache
        all_filtered_ids_str = await crud_question_banks.get_filtered_question_ids(db, active_filters)
        total_items = len(all_filtered_ids_str)
        
        ids_for_page_str = all_filtered_ids_str[skip : skip + limit]
        ids_for_page_obj = [ObjectId(id_str) for id_str in ids_for_page_str]
        
        data = await crud_question_banks.get_questions_details_by_ids(db, question_ids=ids_for_page_obj)
    
    total_pages = (total_items + limit - 1) // limit
    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": data
    }

@router.get("/accessible", response_model=PaginatedQuestionBankResponse)
async def get_accessible_questions(
    purpose: Optional[str] = Query(None, description="Filter by purpose (e.g., 'UTS 2025')"),
    subject_id: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    search: Optional[str] = Query(None, description="Search in question text, subject name, or tags"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    active_period: dict = Depends(deps.get_current_academic_period)
):
    """
    Mengambil semua soal yang bisa diakses oleh user:
    1. Soal milik sendiri (semua)
    2. Jika koordinator: soal yang di-submit ke koordinasi dia
    """
    teacher_id = current_user["_id"]
    period_id = active_period["_id"]
    accessible_questions = {}  # Dict untuk avoid duplikasi
    
    # 1. SELALU ambil soal milik sendiri
    my_questions_filter = {"created_by_teacher_id": teacher_id}
    
    # Apply subject filter jika ada
    if subject_id and ObjectId.is_valid(subject_id):
        my_questions_filter["subject_id"] = ObjectId(subject_id)
    
    my_questions = await db["question_banks"].find(my_questions_filter).to_list(None)
    
    for q in my_questions:
        accessible_questions[str(q["_id"])] = {
            **q,
            "source": "own",
            "access_reason": "owner"
        }
    
    # 2. CEK apakah user adalah koordinator (pake function yang sama kayak /for-review)
    coordinations = await crud_coordination_assignments.get_coordinations_by_user(db, teacher_id, period_id)
    
    # Apply filters untuk koordinasi jika ada
    if coordinations and (subject_id or grade_level):
        filtered_coordinations = []
        for coord in coordinations:
            include_coord = True
            
            if subject_id and ObjectId.is_valid(subject_id):
                if coord["subject_id"] != ObjectId(subject_id):
                    include_coord = False
            
            if grade_level and coord.get("grade_level") != grade_level:
                include_coord = False
                
            if include_coord:
                filtered_coordinations.append(coord)
        
        coordinations = filtered_coordinations
    
    if coordinations:
        # User adalah koordinator, ambil soal yang di-submit ke dia
        coordination_ids = [coord["_id"] for coord in coordinations]
        
        # Apply purpose filter - kalau purpose None, ambil semua
        if not purpose:
            # Kalau nggak ada purpose, ambil semua submissions dengan status submitted
            all_submissions = []
            for coord_id in coordination_ids:
                submissions = await crud_question_submissions.get_submissions_for_coordinator(
                    db, [coord_id], "", "submitted"  # Purpose kosong untuk ambil semua
                )
                all_submissions.extend(submissions)
            submitted_questions = all_submissions
        else:
            # Pake function yang sama kayak /for-review
            submitted_questions = await crud_question_submissions.get_submissions_for_coordinator(
                db, coordination_ids, purpose, "submitted"
            )
        
        for sq in submitted_questions:
            question = sq["question_details"]
            submission = sq
            
            question_key = str(question["_id"])
            
            # Jangan overwrite soal milik sendiri
            if question_key not in accessible_questions:
                accessible_questions[question_key] = {
                    **question,
                    "source": "submitted_to_coordination",
                    "access_reason": "coordinator",
                    "submission_id": submission["_id"],
                    "submission_status": submission["status"],
                    "submitted_by_teacher_id": submission["submitted_by_teacher_id"],
                    "purpose": submission["purpose"],
                    "submitted_at": submission["created_at"]
                }
    
    # 3. Apply grade_level filter jika diperlukan
    result_questions = list(accessible_questions.values())
    
    # Filter grade_level butuh logic khusus karena question_banks tidak punya grade_level langsung
    if grade_level:
        filtered_questions = []
        
        for q in result_questions:
            include_question = False
            
            if q.get("source") == "own":
                # Untuk soal milik sendiri, cek apakah user mengajar di grade_level tersebut
                # dengan subject_id yang sama
                teaching_check = await db["teaching_assignments"].find_one({
                    "teacher_id": teacher_id,
                    "academic_period_id": period_id,
                    "subject_id": q["subject_id"]
                })
                
                if teaching_check:
                    # Ambil class details untuk cek grade_level
                    class_details = await db["classes"].find_one({
                        "_id": teaching_check["class_id"]
                    })
                    
                    if class_details and class_details.get("grade_level") == grade_level:
                        include_question = True
            
            elif q.get("source") == "submitted_to_coordination":
                # Untuk soal yang di-submit, cek coordination assignment
                for coord in coordinations:
                    if coord.get("grade_level") == grade_level and coord["subject_id"] == q["subject_id"]:
                        include_question = True
                        break
            
            if include_question:
                filtered_questions.append(q)
        
        result_questions = filtered_questions
    
    # Apply search filter jika ada
    if search:
        search_filtered = []
        for q in result_questions:
            if (search.lower() in q.get("question_text", "").lower() or
                search.lower() in q.get("subject_details", {}).get("name", "").lower() or
                any(search.lower() in tag.lower() for tag in q.get("tags", []))):
                search_filtered.append(q)
        result_questions = search_filtered
    
    # Apply pagination
    total_items = len(result_questions)
    skip = (page - 1) * limit
    paginated_questions = result_questions[skip:skip + limit]
    
    total_pages = (total_items + limit - 1) // limit
    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
        "data": paginated_questions
    }

@router.post("/by-ids", response_model=List[QuestionBankPublic])
async def read_questions_by_ids(
    ids_in: QuestionIdsList,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_user)
):
    """Mengambil detail beberapa soal berdasarkan daftar ID yang diberikan."""
    questions = await crud_question_banks.get_questions_by_ids(db, question_ids=ids_in.ids)
    return questions

# ===== SUBMISSION WORKFLOW =====

@router.post("/submit-for-review", status_code=status.HTTP_201_CREATED)
async def submit_questions_for_review(
    submission_in: QuestionSubmissionCreate,
    db: AsyncIOMotorDatabase = Depends(deps.get_database),
    current_user: dict = Depends(deps.get_current_active_teacher),
    active_period: dict = Depends(deps.get_current_academic_period)
):
    """Guru mengajukan soal-soal dari bank soalnya untuk direview oleh koordinator."""
    # Validasi: Pastikan koordinator yang dituju benar-benar ada
    coord_assignment = await db["coordination_assignments"].find_one({
        "_id": submission_in.coordination_assignment_id
    })
    if not coord_assignment:
        raise HTTPException(status_code=404, detail="Coordination assignment not found.")

    # Validasi: Pastikan semua soal yang di-submit adalah milik user
    question_ids = submission_in.question_ids
    my_questions = await crud_question_banks.get_questions_by_ids(db, question_ids)
    
    for question in my_questions:
        if question["created_by_teacher_id"] != current_user["_id"]:
            raise HTTPException(
                status_code=403, 
                detail=f"Question {question['_id']} is not owned by you"
            )

    # Buat dokumen submission untuk setiap soal
    submissions_to_create = []
    for q_id in question_ids:
        submissions_to_create.append({
            "question_id": q_id,
            "submitted_by_teacher_id": current_user["_id"],
            "coordination_assignment_id": submission_in.coordination_assignment_id,
            "academic_period_id": ObjectId(active_period["_id"]),
            "purpose": submission_in.purpose,
            "status": "submitted",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    await crud_question_submissions.create_submissions(db, submissions_to_create)
    return {"message": f"{len(submissions_to_create)} question(s) submitted for review."}