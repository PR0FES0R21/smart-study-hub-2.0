# Exam Analytics API Usage Guide

## Overview
Exam Analytics API menyediakan analisis mendalam tentang performa siswa dalam ujian, termasuk fraud detection, learning insights, dan class comparison.

## Endpoints

### 1. Get Comprehensive Analytics
**Endpoint:** `GET /api/v1/exam-analytics/session/{exam_session_id}`

**Description:** Mendapatkan analytics lengkap untuk exam session tertentu

**Parameters:**
- `exam_session_id` (path): ID dari exam session
- `force_regenerate` (query, optional): Force regenerate analytics (default: false)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/exam-analytics/session/65a1b2c3d4e5f6789abcdef0?force_regenerate=false" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Example Response:**
```json
{
  "exam_session_id": "65a1b2c3d4e5f6789abcdef0",
  "exam_id": "65a1b2c3d4e5f6789abcdef1",
  "student_id": "65a1b2c3d4e5f6789abcdef2",
  "exam_title": "Mathematics Final Test",
  "exam_type": "regular",
  "subject_name": "Mathematics",
  "teacher_name": "John Doe",
  "class_name": "XII IPA 1",
  "academic_period": "2024-1",
  "started_at": "2024-01-15T10:00:00Z",
  "submitted_at": "2024-01-15T11:30:00Z",
  "duration_allowed": 90,
  "duration_taken": 90.0,
  "is_overtime": false,
  "performance_metrics": {
    "total_questions": 20,
    "answered_questions": 18,
    "correct_answers": 15,
    "wrong_answers": 3,
    "unanswered_questions": 2,
    "accuracy_percentage": 83.33,
    "completion_percentage": 90.0,
    "total_time_taken": 5400.0,
    "average_time_per_question": 270.0,
    "fastest_answer": 30.0,
    "slowest_answer": 600.0,
    "score": 75.0,
    "max_possible_score": 100.0
  },
  "violation_analytics": {
    "total_violations": 3,
    "violations_by_severity": {
      "low": 2,
      "medium": 1
    },
    "violations_by_type": {
      "tab_switch": 2,
      "text_selection": 1
    },
    "fraud_score": 0.25,
    "is_flagged": false,
    "risk_level": "low"
  },
  "class_comparison": {
    "class_average_score": 68.5,
    "class_highest_score": 95.0,
    "class_lowest_score": 45.0,
    "student_rank": 3,
    "total_participants": 25,
    "percentile": 88.0,
    "above_average": true
  },
  "behavioral_insights": [
    "Good understanding with room for improvement",
    "Minor violations detected - maintain focus during exams"
  ],
  "recommendations": [
    "Review class materials and compare with top performers",
    "Analyze your mistakes to identify knowledge gaps"
  ]
}
```

### 2. Get Analytics Summary
**Endpoint:** `GET /api/v1/exam-analytics/session/{exam_session_id}/summary`

**Description:** Mendapatkan ringkasan analytics untuk dashboard display

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/exam-analytics/session/65a1b2c3d4e5f6789abcdef0/summary" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Example Response:**
```json
{
  "exam_session_id": "65a1b2c3d4e5f6789abcdef0",
  "student_name": "Alice Johnson",
  "exam_title": "Mathematics Final Test",
  "score": 75.0,
  "accuracy": 83.33,
  "completion": 90.0,
  "rank_in_class": 3,
  "total_violations": 3,
  "risk_level": "low",
  "duration_taken": 90.0,
  "is_flagged": false,
  "generated_at": "2024-01-15T12:00:00Z"
}
```

### 3. Get Batch Analytics (Teacher/Admin Only)
**Endpoint:** `GET /api/v1/exam-analytics/exam/{exam_id}/batch`

**Description:** Mendapatkan analytics untuk seluruh siswa dalam ujian tertentu

**Parameters:**
- `exam_id` (path): ID dari exam
- `include_flagged_only` (query, optional): Hanya siswa yang flagged (default: false)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/exam-analytics/exam/65a1b2c3d4e5f6789abcdef1/batch?include_flagged_only=false" \
  -H "Authorization: Bearer TEACHER_JWT_TOKEN"
```

### 4. Get Cheat Detection Report (Teacher/Admin Only)
**Endpoint:** `GET /api/v1/exam-analytics/session/{exam_session_id}/cheat-detection`

**Description:** Mendapatkan detailed fraud detection report

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/exam-analytics/session/65a1b2c3d4e5f6789abcdef0/cheat-detection" \
  -H "Authorization: Bearer TEACHER_JWT_TOKEN"
```

