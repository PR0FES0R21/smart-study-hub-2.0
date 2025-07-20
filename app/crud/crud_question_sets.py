from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId
from app.schemas.question_set import QuestionSetCreate, QuestionSetUpdate

async def create_question_set(db: AsyncIOMotorDatabase, qset: QuestionSetCreate) -> dict:
    qset_dict = qset.model_dump(mode='python')
    result = await db["question_sets"].insert_one(qset_dict)
    return await db["question_sets"].find_one({"_id": result.inserted_id})

async def get_question_sets(db: AsyncIOMotorDatabase, subject_id: ObjectId, grade_level: int) -> List[dict]:
    return await db["question_sets"].find({"subject_id": subject_id, "grade_level": grade_level}).to_list(None)
