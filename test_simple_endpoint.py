#!/usr/bin/env python3
"""
Simple test to show the new endpoint structure
"""

print("🚀 New Question Set Questions Endpoint")
print("=" * 50)
print()
print("📍 Endpoint: GET /api/v1/question-sets/{question_set_id}/questions")
print()
print("📋 Example Response:")
print("""
{
  "question_set_id": "689ef2b43e2daffae0f4ebeb",
  "question_set_name": "UTS Ganjil 2024 S1 hehe",
  "total_questions": 7,
  "question_ids": [
    "688c844bfcc1873a29ed958a",
    "6888b18eda5b866b5af5a28b",
    "688ba311c97c3d98965af418",
    "688b74909486c732d234bcf6",
    "688b724f9486c732d234bcf1",
    "6888bbb0da5b866b5af5a294",
    "6888b1d8da5b866b5af5a291"
  ]
}
""")
print()
print("✅ Features:")
print("- Returns only question IDs (lightweight)")
print("- Maintains question order from question_set")
print("- Validates user access permissions")
print("- Perfect for exam submission workflows")
print()
print("🔒 Access Control:")
print("- User must have 'can_view' permission on question set")
print("- Follows same rules as question set detail endpoint")
print("- Public question sets accessible to all teachers")
print("- Private question sets only accessible to authorized users")