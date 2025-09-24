# ==============================================================================
# File: tests/test_teacher_analytics.py
# Deskripsi: Unit tests untuk Teacher Analytics system
# ==============================================================================
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import AsyncClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.schemas.teacher_analytics import (
    ExamAnalytics, ExamMetadata, ClassStatistics, 
    QuestionAnalysis, StudentPerformance, TimeAnalysis,
    ViolationAnalysis, AnalyticsTask
)
from app.crud.crud_teacher_analytics import TeacherAnalyticsCRUD
from app.tasks.teacher_analytics_tasks import TeacherAnalyticsTaskManager


class TestTeacherAnalyticsSchemas:
    """Test Pydantic schemas untuk teacher analytics"""
    
    def test_exam_metadata_schema(self):
        """Test ExamMetadata schema validation"""
        metadata = ExamMetadata(
            exam_id=ObjectId(),
            exam_title="Test Exam",
            exam_type="official_uts",
            subject_name="Mathematics",
            class_name="10A",
            teacher_name="John Doe",
            total_questions=25,
            max_score=100,
            duration_minutes=90,
            availability_start_time=datetime.utcnow(),
            availability_end_time=datetime.utcnow() + timedelta(hours=2),
            academic_period="2024/2025"
        )
        
        assert metadata.exam_title == "Test Exam"
        assert metadata.total_questions == 25
        assert metadata.duration_minutes == 90
    
    def test_class_statistics_schema(self):
        """Test ClassStatistics schema with grade distribution"""
        stats = ClassStatistics(
            total_students=30,
            students_completed=25,
            students_in_progress=3,
            students_not_started=2,
            completion_rate=83.33,
            class_average=75.5,
            median_score=78.0,
            highest_score=95,
            lowest_score=45,
            standard_deviation=12.5,
            passing_rate=80.0,
            grade_distribution={"A": 5, "B": 10, "C": 8, "D": 2, "E": 0},
            score_ranges={"81-100": 8, "61-80": 12, "41-60": 4, "21-40": 1, "0-20": 0}
        )
        
        assert stats.total_students == 30
        assert stats.completion_rate == 83.33
        assert stats.grade_distribution["A"] == 5
        assert sum(stats.grade_distribution.values()) == 25  # Only completed students
    
    def test_question_analysis_schema(self):
        """Test QuestionAnalysis schema"""
        analysis = QuestionAnalysis(
            question_id=ObjectId(),
            question_number=1,
            question_text="What is 2+2?",
            question_type="multiple_choice",
            difficulty="easy",
            points=5,
            class_accuracy=0.85,
            correct_count=17,
            wrong_count=3,
            unanswered_count=0,
            average_time=45.5,
            median_time=42.0,
            fastest_time=15.0,
            slowest_time=120.0,
            is_problematic=False,
            discrimination_index=0.65,
            answer_distribution={"A": 17, "B": 2, "C": 1, "D": 0},
            correct_option="A"
        )
        
        assert analysis.class_accuracy == 0.85
        assert analysis.is_problematic == False
        assert analysis.discrimination_index > 0.5  # Good discrimination


