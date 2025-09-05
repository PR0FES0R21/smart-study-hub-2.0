# 📊 Enhanced Teacher Exams Endpoint with Analytics Status

## 🎯 Overview

Endpoint `/api/v1/exams/teacher` telah dienhance untuk **include analytics status** di setiap ujian. Sekarang guru dapat:

- ✅ Lihat status analytics langsung dari halaman daftar ujian
- ✅ Tahu ujian mana yang sudah ada analytics (completed)
- ✅ Tahu ujian mana yang sedang di-generate (pending/processing) 
- ✅ Tahu ujian mana yang belum ada analytics (not_generated)
- ✅ Monitor progress real-time untuk analytics yang sedang di-generate
- ✅ Akses direct ke analytics page atau trigger generation dari UI

---

## 📋 Endpoint Details

**URL:** `GET /api/v1/exams/teacher`

**Method:** GET

**Authorization:** Bearer Token (Teacher role)

**New Analytics Fields Added:**
- `analytics_status`
- `analytics_generated_at` 
- `analytics_task_id`
- `analytics_progress`

---

## 📊 Analytics Status Values

| Status | Description | UI Action |
|--------|-------------|-----------|
| `not_generated` | Belum ada analytics | Tampilkan tombol "Generate Analytics" |
| `pending` | Task analytics dalam antrian | Tampilkan "Queued..." + progress indicator |
| `processing` | Sedang generate analytics | Tampilkan progress bar + percentage |
| `completed` | Analytics sudah siap | Tampilkan tombol "View Analytics" |
| `failed` | Generation gagal | Tampilkan tombol "Retry Generation" |

---

## 📤 Response Example

### Success Response (200)

```json
{
  "total_items": 5,
  "total_pages": 1,
  "current_page": 1,
  "limit": 20,
  "data": [
    {
      "_id": "68920557e58cfa66adfcdd7f",
      "title": "Ujian Matematika Semester 1",
      "exam_type": "official_uts",
      "duration_minutes": 120,
      "availability_start_time": "2025-01-10T08:00:00Z",
      "availability_end_time": "2025-01-10T10:00:00Z",
      "status": "completed",
      "settings": {
        "shuffle_questions": true,
        "shuffle_options": true,
        "show_results_after_submission": false
      },
      "academic_period_id": "68920557e58cfa66adfcdd9a",
      "teaching_assignment_id": "68920557e58cfa66adfcdd8a",
      "proctor_ids": ["68822f07979cbba23e6db950"],
      "question_ids": ["q1", "q2", "q3"],
      
      // ✨ NEW ANALYTICS FIELDS
      "analytics_status": "completed",
      "analytics_generated_at": "2025-01-10T12:30:15Z",
      "analytics_task_id": null,
      "analytics_progress": null,
      
      // Existing fields
      "subject_details": { /* subject info */ },
      "class_details": { /* class info */ },
      "teaching_assignment": { /* assignment info */ }
    },
    {
      "_id": "68920557e58cfa66adfcdd8g",
      "title": "Ujian Fisika Bab 2",
      "exam_type": "quiz",
      "duration_minutes": 90,
      "availability_start_time": "2025-01-11T08:00:00Z",
      "availability_end_time": "2025-01-11T09:30:00Z",
      "status": "ongoing",
      
      // ✨ Analytics sedang di-generate
      "analytics_status": "processing",
      "analytics_generated_at": null,
      "analytics_task_id": "analytics_68920557e58cfa66adfcdd8g_teacher_1756978890",
      "analytics_progress": 65.0,
      
      "subject_details": { /* subject info */ },
      "class_details": { /* class info */ }
    },
    {
      "_id": "68920557e58cfa66adfcdd9h",
      "title": "Ujian Kimia Bab 1", 
      "exam_type": "daily_test",
      "duration_minutes": 60,
      "availability_start_time": "2025-01-12T08:00:00Z",
      "availability_end_time": "2025-01-12T09:00:00Z",
      "status": "ready",
      
      // ✨ Belum ada analytics
      "analytics_status": "not_generated",
      "analytics_generated_at": null,
      "analytics_task_id": null,
      "analytics_progress": null,
      
      "subject_details": { /* subject info */ },
      "class_details": { /* class info */ }
    }
  ]
}
```

---

## 🧪 Testing Examples

### Using cURL

```bash
# Get JWT Token terlebih dahulu
export TOKEN="your_teacher_jwt_token"

# Get exams with analytics status
curl -X GET "http://localhost:8000/api/v1/exams/teacher?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.data[] | {title: .title, analytics_status: .analytics_status, analytics_progress: .analytics_progress}'
```

### Using JavaScript/Fetch

