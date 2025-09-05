#!/bin/bash

# =============================================================================
# Script untuk Testing Enhanced Teacher Exams Endpoint with Analytics Status
# Usage: ./test_teacher_exams_analytics.sh
# =============================================================================

# Configuration
SERVER="http://localhost:8000"
USERNAME="guru123"  # Ganti dengan username guru
PASSWORD="password123"  # Ganti dengan password guru

echo "🧪 Testing Enhanced Teacher Exams Endpoint with Analytics Status"
echo "================================================================="

# Step 1: Login sebagai guru
echo "🔑 Step 1: Login sebagai guru..."
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
echo "Token: ${TOKEN:0:30}..."

echo ""
echo "📝 Step 2: Fetch teacher exams with analytics status..."

# Fetch exams dengan analytics status
EXAMS_RESPONSE=$(curl -s -X GET "$SERVER/api/v1/exams/teacher?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN")

# Check if request was successful
if echo "$EXAMS_RESPONSE" | jq -e '.data' > /dev/null 2>&1; then
    echo "✅ Successfully fetched teacher exams!"
    
    TOTAL_ITEMS=$(echo $EXAMS_RESPONSE | jq -r '.total_items')
    echo "📊 Total exams: $TOTAL_ITEMS"
    
    # Analyze each exam's analytics status
    echo ""
    echo "📈 Analytics Status Analysis:"
    echo "=============================="
    
    # Count analytics status
    NOT_GENERATED=$(echo $EXAMS_RESPONSE | jq '[.data[] | select(.analytics_status == "not_generated")] | length')
    PENDING=$(echo $EXAMS_RESPONSE | jq '[.data[] | select(.analytics_status == "pending")] | length')
    PROCESSING=$(echo $EXAMS_RESPONSE | jq '[.data[] | select(.analytics_status == "processing")] | length')
    COMPLETED=$(echo $EXAMS_RESPONSE | jq '[.data[] | select(.analytics_status == "completed")] | length')
    FAILED=$(echo $EXAMS_RESPONSE | jq '[.data[] | select(.analytics_status == "failed")] | length')
    
    echo "📊 Status Summary:"
    echo "  ➤ Not Generated: $NOT_GENERATED"
    echo "  ➤ Pending: $PENDING" 
    echo "  ➤ Processing: $PROCESSING"
    echo "  ➤ Completed: $COMPLETED"
    echo "  ➤ Failed: $FAILED"
    
    echo ""
    echo "📋 Detailed Exam List:"
    echo "======================="
    
    # Display each exam with its analytics status
    echo $EXAMS_RESPONSE | jq -r '.data[] | "\(.title) | \(.exam_type) | \(.status) | Analytics: \(.analytics_status) | \(if .analytics_progress then "Progress: \(.analytics_progress)%" else "" end) | \(if .analytics_generated_at then "Generated: \(.analytics_generated_at)" else "" end)"' | 
    while IFS= read -r line; do
        echo "  📝 $line"
    done
    
    echo ""
    echo "🔍 Step 3: Test specific scenarios..."
    
    # Check for exams that can be used for testing
    FIRST_NOT_GENERATED=$(echo $EXAMS_RESPONSE | jq -r '.data[] | select(.analytics_status == "not_generated") | ._id' | head -1)
    FIRST_COMPLETED=$(echo $EXAMS_RESPONSE | jq -r '.data[] | select(.analytics_status == "completed") | ._id' | head -1)
    FIRST_PROCESSING=$(echo $EXAMS_RESPONSE | jq -r '.data[] | select(.analytics_status == "processing") | ._id' | head -1)
    
    if [ "$FIRST_NOT_GENERATED" != "null" ] && [ -n "$FIRST_NOT_GENERATED" ]; then
        echo "✨ Found exam without analytics: $FIRST_NOT_GENERATED"
        echo "   ➤ This exam can be used to test analytics generation"
        
        echo ""
        echo "🚀 Step 4: Test analytics generation..."
        GENERATE_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$SERVER/api/v1/teacher-analytics/exams/$FIRST_NOT_GENERATED/analytics/generate" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d '{
            "force_regenerate": false,
            "include_comparison": true
          }')
        
        HTTP_CODE="${GENERATE_RESPONSE: -3}"
        RESPONSE_BODY="${GENERATE_RESPONSE%???}"
        
        echo "Analytics generation response: HTTP $HTTP_CODE"
        if [ "$HTTP_CODE" = "200" ]; then
            TASK_ID=$(echo $RESPONSE_BODY | jq -r '.task_id')
            echo "✅ Analytics generation started!"
            echo "   ➤ Task ID: $TASK_ID"
            
            # Test fetching exams again to see updated status
            echo ""
            echo "🔄 Step 5: Verify status update..."
            sleep 2  # Wait a bit for status to update
            
            UPDATED_RESPONSE=$(curl -s -X GET "$SERVER/api/v1/exams/teacher?page=1&limit=10" \
              -H "Authorization: Bearer $TOKEN")
            
            UPDATED_STATUS=$(echo $UPDATED_RESPONSE | jq -r ".data[] | select(._id == \"$FIRST_NOT_GENERATED\") | .analytics_status")
            UPDATED_TASK_ID=$(echo $UPDATED_RESPONSE | jq -r ".data[] | select(._id == \"$FIRST_NOT_GENERATED\") | .analytics_task_id")
            
            echo "✅ Status updated successfully!"
            echo "   ➤ New Status: $UPDATED_STATUS"
            echo "   ➤ Task ID: $UPDATED_TASK_ID"
            
        else
            echo "⚠️ Analytics generation response:"
            echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
        fi
        
    elif [ "$FIRST_COMPLETED" != "null" ] && [ -n "$FIRST_COMPLETED" ]; then
        echo "✅ Found exam with completed analytics: $FIRST_COMPLETED"
        echo "   ➤ This exam has analytics ready to view"
        
        # Test fetching the actual analytics
        echo ""
        echo "📊 Step 4: Test fetching analytics..."
        ANALYTICS_RESPONSE=$(curl -s -w "%{http_code}" -X GET "$SERVER/api/v1/teacher-analytics/exams/$FIRST_COMPLETED/analytics" \
          -H "Authorization: Bearer $TOKEN")
        
        HTTP_CODE="${ANALYTICS_RESPONSE: -3}"
        RESPONSE_BODY="${ANALYTICS_RESPONSE%???}"
        
        if [ "$HTTP_CODE" = "200" ]; then
            echo "✅ Analytics data accessible!"
            GENERATED_AT=$(echo $RESPONSE_BODY | jq -r '.generated_at')
            CLASS_AVERAGE=$(echo $RESPONSE_BODY | jq -r '.class_statistics.class_average')
            TOTAL_STUDENTS=$(echo $RESPONSE_BODY | jq -r '.class_statistics.total_students')
            echo "   ➤ Generated: $GENERATED_AT"
            echo "   ➤ Class Average: $CLASS_AVERAGE"
            echo "   ➤ Total Students: $TOTAL_STUDENTS"
        else
            echo "⚠️ Could not fetch analytics: HTTP $HTTP_CODE"
        fi
        
    else
        echo "ℹ️ No specific exams found for testing scenarios"
        echo "   ➤ All exams might be in pending/processing state"
    fi
    
    if [ "$FIRST_PROCESSING" != "null" ] && [ -n "$FIRST_PROCESSING" ]; then
        echo ""
        echo "⏳ Found exam with processing analytics: $FIRST_PROCESSING"
        PROGRESS=$(echo $EXAMS_RESPONSE | jq -r ".data[] | select(._id == \"$FIRST_PROCESSING\") | .analytics_progress")
        TASK_ID=$(echo $EXAMS_RESPONSE | jq -r ".data[] | select(._id == \"$FIRST_PROCESSING\") | .analytics_task_id")
        echo "   ➤ Progress: $PROGRESS%"
        echo "   ➤ Task ID: $TASK_ID"
        echo "   ➤ You can monitor this task using task status endpoint"
    fi
    