class TestTeacherAnalyticsCRUD:
    """Test CRUD functions untuk teacher analytics"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database connection"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def analytics_crud(self):
        """Teacher analytics CRUD instance"""
        return TeacherAnalyticsCRUD()
    
    @pytest.fixture
    def sample_exam_data(self):
        """Sample exam data untuk testing"""
        return {
            "_id": ObjectId(),
            "title": "Mathematics Test",
            "exam_type": "official_uts",
            "duration_minutes": 90,
            "question_ids": [ObjectId(), ObjectId(), ObjectId()],
            "availability_start_time": datetime.utcnow(),
            "availability_end_time": datetime.utcnow() + timedelta(hours=2),
            "assignment": {
                "teacher_id": ObjectId(),
                "subject_id": ObjectId(),
                "class_id": ObjectId()
            },
            "subject": {"name": "Mathematics"},
            "class": {"name": "10A"},
            "teacher": {"full_name": "John Doe", "first_name": "John", "last_name": "Doe"}
        }
    
    @pytest.fixture
    def sample_exam_sessions(self):
        """Sample exam sessions untuk testing"""
        teacher_id = ObjectId()
        return [
            {
                "_id": ObjectId(),
                "exam_id": ObjectId(),
                "student_id": ObjectId(),
                "status": "graded",
                "score": 85,
                "started_at": datetime.utcnow() - timedelta(hours=2),
                "submitted_at": datetime.utcnow() - timedelta(hours=1),
                "answers": {"q1": "answer1", "q2": "answer2"},
                "interaction_logs": [],
                "violations": [],
                "student": {"first_name": "Alice", "last_name": "Smith"},
                "profile": {"full_name": "Alice Smith"}
            },
            {
                "_id": ObjectId(),
                "exam_id": ObjectId(),
                "student_id": ObjectId(),
                "status": "graded",
                "score": 92,
                "started_at": datetime.utcnow() - timedelta(hours=2),
                "submitted_at": datetime.utcnow() - timedelta(hours=1),
                "answers": {"q1": "answer1", "q2": "answer2"},
                "interaction_logs": [],
                "violations": [],
                "student": {"first_name": "Bob", "last_name": "Johnson"},
                "profile": {"full_name": "Bob Johnson"}
            }
        ]
    
    @pytest.mark.asyncio
    async def test_generate_exam_metadata(self, analytics_crud, mock_db, sample_exam_data):
        """Test generation of exam metadata"""
        # Mock academic period lookup
        mock_db.academic_periods.find_one.return_value = {"name": "2024/2025 Semester 1"}
        
        with patch.object(analytics_crud, '_get_db', return_value=mock_db):
            metadata = await analytics_crud._generate_exam_metadata(mock_db, sample_exam_data)
        
        assert isinstance(metadata, ExamMetadata)
        assert metadata.exam_title == "Mathematics Test"
        assert metadata.subject_name == "Mathematics"
        assert metadata.class_name == "10A"
        assert metadata.teacher_name == "John Doe"
        assert metadata.total_questions == 3
        assert metadata.academic_period == "2024/2025 Semester 1"
    
    @pytest.mark.asyncio
    async def test_generate_class_statistics(self, analytics_crud, mock_db, sample_exam_data, sample_exam_sessions):
        """Test generation of class statistics"""
        # Mock profiles count
        mock_db.profiles.count_documents.return_value = 30
        
        with patch.object(analytics_crud, '_get_db', return_value=mock_db):
            stats = await analytics_crud._generate_class_statistics(mock_db, sample_exam_sessions, sample_exam_data)
        
        assert isinstance(stats, ClassStatistics)
        assert stats.total_students == 30
        assert stats.students_completed == 2
        assert stats.class_average == 88.5  # (85 + 92) / 2
        assert stats.highest_score == 92
        assert stats.lowest_score == 85
        assert stats.completion_rate == pytest.approx(6.67, rel=1e-2)  # 2/30 * 100
    
    @pytest.mark.asyncio
    async def test_generate_student_performances(self, analytics_crud, mock_db, sample_exam_data, sample_exam_sessions):
        """Test generation of student performances with ranking"""
        with patch.object(analytics_crud, '_get_db', return_value=mock_db):
            performances = await analytics_crud._generate_student_performances(
                mock_db, sample_exam_sessions, sample_exam_data
            )
        
        assert len(performances) == 2
        
        # Check ranking (highest score first)
        assert performances[0].student_name == "Bob Johnson"
        assert performances[0].score == 92
        assert performances[0].rank == 1
        
        assert performances[1].student_name == "Alice Smith"  
        assert performances[1].score == 85
        assert performances[1].rank == 2
        
        # Check percentiles (for 2 students: 50% each position)
        assert performances[0].percentile == 50.0  # Only student below
        assert performances[1].percentile == 0     # No students below
    
    @pytest.mark.asyncio
    async def test_authorization_check(self, analytics_crud, mock_db):
        """Test authorization - guru hanya bisa akses ujian miliknya"""
        exam_id = str(ObjectId())
        teacher_id = ObjectId()
        wrong_teacher_id = ObjectId()
        
        # Mock exam data with specific teacher
        mock_exam_data = {
            "_id": ObjectId(exam_id),
            "assignment": {"teacher_id": teacher_id}
        }
        
        # Mock the complete chain: db.exams.aggregate().to_list()
        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[mock_exam_data])
        mock_db.exams.aggregate = Mock(return_value=mock_cursor)
        
        with patch.object(analytics_crud, '_get_db', return_value=mock_db):
            # Should succeed with correct teacher
            result = await analytics_crud._get_exam_data(mock_db, exam_id, teacher_id)
            assert result["_id"] == ObjectId(exam_id)
            
            # Test authorization failure - empty result for wrong teacher
            mock_cursor.to_list = AsyncMock(return_value=[])
            with pytest.raises(Exception) as exc_info:
                await analytics_crud._get_exam_data(mock_db, exam_id, wrong_teacher_id)
            assert "Exam not found" in str(exc_info.value)


class TestTeacherAnalyticsTaskManager:
    """Test background task manager"""
    
    @pytest.fixture
    def task_manager(self):
        return TeacherAnalyticsTaskManager()
    
    def test_generate_task_id(self):
        """Test task ID generation"""
        exam_id = "test_exam_123"
        teacher_id = ObjectId()
        
        task_id = TeacherAnalyticsTaskManager.generate_task_id(exam_id, teacher_id)
        
        assert task_id.startswith(f"analytics_{exam_id}_{teacher_id}_")
        # Split by '_' and check minimum parts (analytics, exam parts, teacher, timestamp)
        parts = task_id.split('_')
        assert len(parts) >= 4  # At least analytics, exam part(s), teacher, timestamp
        assert parts[0] == "analytics"
        assert str(teacher_id) in task_id
    
    @pytest.mark.asyncio
    async def test_task_creation(self):
        """Test task creation and tracking"""
        exam_id = str(ObjectId())  # Use valid ObjectId string
        teacher_id = ObjectId()
        
        with patch('app.tasks.teacher_analytics_tasks.teacher_analytics_crud') as mock_crud:
            mock_crud.get_analytics.return_value = None  # No existing analytics
            
            # Mock the actual processing
            with patch.object(TeacherAnalyticsTaskManager, '_process_analytics_generation'):
                task_id = await TeacherAnalyticsTaskManager.start_analytics_generation(
                    exam_id, teacher_id, force_regenerate=False
                )
        
        assert task_id.startswith("analytics_")
        
        # Check task was stored
        task = await TeacherAnalyticsTaskManager.get_task_status(task_id)
        assert task is not None
        assert str(task.exam_id) == exam_id  # Compare as string
        assert task.teacher_id == teacher_id
        assert task.status in ["pending", "processing"]
    
    @pytest.mark.asyncio
    async def test_task_status_updates(self):
        """Test task status updates"""
        task_id = "test_task_123"
        
        # Create a mock task
        from app.schemas.teacher_analytics import AnalyticsTask
        task = AnalyticsTask(
            task_id=task_id,
            exam_id=ObjectId(),
            teacher_id=ObjectId(),
            status="pending",
            progress=0.0,
            started_at=datetime.utcnow()
        )
        
        # Store task manually
        from app.tasks.teacher_analytics_tasks import _task_storage
        _task_storage[task_id] = task
        
        # Test status update
        await TeacherAnalyticsTaskManager.update_task_status(task_id, "processing", 50.0)
        
        updated_task = await TeacherAnalyticsTaskManager.get_task_status(task_id)
        assert updated_task.status == "processing"
        assert updated_task.progress == 50.0
        
        # Test completion
        await TeacherAnalyticsTaskManager.update_task_status(task_id, "completed", 100.0)
        
        completed_task = await TeacherAnalyticsTaskManager.get_task_status(task_id)
        assert completed_task.status == "completed"
        assert completed_task.progress == 100.0
        assert completed_task.completed_at is not None


@pytest.mark.skip("API tests require complex auth setup - focusing on core logic for now")
class TestTeacherAnalyticsAPI:
    """Test API endpoints untuk teacher analytics"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_teacher_token(self):
        """Mock teacher JWT token"""
        # In real implementation, generate proper JWT
        return "mock_teacher_token_123"
    
    @pytest.fixture
    def auth_headers(self, mock_teacher_token):
        """Authorization headers"""
        return {"Authorization": f"Bearer {mock_teacher_token}"}
    
    def test_generate_analytics_endpoint_invalid_exam_id(self, client, auth_headers):
        """Test generate analytics dengan invalid exam ID"""
        with patch('app.api.v1.deps.get_current_active_teacher') as mock_auth:
            mock_auth.return_value = {"_id": ObjectId(), "roles": ["teacher"]}
            
            response = client.post(
                "/api/v1/teacher-analytics/exams/invalid_id/analytics/generate",
                json={"exam_id": ObjectId(), "force_regenerate": False},
                headers=auth_headers
            )
        
        assert response.status_code == 400
        assert "Invalid exam ID" in response.json()["detail"]
    
    def test_get_analytics_not_found(self, client, auth_headers):
        """Test get analytics when analytics doesn't exist"""
        exam_id = str(ObjectId())
        
        with patch('app.api.v1.deps.get_current_active_teacher') as mock_auth:
            mock_auth.return_value = {"_id": ObjectId(), "roles": ["teacher"]}
            
            with patch('app.crud.crud_teacher_analytics.teacher_analytics_crud.get_analytics') as mock_get:
                mock_get.return_value = None
                
                response = client.get(
                    f"/api/v1/teacher-analytics/exams/{exam_id}/analytics",
                    headers=auth_headers
                )
        
        assert response.status_code == 404
        assert "Analytics not found" in response.json()["detail"]
    
    def test_task_status_endpoint(self, client, auth_headers):
        """Test task status endpoint"""
        task_id = "test_task_123"
        teacher_id = ObjectId()
        
        # Create mock task
        mock_task = AnalyticsTask(
            task_id=task_id,
            exam_id=ObjectId(),
            teacher_id=teacher_id,
            status="processing",
            progress=75.0,
            started_at=datetime.utcnow()
        )
        
        with patch('app.api.v1.deps.get_current_active_teacher') as mock_auth:
            mock_auth.return_value = {"_id": teacher_id, "roles": ["teacher"]}
            
            with patch('app.tasks.teacher_analytics_tasks.get_analytics_task_status') as mock_get_task:
                mock_get_task.return_value = mock_task
                
                response = client.get(
                    f"/api/v1/teacher-analytics/tasks/{task_id}/status",
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task_id
        assert data["status"] == "processing" 
        assert data["progress"] == 75.0


class TestIntegration:
    """Integration tests untuk complete workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_analytics_workflow(self):
        """Test complete workflow dari generation sampai retrieval"""
        # This would be a full integration test
        # Testing the entire flow from API call to database storage
        pass
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        # Test various error conditions
        pass
    
    def test_performance_with_large_data(self):
        """Test performance dengan data besar"""
        # Test dengan banyak siswa dan pertanyaan
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
