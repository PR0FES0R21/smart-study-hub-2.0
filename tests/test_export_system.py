#!/usr/bin/env python3
"""
Flexible Export System Testing Script
Test all endpoints dengan berbagai payloads
"""

import requests
import json
import time
import os
from typing import Dict, Any, Optional

class ExportSystemTester:
    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        self.base_url = f"{base_url}/api/v1/exports"
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json"
        }
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, details: str = "", response: dict = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response": response
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if not success and response:
            print(f"   Error: {response}")
        print()
    
    def test_get_collections(self):
        """Test GET /collections endpoint"""
        try:
            response = requests.get(f"{self.base_url}/collections", headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                collections_count = len(data.get("collections", []))
                self.log_test(
                    "GET /collections", 
                    True, 
                    f"Found {collections_count} collections",
                    data
                )
                return data
            else:
                self.log_test(
                    "GET /collections", 
                    False, 
                    f"HTTP {response.status_code}",
                    response.text
                )
                return None
                
        except Exception as e:
            self.log_test("GET /collections", False, f"Exception: {str(e)}")
            return None
    
    def test_get_formats(self):
        """Test GET /formats endpoint"""
        try:
            response = requests.get(f"{self.base_url}/formats", headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                formats = data.get("supported_formats", [])
                self.log_test(
                    "GET /formats", 
                    True, 
                    f"Supported formats: {', '.join(formats)}",
                    data
                )
                return data
            else:
                self.log_test(
                    "GET /formats", 
                    False, 
                    f"HTTP {response.status_code}",
                    response.text
                )
                return None
                
        except Exception as e:
            self.log_test("GET /formats", False, f"Exception: {str(e)}")
            return None
    
    def test_validate_config(self):
        """Test POST /validate endpoint"""
        # Test 1: Basic validation
        payload1 = {
            "config": {
                "main_collection": "users",
                "fields": ["username", "email"],
                "filters": [
                    {
                        "field": "roles",
                        "operator": "eq",
                        "value": "student"
                    }
                ],
                "limit": 10
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/validate", 
                headers=self.headers,
                json=payload1
            )
            
            if response.status_code == 200:
                data = response.json()
                is_valid = data.get("valid", False)
                estimated = data.get("estimated_records", 0)
                self.log_test(
                    "POST /validate (basic)", 
                    is_valid, 
                    f"Estimated records: {estimated}",
                    data
                )
            else:
                self.log_test(
                    "POST /validate (basic)", 
                    False, 
                    f"HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test("POST /validate (basic)", False, f"Exception: {str(e)}")
        
        # Test 2: Complex validation with joins
        payload2 = {
            "config": {
                "main_collection": "users",
                "fields": ["username", "email"],
                "filters": [
                    {
                        "field": "roles",
                        "operator": "eq",
                        "value": "student"
                    }
                ],
                "joins": [
                    {
                        "collection": "profiles",
                        "local_field": "profile_id",
                        "foreign_field": "_id",
                        "fields": ["full_name", "birth_date"],
                        "join_type": "unwind"
                    }
                ],
                "sort": {"username": 1},
                "limit": 50
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/validate", 
                headers=self.headers,
                json=payload2
            )
            
            if response.status_code == 200:
                data = response.json()
                is_valid = data.get("valid", False)
                warnings = len(data.get("warnings", []))
                self.log_test(
                    "POST /validate (with joins)", 
                    is_valid, 
                    f"Warnings: {warnings}",
                    data
                )
            else:
                self.log_test(
                    "POST /validate (with joins)", 
                    False, 
                    f"HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test("POST /validate (with joins)", False, f"Exception: {str(e)}")
    
    def test_execute_export(self):
        """Test POST /execute endpoint"""
        # Test 1: Simple sync export
        payload1 = {
            "config": {
                "main_collection": "users",
                "fields": ["username", "email", "is_active"],
                "filters": [
                    {
                        "field": "roles",
                        "operator": "eq", 
                        "value": "student"
                    }
                ],
                "limit": 5
            },
            "format": "json",
            "filename": "test_export_simple",
            "async_export": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/execute",
                headers=self.headers,
                json=payload1
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                record_count = data.get("record_count", 0)
                file_url = data.get("file_url", "")
                
                self.log_test(
                    "POST /execute (simple sync)",
                    success,
                    f"Records: {record_count}, File: {file_url}",
                    data
                )
                
                return file_url
            else:
                self.log_test(
                    "POST /execute (simple sync)",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return None
                
        except Exception as e:
            self.log_test("POST /execute (simple sync)", False, f"Exception: {str(e)}")
            return None
        
        # Test 2: Export with joins
        payload2 = {
            "config": {
                "main_collection": "users",
                "fields": ["username", "email"],
                "filters": [
                    {
                        "field": "roles",
                        "operator": "eq",
                        "value": "student"
                    }
                ],
                "joins": [
                    {
                        "collection": "profiles",
                        "local_field": "profile_id",
                        "foreign_field": "_id",
                        "fields": ["full_name", "gender"],
                        "join_type": "unwind"
                    }
                ],
                "sort": {"username": 1},
                "limit": 10
            },
            "format": "excel",
            "filename": "test_export_with_joins"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/execute",
                headers=self.headers,
                json=payload2
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if data.get("task_id"):
                    # Async export
                    self.log_test(
                        "POST /execute (with joins - async)",
                        success,
                        f"Task ID: {data.get('task_id')}",
                        data
                    )
                    return data.get("task_id")
                else:
                    # Sync export
                    record_count = data.get("record_count", 0)
                    file_url = data.get("file_url", "")
                    self.log_test(
                        "POST /execute (with joins - sync)",
                        success,
                        f"Records: {record_count}, File: {file_url}",
                        data
                    )
                    return file_url
            else:
                self.log_test(
                    "POST /execute (with joins)",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return None
                
        except Exception as e:
            self.log_test("POST /execute (with joins)", False, f"Exception: {str(e)}")
            return None
    
    def test_async_status(self, task_id: str):
        """Test GET /status/{task_id} endpoint"""
        if not task_id:
            return
            
        try:
            response = requests.get(f"{self.base_url}/status/{task_id}", headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                status_info = data.get("status", {})
                status = status_info.get("status", "unknown")
                progress = status_info.get("progress", 0)
                
                self.log_test(
                    "GET /status/{task_id}",
                    True,
                    f"Status: {status}, Progress: {progress}%",
                    data
                )
                
                return status_info
            else:
                self.log_test(
                    "GET /status/{task_id}",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return None
                
        except Exception as e:
            self.log_test("GET /status/{task_id}", False, f"Exception: {str(e)}")
            return None
    
    def test_quick_exports(self):
        """Test quick export endpoints"""
        # Test 1: Quick student export
        try:
            response = requests.post(
                f"{self.base_url}/quick/students?format=json&grade_level=10",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "POST /quick/students",
                    success,
                    "Grade 10 students export",
                    data
                )
            else:
                self.log_test(
                    "POST /quick/students",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test("POST /quick/students", False, f"Exception: {str(e)}")
        
        # Test 2: Quick exam results export
        try:
            response = requests.post(
                f"{self.base_url}/quick/exam-results?format=json",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "POST /quick/exam-results",
                    success,
                    "All exam results export",
                    data
                )
            else:
                self.log_test(
                    "POST /quick/exam-results",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test("POST /quick/exam-results", False, f"Exception: {str(e)}")
    
    def test_error_cases(self):
        """Test error handling"""
        # Test 1: Invalid collection
        payload1 = {
            "config": {
                "main_collection": "invalid_collection",
                "fields": ["field1", "field2"]
            },
            "format": "excel"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/execute",
                headers=self.headers,
                json=payload1
            )
            
            # Should return error
            success = response.status_code == 400
            self.log_test(
                "Error Test: Invalid Collection",
                success,
                f"Expected 400, got {response.status_code}",
                response.text
            )
            
        except Exception as e:
            self.log_test("Error Test: Invalid Collection", False, f"Exception: {str(e)}")
        
        # Test 2: Invalid format
        payload2 = {
            "config": {
                "main_collection": "users",
                "fields": ["username", "email"]
            },
            "format": "pdf"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/execute",
                headers=self.headers,
                json=payload2
            )
            
            # Should return error
            success = response.status_code == 400
            self.log_test(
                "Error Test: Invalid Format",
                success,
                f"Expected 400, got {response.status_code}",
                response.text
            )
            
        except Exception as e:
            self.log_test("Error Test: Invalid Format", False, f"Exception: {str(e)}")
    
    def test_file_download(self, file_url: str):
        """Test file download"""
        if not file_url:
            return
            
        try:
            # Extract filename from URL
            filename = file_url.split("/")[-1]
            
            response = requests.get(f"{self.base_url.replace('/exports', '')}{file_url}", headers=self.headers)
            
            if response.status_code == 200:
                # Check if content looks like a file
                content_length = len(response.content)
                content_type = response.headers.get("content-type", "")
                
                self.log_test(
                    "GET /download/{filename}",
                    True,
                    f"File size: {content_length} bytes, Type: {content_type}"
                )
                
                # Save file to test
                with open(f"test_downloaded_{filename}", "wb") as f:
                    f.write(response.content)
                print(f"   File saved as: test_downloaded_{filename}")
                
            else:
                self.log_test(
                    "GET /download/{filename}",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test("GET /download/{filename}", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Flexible Export System Tests\n")
        print("=" * 50)
        
        if not self.token:
            print("⚠️  Warning: No token provided. Some tests may fail.")
            print("   Set token with: tester.token = 'your_token_here'\n")
        
        # Basic endpoint tests
        print("📋 Testing Basic Endpoints...")
        self.test_get_collections()
        self.test_get_formats()
        
        # Validation tests
        print("🔍 Testing Validation...")
        self.test_validate_config()
        
        # Export execution tests
        print("📤 Testing Export Execution...")
        file_url_or_task = self.test_execute_export()
        
        # If we got a task ID, check status
        if isinstance(file_url_or_task, str) and len(file_url_or_task) > 20:
            print("⏳ Testing Async Status...")
            self.test_async_status(file_url_or_task)
        elif file_url_or_task:
            # Test file download
            print("📁 Testing File Download...")
            self.test_file_download(file_url_or_task)
        
        # Quick export tests
        print("⚡ Testing Quick Exports...")
        self.test_quick_exports()
        
        # Error handling tests
        print("🚨 Testing Error Handling...")
        self.test_error_cases()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n🎯 Test completed!")
        
        # Save detailed results
        with open("export_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print("📄 Detailed results saved to: export_test_results.json")


def main():
    """Main testing function"""
    print("Flexible Export System Tester")
    print("=" * 40)
    
    # Configuration
    BASE_URL = "http://localhost:8000"  # Change this to your server URL
    TOKEN = None  # Set your access token here
    
    print(f"Base URL: {BASE_URL}")
    print(f"Token: {'Set' if TOKEN else 'Not Set'}")
    print()
    
    # Get token from user if not set
    if not TOKEN:
        token_input = input("Enter your access token (or press Enter to skip): ")
        if token_input.strip():
            TOKEN = token_input.strip()
    
    # Initialize tester
    tester = ExportSystemTester(BASE_URL, TOKEN)
    
    # Run tests
    tester.run_all_tests()


if __name__ == "__main__":
    main()
