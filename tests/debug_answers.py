import asyncio
from bson import ObjectId
from app.core.db import db

async def debug_answers():
    session_id = "68b73495b09dfc3016243c46"
    
    session = await db.exam_sessions.find_one({"_id": ObjectId(session_id)})
    
    if session:
        answers = session.get("answers", [])
        print(f"Answers count: {len(answers)}")
        print(f"Answers type: {type(answers)}")
        
        for i, answer in enumerate(answers):
            print(f"\nAnswer {i+1}:")
            print(f"  Type: {type(answer)}")
            if isinstance(answer, dict):
                print(f"  Keys: {list(answer.keys())}")
                for key, value in answer.items():
                    print(f"    {key}: {value} ({type(value)})")
            else:
                print(f"  Value: {answer}")

if __name__ == "__main__":
    asyncio.run(debug_answers())
