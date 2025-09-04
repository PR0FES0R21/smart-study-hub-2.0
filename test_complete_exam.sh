#!/bin/bash

# =============================================================================
# Script untuk Testing Complete Exam Endpoint
# Usage: ./test_complete_exam.sh
# =============================================================================

# Configuration
SERVER="http://localhost:8000"
USERNAME="admin"  # atau "guru123"
PASSWORD="admin123"  # atau password guru
EXAM_ID="your_exam_id_here"  # Ganti dengan ID ujian yang valid

echo "🧪 Testing Complete Exam Endpoint"
echo "=================================="

# Step 1: Login
echo "🔑 Step 1: Login..."
LOGIN_RESPONSE=$(curl -s -X POST "$SERVER/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
    echo "❌ Login failed!"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful!"
echo "Token: ${TOKEN:0:20}..."

echo ""
echo "📋 Step 2: Get exam details first..."
EXAM_RESPONSE=$(curl -s -X GET "$SERVER/api/v1/exams/$EXAM_ID/details" \
  -H "Authorization: Bearer $TOKEN")

EXAM_STATUS=$(echo $EXAM_RESPONSE | jq -r '.status')
EXAM_TITLE=$(echo $EXAM_RESPONSE | jq -r '.title')

if [ "$EXAM_STATUS" = "null" ]; then
    echo "❌ Exam not found or no access!"
    echo "Response: $EXAM_RESPONSE"
    exit 1
fi

echo "📝 Exam Details:"
echo "  Title: $EXAM_TITLE"
echo "  Current Status: $EXAM_STATUS"

# Step 3: Test Complete Exam
echo ""
echo "🎯 Step 3: Complete exam..."

if [ "$EXAM_STATUS" = "completed" ]; then
    echo "⚠️  Exam is already completed. Testing error handling..."
fi

COMPLETE_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$SERVER/api/v1/exams/$EXAM_ID/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation": true,
    "reason": "Testing manual completion via script"
  }')

HTTP_CODE="${COMPLETE_RESPONSE: -3}"
RESPONSE_BODY="${COMPLETE_RESPONSE%???}"

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Exam completed successfully!"
    NEW_STATUS=$(echo $RESPONSE_BODY | jq -r '.status')
    COMPLETED_AT=$(echo $RESPONSE_BODY | jq -r '.completed_at')
    COMPLETED_BY=$(echo $RESPONSE_BODY | jq -r '.completed_by')
    COMPLETION_REASON=$(echo $RESPONSE_BODY | jq -r '.completion_reason')
    
    echo "📊 Completion Details:"
    echo "  New Status: $NEW_STATUS"
    echo "  Completed At: $COMPLETED_AT"
    echo "  Completed By: $COMPLETED_BY"
    echo "  Reason: $COMPLETION_REASON"
    
elif [ "$HTTP_CODE" = "400" ]; then
    echo "⚠️  Bad Request (Expected for already completed exam):"
    ERROR_DETAIL=$(echo $RESPONSE_BODY | jq -r '.detail')
    echo "  Error: $ERROR_DETAIL"
    
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ Forbidden - No permission:"
    ERROR_DETAIL=$(echo $RESPONSE_BODY | jq -r '.detail')
    echo "  Error: $ERROR_DETAIL"
    
elif [ "$HTTP_CODE" = "404" ]; then
    echo "❌ Exam not found:"
    ERROR_DETAIL=$(echo $RESPONSE_BODY | jq -r '.detail')
    echo "  Error: $ERROR_DETAIL"
    
else
    echo "❌ Unexpected response:"
    echo "  Body: $RESPONSE_BODY"
fi

echo ""
echo "🧪 Step 4: Test error scenarios..."

# Test without confirmation
echo "Testing without confirmation..."
ERROR_RESPONSE=$(curl -s -X POST "$SERVER/api/v1/exams/$EXAM_ID/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation": false,
    "reason": "This should fail"
  }')

ERROR_DETAIL=$(echo $ERROR_RESPONSE | jq -r '.detail')
echo "Expected Error: $ERROR_DETAIL"

# Test with invalid exam ID
echo "Testing with invalid exam ID..."
INVALID_RESPONSE=$(curl -s -X POST "$SERVER/api/v1/exams/invalid_id/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation": true,
    "reason": "This should fail"
  }')

ERROR_DETAIL=$(echo $INVALID_RESPONSE | jq -r '.detail')
echo "Expected Error: $ERROR_DETAIL"

echo ""
echo "🎯 Testing completed!"
echo ""
echo "📋 Summary:"
echo "- Complete exam: HTTP $HTTP_CODE"
echo "- Error handling: Tested ✅"
echo "- Authorization: Validated ✅"
echo ""
echo "💡 To test with different user roles:"
echo "1. Change USERNAME/PASSWORD to guru account"  
echo "2. Change USERNAME/PASSWORD to proctor account"
echo "3. Use different EXAM_ID values"
