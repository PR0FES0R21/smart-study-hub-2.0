# ==============================================================================
# File: tests/test_exam_analytics_unit.py
# Deskripsi: Comprehensive unit tests untuk exam analytics system
# ==============================================================================

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from bson import ObjectId

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crud.exam_analytics import ExamAnalyticsCRUD
from app.schemas.exam_analytics import ExamSessionAnalytics

class TestExamAnalyticsCRUD:
    """Test class for ExamAnalyticsCRUD"""
    
    def setup_method(self):
        """Setup test data"""
        self.crud = ExamAnalyticsCRUD()
        self.session_id = str(ObjectId())
        self.student_id = ObjectId()
        self.teacher_id = ObjectId()
        self.exam_id = ObjectId()
        self.subject_id = ObjectId()
        self.class_id = ObjectId()
        self.question_id = ObjectId()
        
        # Sample exam session data
        self.exam_session_data = {
            "_id": ObjectId(self.session_id),
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "started_at": datetime.utcnow() - timedelta(hours=1),
            "submitted_at": datetime.utcnow(),
            "status": "submitted",
            "score": 8,
            "answers": [{
                "question_id": self.question_id,
                "selected_option": str(ObjectId()),
                "is_correct": True,
                "answered_at": datetime.utcnow() - timedelta(minutes=30),
                "time_spent": 120,
                "position": 1,
                "points_earned": 8,
                "change_count": 0
            }],
            "violations": [{
                "violation_type": "tab_switch",
                "severity": "low",
                "detected_at": datetime.utcnow() - timedelta(minutes=15),
                "description": "Student switched tab"
            }],
            "client_info": {
                "browser": "Chrome",
                "os": "Windows"
            }
        }
        
        # Sample exam data
        self.exam_data = {
            "_id": self.exam_id,
            "title": "Test Exam",
            "teacher_id": self.teacher_id,  # This is the key field that was missing!
            "subject_id": self.subject_id,
            "class_id": self.class_id,
            "duration": 60,
            "questions": [{
                "question_id": self.question_id,
                "position": 1,
                "points": 10,
                "original_position": 1
            }],
            "exam_type": "regular",
            "academic_period": "2024-1"
        }
        
        # Sample student data
        self.student_data = {
            "_id": self.student_id,
            "first_name": "Test",
            "last_name": "Student",
            "email": "student@test.com"
        }
        
        # Sample teacher data
        self.teacher_data = {
            "_id": self.teacher_id,
            "first_name": "Test",
            "last_name": "Teacher",
            "email": "teacher@test.com"
        }
        
        # Sample subject data
        self.subject_data = {
            "_id": self.subject_id,
            "name": "Mathematics",
            "code": "MATH"
        }
        
        # Sample class data
        self.class_data = {
            "_id": self.class_id,
            "name": "XII IPA 1"
        }
        
        # Sample question data
        self.question_data = {
            "_id": self.question_id,
            "question_text": "What is 2 + 2?",
            "type": "multiple_choice",
            "difficulty": "easy",
            "options": [{
                "_id": ObjectId(),
                "text": "4",
                "is_correct": True
            }, {
                "_id": ObjectId(),
                "text": "3",
                "is_correct": False
            }],
            "correct_answer": "4"
        }

    @pytest.mark.asyncio
    async def test_generate_performance_metrics(self):
        """Test performance metrics generation"""
        performance = await self.crud._generate_performance_metrics(
            self.exam_session_data, 
            self.exam_data
        )
        
        assert performance.total_questions == 1
        assert performance.answered_questions == 1
        assert performance.correct_answers == 1
        assert performance.wrong_answers == 0
        assert performance.accuracy_percentage == 100.0
        assert performance.completion_percentage == 100.0

    @pytest.mark.asyncio
    async def test_generate_violation_analytics(self):
        """Test violation analytics generation"""
        violation_analytics = await self.crud._generate_violation_analytics(
            self.exam_session_data
        )
        
        assert violation_analytics.total_violations == 1
        assert violation_analytics.violations_by_type["tab_switch"] == 1
        assert violation_analytics.violations_by_severity["low"] == 1
        assert violation_analytics.risk_level in ["low", "medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_calculate_fraud_score(self):
        """Test fraud score calculation"""
        violations = [{
            "severity": "low"
        }, {
            "severity": "medium"
        }]
        
        fraud_score = self.crud._calculate_fraud_score(violations)
        
        assert 0.0 <= fraud_score <= 1.0
        
        # Test with no violations
        empty_fraud_score = self.crud._calculate_fraud_score([])
        assert empty_fraud_score == 0.0

    def test_determine_risk_level(self):
        """Test risk level determination"""
        # Test low risk
        risk_low = self.crud._determine_risk_level(0.1, 1)
        assert risk_low == "low"
        
        # Test medium risk
        risk_medium = self.crud._determine_risk_level(0.3, 3)
        assert risk_medium == "medium"
        
        # Test high risk
        risk_high = self.crud._determine_risk_level(0.6, 6)
        assert risk_high == "high"
        
        # Test critical risk
        risk_critical = self.crud._determine_risk_level(0.9, 12)
        assert risk_critical == "critical"

    @pytest.mark.asyncio
    async def test_analyze_answer_patterns(self):
        """Test answer pattern analysis"""
        patterns = await self.crud._analyze_answer_patterns(self.exam_session_data)
        
        assert "max_correct_streak" in patterns
        assert "max_wrong_streak" in patterns
        assert "performance_trend" in patterns
        assert "consistency_score" in patterns
        assert patterns["performance_trend"] in ["improving", "declining", "stable"]

    @pytest.mark.asyncio
    async def test_analyze_time_allocation(self):
        """Test time allocation analysis"""
        time_analysis = await self.crud._analyze_time_allocation(
            self.exam_session_data, 
            self.exam_data
        )
        
        if "error" not in time_analysis:
            assert "average_time_per_question" in time_analysis
            assert "time_efficiency" in time_analysis
            assert "time_distribution" in time_analysis
            assert time_analysis["time_efficiency"] <= 1.0

    @pytest.mark.asyncio
    async def test_generate_behavioral_insights(self):
        """Test behavioral insights generation"""
        from app.schemas.exam_analytics import PerformanceMetrics, ViolationAnalytics
        
        performance = PerformanceMetrics(
            total_questions=10,
            answered_questions=10,
            correct_answers=8,
            wrong_answers=2,
            unanswered_questions=0,
            accuracy_percentage=80.0,
            completion_percentage=100.0,
            total_time_taken=3600,
            average_time_per_question=60,
            fastest_answer=30,
            slowest_answer=120,
            score=80,
            max_possible_score=100
        )
        
        violations = ViolationAnalytics(
            total_violations=2,
            violations_by_severity={"low": 2},
            violations_by_type={"tab_switch": 2},
            violation_timeline=[],
            fraud_score=0.2,
            is_flagged=False,
            risk_level="low"
        )
        
        insights = await self.crud._generate_behavioral_insights(
            self.exam_session_data,
            performance,
            violations
        )
        
        assert isinstance(insights, list)
        assert len(insights) <= 5  # Should be limited to 5

    @pytest.mark.asyncio
    async def test_generate_recommendations(self):
        """Test recommendations generation"""
        from app.schemas.exam_analytics import PerformanceMetrics, ViolationAnalytics, ClassComparison
        
        performance = PerformanceMetrics(
            total_questions=10,
            answered_questions=10,
            correct_answers=6,
            wrong_answers=4,
            unanswered_questions=0,
            accuracy_percentage=60.0,
            completion_percentage=100.0,
            total_time_taken=3600,
            average_time_per_question=360,  # 6 minutes per question (slow)
            fastest_answer=30,
            slowest_answer=600,
            score=60,
            max_possible_score=100
        )
        
        violations = ViolationAnalytics(
            total_violations=5,
            violations_by_severity={"medium": 3, "high": 2},
            violations_by_type={"tab_switch": 3, "text_selection": 2},
            violation_timeline=[],
            fraud_score=0.5,
            is_flagged=True,
            risk_level="medium"
        )
        
        class_comparison = ClassComparison(
            class_average_score=75.0,
            class_highest_score=95.0,
            class_lowest_score=45.0,
            student_rank=15,
            total_participants=20,
            percentile=25.0,
            above_average=False,
            score_distribution=[]
        )
        
        recommendations = await self.crud._generate_recommendations(
            performance,
            violations,
            class_comparison
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5  # Should be limited to 5

class TestExamAnalyticsIntegration:
    """Integration tests with mocked database"""
    
    def setup_method(self):
        """Setup test environment"""
        self.crud = ExamAnalyticsCRUD()
        self.session_id = str(ObjectId())
        
    @pytest.mark.asyncio
    async def test_generate_exam_analytics_with_missing_teacher_id(self):
        """Test the specific error case - missing teacher_id in exam data"""
        
        # Mock database data
        exam_session_data = {
            "_id": ObjectId(self.session_id),
            "exam_id": ObjectId(),
            "student_id": ObjectId(),
            "started_at": datetime.utcnow() - timedelta(hours=1),
            "submitted_at": datetime.utcnow(),
            "status": "submitted",
            "score": 10,
            "answers": [],
            "violations": []
        }
        
        # This exam data is missing teacher_id - this should trigger the error!
        exam_data = {
            "_id": exam_session_data["exam_id"],
            "title": "Test Exam",
            # "teacher_id": ObjectId(),  # <-- MISSING! This causes the error
            "subject_id": ObjectId(),
            "class_id": ObjectId(),
            "duration": 60,
            "questions": []
        }
        
        # Mock the database calls
        with patch.object(self.crud, '_get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Setup mock returns
            mock_db.exam_sessions.find_one.return_value = exam_session_data
            mock_db.exams.find_one.return_value = exam_data  # Missing teacher_id
            mock_db.users.find_one.side_effect = [
                None,  # No teacher found because teacher_id is missing
                {"_id": exam_session_data["student_id"], "first_name": "Test", "last_name": "Student"}
            ]
            mock_db.subjects.find_one.return_value = {"_id": exam_data["subject_id"], "name": "Test Subject"}
            mock_db.classes.find_one.return_value = {"_id": exam_data["class_id"], "name": "Test Class"}
            
            # This should raise an error
            with pytest.raises(KeyError, match="teacher_id"):
                await self.crud.generate_exam_analytics(self.session_id)

    @pytest.mark.asyncio 
    async def test_generate_exam_analytics_success(self):
        """Test successful analytics generation with all required fields"""
        
        exam_session_data = {
            "_id": ObjectId(self.session_id),
            "exam_id": ObjectId(),
            "student_id": ObjectId(),
            "started_at": datetime.utcnow() - timedelta(hours=1),
            "submitted_at": datetime.utcnow(),
            "status": "submitted",
            "score": 10,
            "answers": [{
                "question_id": ObjectId(),
                "selected_option": str(ObjectId()),
                "is_correct": True,
                "answered_at": datetime.utcnow() - timedelta(minutes=30),
                "time_spent": 120,
                "position": 1,
                "points_earned": 10,
                "change_count": 0
            }],
            "violations": []
        }
        
        # Complete exam data with all required fields
        exam_data = {
            "_id": exam_session_data["exam_id"],
            "title": "Test Exam",
            "teacher_id": ObjectId(),  # <-- Present!
            "subject_id": ObjectId(),
            "class_id": ObjectId(),
            "duration": 60,
            "questions": [{
                "question_id": ObjectId(),
                "position": 1,
                "points": 10
            }],
            "exam_type": "regular",
            "academic_period": "2024-1"
        }
        
        # Mock the database calls
        with patch.object(self.crud, '_get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Setup mock returns with complete data
            mock_db.exam_analytics.find_one.return_value = None  # No cached data
            mock_db.exam_sessions.find_one.return_value = exam_session_data
            mock_db.exams.find_one.return_value = exam_data
            mock_db.users.find_one.side_effect = [
                {"_id": exam_data["teacher_id"], "first_name": "Test", "last_name": "Teacher"},
                {"_id": exam_session_data["student_id"], "first_name": "Test", "last_name": "Student"}
            ]
            mock_db.subjects.find_one.return_value = {"_id": exam_data["subject_id"], "name": "Test Subject"}
            mock_db.classes.find_one.return_value = {"_id": exam_data["class_id"], "name": "Test Class"}
            mock_db.questions.find_one.return_value = {
                "_id": exam_data["questions"][0]["question_id"],
                "question_text": "Test Question",
                "type": "multiple_choice",
                "difficulty": "easy",
                "options": [{
                    "_id": ObjectId(),
                    "text": "Option A",
                    "is_correct": True
                }]
            }
            mock_db.exam_sessions.find.return_value.to_list.return_value = [exam_session_data]
            mock_db.exam_analytics.replace_one = AsyncMock()
            
            # This should succeed
            result = await self.crud.generate_exam_analytics(self.session_id)
            
            assert isinstance(result, ExamSessionAnalytics)
            assert result.exam_title == "Test Exam"
            assert result.teacher_name == "Test Teacher"

def run_all_tests():
    """Run all tests manually for debugging"""
    import asyncio
    
    print("🧪 Running Exam Analytics Unit Tests")
    print("=" * 50)
    
    # Test CRUD methods
    crud_test = TestExamAnalyticsCRUD()
    crud_test.setup_method()
    
    async def run_crud_tests():
        try:
            await crud_test.test_generate_performance_metrics()
            print("✅ test_generate_performance_metrics - PASSED")
        except Exception as e:
            print(f"❌ test_generate_performance_metrics - FAILED: {e}")
        
        try:
            await crud_test.test_generate_violation_analytics()
            print("✅ test_generate_violation_analytics - PASSED")
        except Exception as e:
            print(f"❌ test_generate_violation_analytics - FAILED: {e}")
        
        try:
            await crud_test.test_calculate_fraud_score()
            print("✅ test_calculate_fraud_score - PASSED")
        except Exception as e:
            print(f"❌ test_calculate_fraud_score - FAILED: {e}")
        
        try:
            crud_test.test_determine_risk_level()
            print("✅ test_determine_risk_level - PASSED")
        except Exception as e:
            print(f"❌ test_determine_risk_level - FAILED: {e}")
        
        try:
            await crud_test.test_analyze_answer_patterns()
            print("✅ test_analyze_answer_patterns - PASSED")
        except Exception as e:
            print(f"❌ test_analyze_answer_patterns - FAILED: {e}")
        
        try:
            await crud_test.test_analyze_time_allocation()
            print("✅ test_analyze_time_allocation - PASSED")
        except Exception as e:
            print(f"❌ test_analyze_time_allocation - FAILED: {e}")
        
        try:
            await crud_test.test_generate_behavioral_insights()
            print("✅ test_generate_behavioral_insights - PASSED")
        except Exception as e:
            print(f"❌ test_generate_behavioral_insights - FAILED: {e}")
        
        try:
            await crud_test.test_generate_recommendations()
            print("✅ test_generate_recommendations - PASSED")
        except Exception as e:
            print(f"❌ test_generate_recommendations - FAILED: {e}")
    
    asyncio.run(run_crud_tests())
    
    print("\n" + "=" * 50)
    
    # Test integration scenarios
    integration_test = TestExamAnalyticsIntegration()
    integration_test.setup_method()
    
    async def run_integration_tests():
        try:
            await integration_test.test_generate_exam_analytics_with_missing_teacher_id()
            print("❌ test_missing_teacher_id should have failed!")
        except KeyError:
            print("✅ test_missing_teacher_id - CAUGHT EXPECTED ERROR")
        except Exception as e:
            print(f"❌ test_missing_teacher_id - UNEXPECTED ERROR: {e}")
        
        try:
            await integration_test.test_generate_exam_analytics_success()
            print("✅ test_generate_exam_analytics_success - PASSED")
        except Exception as e:
            print(f"❌ test_generate_exam_analytics_success - FAILED: {e}")
    
    asyncio.run(run_integration_tests())
    
    print("\n🎉 Unit Tests Completed!")

if __name__ == "__main__":
    run_all_tests()