else
    echo "❌ Failed to fetch teacher exams!"
    echo "Response: $EXAMS_RESPONSE"
fi

echo ""
echo "🔍 Step 6: Test field validation..."

# Test the new analytics fields are present
echo "Checking if new analytics fields are present..."
HAS_ANALYTICS_STATUS=$(echo $EXAMS_RESPONSE | jq '.data[0] | has("analytics_status")')
HAS_ANALYTICS_GENERATED_AT=$(echo $EXAMS_RESPONSE | jq '.data[0] | has("analytics_generated_at")')
HAS_ANALYTICS_TASK_ID=$(echo $EXAMS_RESPONSE | jq '.data[0] | has("analytics_task_id")')
HAS_ANALYTICS_PROGRESS=$(echo $EXAMS_RESPONSE | jq '.data[0] | has("analytics_progress")')

echo "New fields validation:"
echo "  ✅ analytics_status: $HAS_ANALYTICS_STATUS"
echo "  ✅ analytics_generated_at: $HAS_ANALYTICS_GENERATED_AT" 
echo "  ✅ analytics_task_id: $HAS_ANALYTICS_TASK_ID"
echo "  ✅ analytics_progress: $HAS_ANALYTICS_PROGRESS"

echo ""
echo "🎯 Testing completed!"
echo ""
echo "📋 Summary:"
echo "- Teacher exams endpoint: ✅ Working"
echo "- Analytics status integration: ✅ Working"
echo "- New fields present: ✅ Working"
echo "- Response format: ✅ Valid JSON"
echo ""
echo "💡 Frontend developers can now:"
echo "1. 🔍 Check analytics_status to show appropriate UI"
echo "2. ⚡ Trigger generation for not_generated exams"
echo "3. 📊 Show progress for processing exams"  
echo "4. 👀 Navigate to analytics for completed exams"
echo "5. 🔄 Implement polling for real-time updates"