```javascript
const fetchTeacherExamsWithAnalytics = async () => {
  try {
    const response = await fetch('/api/v1/exams/teacher?page=1&limit=20', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch exams');
    }
    
    const data = await response.json();
    
    // Process exams dengan analytics status
    data.data.forEach(exam => {
      console.log(`Exam: ${exam.title}`);
      console.log(`Analytics Status: ${exam.analytics_status}`);
      
      switch (exam.analytics_status) {
        case 'not_generated':
          console.log('  ➤ Can generate analytics');
          break;
        case 'processing':
          console.log(`  ➤ Generating... ${exam.analytics_progress}%`);
          break;
        case 'completed':
          console.log(`  ➤ Analytics ready since ${exam.analytics_generated_at}`);
          break;
        case 'pending':
          console.log('  ➤ Queued for generation');
          break;
        case 'failed':
          console.log('  ➤ Generation failed, can retry');
          break;
      }
    });
    
    return data;
    
  } catch (error) {
    console.error('Error fetching exams:', error);
    throw error;
  }
};
```

---

## 🎨 Frontend Integration Examples

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

const ExamListWithAnalytics = () => {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchExams();
  }, []);
  
  const fetchExams = async () => {
    try {
      const response = await fetch('/api/v1/exams/teacher', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setExams(data.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const renderAnalyticsStatus = (exam) => {
    switch (exam.analytics_status) {
      case 'not_generated':
        return (
          <button 
            className="btn btn-primary"
            onClick={() => generateAnalytics(exam._id)}
          >
            Generate Analytics
          </button>
        );
        
      case 'pending':
        return (
          <div className="badge badge-warning">
            <span className="spinner"></span> Queued
          </div>
        );
        
      case 'processing':
        return (
          <div className="progress-container">
            <div className="progress-bar" style={{width: `${exam.analytics_progress}%`}}>
              {exam.analytics_progress.toFixed(1)}%
            </div>
            <small>Generating analytics...</small>
          </div>
        );
        
      case 'completed':
        return (
          <button 
            className="btn btn-success"
            onClick={() => viewAnalytics(exam._id)}
          >
            View Analytics
          </button>
        );
        
      case 'failed':
        return (
          <button 
            className="btn btn-danger"
            onClick={() => retryAnalytics(exam._id)}
          >
            Retry Generation
          </button>
        );
        
      default:
        return <span className="badge badge-secondary">Unknown</span>;
    }
  };
  
  const generateAnalytics = async (examId) => {
    try {
      const response = await fetch(`/api/v1/teacher-analytics/exams/${examId}/analytics/generate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          force_regenerate: false,
          include_comparison: true
        })
      });
      
      if (response.ok) {
        // Refresh data untuk update status
        fetchExams();
        alert('Analytics generation started!');
      }
    } catch (error) {
      console.error('Error generating analytics:', error);
    }
  };
  
  const viewAnalytics = (examId) => {
    // Navigate ke halaman analytics
    window.location.href = `/analytics/${examId}`;
  };
  
  if (loading) return <div>Loading exams...</div>;
  
  return (
    <div className="exam-list">
      <h2>My Exams</h2>
      <div className="table-responsive">
        <table className="table">
          <thead>
            <tr>
              <th>Exam Title</th>
              <th>Type</th>
              <th>Status</th>
              <th>Date</th>
              <th>Analytics</th>
            </tr>
          </thead>
          <tbody>
            {exams.map(exam => (
              <tr key={exam._id}>
                <td>{exam.title}</td>
                <td>{exam.exam_type}</td>
                <td>{exam.status}</td>
                <td>{new Date(exam.availability_start_time).toLocaleDateString()}</td>
                <td>{renderAnalyticsStatus(exam)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ExamListWithAnalytics;
```

### Vue.js Component Example

```vue
<template>
  <div class="exam-list">
    <h2>My Exams</h2>
    <div class="table-responsive">
      <table class="table">
        <thead>
          <tr>
            <th>Exam Title</th>
            <th>Type</th>
            <th>Status</th>
            <th>Analytics</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="exam in exams" :key="exam._id">
            <td>{{ exam.title }}</td>
            <td>{{ exam.exam_type }}</td>
            <td>{{ exam.status }}</td>
            <td>
              <!-- Analytics Status Component -->
              <div v-if="exam.analytics_status === 'not_generated'">
                <button @click="generateAnalytics(exam._id)" class="btn btn-primary">
                  Generate Analytics
                </button>
              </div>
              
              <div v-else-if="exam.analytics_status === 'pending'" class="badge badge-warning">
                <span class="spinner"></span> Queued
              </div>
              
              <div v-else-if="exam.analytics_status === 'processing'" class="progress-container">
                <div class="progress-bar" :style="{width: exam.analytics_progress + '%'}">
                  {{ exam.analytics_progress.toFixed(1) }}%
                </div>
                <small>Generating analytics...</small>
              </div>
              
              <div v-else-if="exam.analytics_status === 'completed'">
                <button @click="viewAnalytics(exam._id)" class="btn btn-success">
                  View Analytics
                </button>
                <small class="text-muted">
                  Generated {{ formatDate(exam.analytics_generated_at) }}
                </small>
              </div>
              
              <div v-else-if="exam.analytics_status === 'failed'">
                <button @click="retryAnalytics(exam._id)" class="btn btn-danger">
                  Retry Generation
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ExamListWithAnalytics',
  data() {
    return {
      exams: [],
      loading: true
    }
  },
  async mounted() {
    await this.fetchExams();
  },
  methods: {
    async fetchExams() {
      try {
        const response = await this.$http.get('/api/v1/exams/teacher');
        this.exams = response.data.data;
      } catch (error) {
        console.error('Error fetching exams:', error);
      } finally {
        this.loading = false;
      }
    },
    
    async generateAnalytics(examId) {
      try {
        await this.$http.post(`/api/v1/teacher-analytics/exams/${examId}/analytics/generate`, {
          force_regenerate: false,
          include_comparison: true
        });
        
        this.$toast.success('Analytics generation started!');
        await this.fetchExams(); // Refresh data
      } catch (error) {
        this.$toast.error('Failed to generate analytics');
      }
    },
    
    viewAnalytics(examId) {
      this.$router.push(`/analytics/${examId}`);
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleDateString();
    }
  }
}
</script>
```

---

## 🔄 Real-time Updates

Untuk real-time updates status analytics, Anda bisa implement polling:

```javascript
class ExamAnalyticsMonitor {
  constructor() {
    this.pollingInterval = null;
    this.processingExams = new Set();
  }
  
  startMonitoring(exams) {
    // Track exams yang sedang processing
    exams.forEach(exam => {
      if (exam.analytics_status === 'processing' || exam.analytics_status === 'pending') {
        this.processingExams.add(exam._id);
      }
    });
    
    // Start polling jika ada yang processing
    if (this.processingExams.size > 0) {
      this.startPolling();
    }
  }
  
  startPolling() {
    if (this.pollingInterval) return; // Already polling
    
    this.pollingInterval = setInterval(async () => {
      try {
        const response = await fetch('/api/v1/exams/teacher', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        let stillProcessing = false;
        
        data.data.forEach(exam => {
          if (this.processingExams.has(exam._id)) {
            if (exam.analytics_status === 'completed' || exam.analytics_status === 'failed') {
              // Task selesai, remove from monitoring
              this.processingExams.delete(exam._id);
              this.onAnalyticsComplete(exam);
            } else if (exam.analytics_status === 'processing') {
              // Update progress
              this.onAnalyticsProgress(exam);
              stillProcessing = true;
            }
          }
        });
        
        // Stop polling jika tidak ada yang processing
        if (!stillProcessing) {
          this.stopPolling();
        }
        
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds
  }
  
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }
  
  onAnalyticsProgress(exam) {
    // Update progress in UI
    console.log(`Analytics for ${exam.title}: ${exam.analytics_progress}%`);
    // Emit event atau update state
  }
  
  onAnalyticsComplete(exam) {
    // Handle completion
    if (exam.analytics_status === 'completed') {
      console.log(`Analytics completed for ${exam.title}`);
      // Show success notification
    } else {
      console.log(`Analytics failed for ${exam.title}`);
      // Show error notification
    }
  }
}

// Usage
const monitor = new ExamAnalyticsMonitor();
monitor.startMonitoring(examsData);
```

---

## 🎯 Benefits for Teachers

### **Improved UX:**
- ✅ **Single Dashboard** - Semua info di satu tempat
- ✅ **Real-time Status** - Tahu kapan analytics siap
- ✅ **Progress Monitoring** - Lihat progress generation
- ✅ **Direct Actions** - Generate atau view langsung dari list

### **Enhanced Workflow:**
1. **List Exams** - Lihat semua ujian dengan status analytics
2. **Generate Analytics** - Klik tombol untuk ujian yang belum ada analytics  
3. **Monitor Progress** - Lihat real-time progress generation
4. **View Results** - Langsung ke analytics page saat siap

### **Better Information:**
- **Status Clarity** - Jelas status masing-masing ujian
- **Time Information** - Kapan analytics terakhir di-generate
- **Task Tracking** - ID task untuk debugging jika perlu

---

## 🔧 Query Performance

### **Database Optimization:**
- ✅ **Single Query** - Semua data diambil dalam 1 aggregation pipeline
- ✅ **Efficient Joins** - Optimal lookup dengan teacher_analytics dan analytics_tasks
- ✅ **Indexed Fields** - exam_metadata.exam_id and task teacher_id indexed

### **Response Size:**
- ✅ **Minimal Fields** - Hanya analytics metadata, bukan full analytics data
- ✅ **Pagination** - Support limit untuk large datasets
- ✅ **Field Selection** - Cleanup temporary fields

---

**Dengan enhancement ini, guru mendapat experience yang jauh lebih baik untuk manage analytics ujian mereka!** 🚀✨