**Example Response:**
```json
{
  "exam_session_id": "65a1b2c3d4e5f6789abcdef0",
  "student_id": "65a1b2c3d4e5f6789abcdef2",
  "overall_fraud_score": 0.25,
  "risk_assessment": "LOW",
  "violation_summary": {
    "total_violations": 3,
    "violations_by_severity": {
      "low": 2,
      "medium": 1
    },
    "fraud_score": 0.25,
    "is_flagged": false,
    "risk_level": "low"
  },
  "suspicious_patterns": [
    {
      "type": "time_anomaly",
      "description": "Unusually fast response times",
      "severity": "medium",
      "evidence": "Average 12.5s per question"
    }
  ],
  "recommended_actions": [
    "Send warning to student",
    "Monitor future exam sessions closely"
  ],
  "requires_manual_review": false,
  "confidence_level": 0.3
}
```

### 5. Get Learning Insights
**Endpoint:** `GET /api/v1/exam-analytics/session/{exam_session_id}/learning-insights`

**Description:** Mendapatkan personalized learning insights untuk student

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/exam-analytics/session/65a1b2c3d4e5f6789abcdef0/learning-insights" \
  -H "Authorization: Bearer STUDENT_JWT_TOKEN"
```

**Example Response:**
```json
{
  "strengths": [
    "Good foundational understanding",
    "Excellent time management",
    "Strong performance on easy questions"
  ],
  "weaknesses": [
    "Struggles with hard questions",
    "Needs practice with essay questions"
  ],
  "study_recommendations": [
    "Focus on advanced practice problems",
    "Review fundamental concepts in this subject",
    "Create summary notes of key topics"
  ],
  "time_management_tips": [
    "Current pacing is appropriate for your style"
  ],
  "difficulty_progression": {
    "easy": 0.95,
    "medium": 0.80,
    "hard": 0.60
  },
  "question_type_mastery": {
    "multiple_choice": 0.85,
    "essay": 0.70
  }
}
```

### 6. Manual Analytics Generation
**Endpoint:** `POST /api/v1/exam-analytics/generate`

**Description:** Manually trigger analytics generation dengan options khusus

**Request Body:**
```json
{
  "exam_session_id": "65a1b2c3d4e5f6789abcdef0",
  "force_regenerate": true,
  "include_class_comparison": true,
  "include_question_analysis": true,
  "include_behavioral_insights": true
}
```

### 7. Delete Analytics Cache (Admin Only)
**Endpoint:** `DELETE /api/v1/exam-analytics/session/{exam_session_id}`

**Description:** Menghapus cached analytics data

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/exam-analytics/session/65a1b2c3d4e5f6789abcdef0" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

### 8. Health Check
**Endpoint:** `GET /api/v1/exam-analytics/health`

**Description:** Health check untuk analytics system

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/exam-analytics/health"
```

## Permission Matrix

| Endpoint | Student | Teacher | Admin |
|----------|---------|---------|-------|
| Get Analytics | Own data only | Own exams only | All |
| Get Summary | Own data only | Own exams only | All |
| Batch Analytics | ❌ | Own exams only | All |
| Cheat Detection | ❌ | Own exams only | All |
| Learning Insights | Own data only | Own exams only | All |
| Manual Generation | Own data only | Own exams only | All |
| Delete Cache | ❌ | ❌ | All |
| Health Check | ✅ | ✅ | ✅ |

## Error Codes

- `400` - Bad Request (Invalid data format)
- `401` - Unauthorized (Invalid or missing JWT token)
- `403` - Forbidden (Insufficient permissions)
- `404` - Not Found (Exam session not found)
- `500` - Internal Server Error

## Authentication

All endpoints (except health check) require JWT authentication:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

## Usage Tips

1. **Caching**: Analytics are cached for 24 hours to improve performance
2. **Force Regenerate**: Use `force_regenerate=true` if you need fresh data
3. **Batch Processing**: Use batch endpoints for class-level analysis
4. **Permission Checks**: Ensure proper role-based access control
5. **Error Handling**: Always implement proper error handling for API calls

## Integration Example

```javascript
// Frontend integration example
const getExamAnalytics = async (sessionId, token) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/exam-analytics/session/${sessionId}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch analytics:', error);
    throw error;
  }
};
```
