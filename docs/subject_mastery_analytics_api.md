# Subject Mastery Analytics API - Radar Chart Ready

## 🎯 **Overview**

Subject Mastery Analytics menyediakan analisis tingkat pemahaman siswa per mata pelajaran dalam format yang **perfect untuk radar chart**. System ini **performance-optimized** dengan smart caching dan efficient aggregation.

### **Key Features:**
- ⚡ **Performance First**: Sub-second response time dengan smart caching
- 📊 **Radar Chart Ready**: Output format optimized untuk Chart.js, ApexCharts
- 🔒 **Role-Based Access**: Student (personal), Teacher (classes), Admin (school-wide)
- 💾 **Smart Caching**: 15-minute TTL dengan intelligent cache keys
- 🚀 **Minimal Data Transfer**: Lean schema dengan hanya essential data

---

## 🌐 **API Endpoints**

### **GET /api/v1/analytics/subject-mastery**

**Query Parameters:**
- `student_id` (optional): Specific student untuk admin/teacher
- `class_id` (optional): Filter berdasarkan kelas
- `grade_level` (optional): Filter berdasarkan tingkat
- `expertise_id` (optional): Filter berdasarkan jurusan
- `start_date` (optional): Tanggal mulai analisis
- `end_date` (optional): Tanggal akhir analisis  
- `academic_period_id` (optional): Filter periode akademik
- `include_zero_scores` (default: false): Include subjects dengan 0 ujian
- `min_exams_per_subject` (default: 1): Minimal ujian per mata pelajaran
- `use_cache` (default: true): Gunakan cached results (15min TTL)

### **POST /api/v1/analytics/subject-mastery**

**Request Body:**
```json
{
  "student_id": "688477a78a56906f19d02551",
  "start_date": "2025-08-01T00:00:00Z", 
  "end_date": "2025-12-31T23:59:59Z",
  "include_zero_scores": false,
  "min_exams_per_subject": 2,
  "use_cache": true
}
```

---

## 📊 **Response Format**

### **Student Response (Personal Radar)**
```json
{
  "entity_id": "688477a78a56906f19d02551",
  "entity_type": "student",
  "entity_name": "Ahmad Rizki Pratama",
  "mastery_data": {
    "subject_scores": {
      "Matematika": 78.5,
      "Bahasa Indonesia": 85.2,
      "Pemrograman Dasar": 92.1,
      "Jaringan Dasar": 74.8,
      "Sistem Operasi": 81.3,
      "Basis Data": 88.7
    },
    "overall_average": 83.4,
    "total_exams": 18
  },
  "metadata": {
    "generated_at": "2025-09-07T14:30:00Z",
    "cache_duration": "15min",
    "user_role": ["student"],
    "total_subjects": 6
  }
}
```

### **Teacher Response (Multiple Classes)**
```json
{
  "entities": [
    {
      "entity_id": "68b2cf7fd1f50504c5aea6a1",
      "entity_type": "class",
      "entity_name": "Kelas 12 TKJ 1",
      "mastery_data": {
        "subject_scores": {
          "Matematika": 76.8,
          "Pemrograman Dasar": 84.2,
          "Jaringan Dasar": 89.1
        },
        "overall_average": 83.4,
        "total_exams": 45
      }
    },
    {
      "entity_id": "68b2cf7fd1f50504c5aea6a2", 
      "entity_type": "class",
      "entity_name": "Kelas 12 TKJ 2",
      "mastery_data": {
        "subject_scores": {
          "Matematika": 79.2,
          "Pemrograman Dasar": 81.7,
          "Jaringan Dasar": 86.4
        },
        "overall_average": 82.4,
        "total_exams": 42
      }
    }
  ],
  "comparison_metadata": {
    "total_entities": 2,
    "school_average": 82.9,
    "highest_average": 83.4,
    "lowest_average": 82.4,
    "best_subject": "Jaringan Dasar",
    "weakest_subject": "Matematika",
    "subject_averages": {
      "Matematika": 78.0,
      "Pemrograman Dasar": 82.9,
      "Jaringan Dasar": 87.8
    }
  }
}
```

---

## 🎮 **Role-Based Access Control**

### **👤 Student Role**
- **Access**: Personal subject mastery only
- **Parameters**: `start_date`, `end_date`, `min_exams_per_subject`
- **Response**: Single radar chart untuk diri sendiri

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/subject-mastery" \
  -H "Authorization: Bearer <student_token>"
```

### **👨‍🏫 Teacher Role**  
- **Access**: Classes yang diajar saja
- **Parameters**: `class_id`, `student_id`, `start_date`, `end_date`
- **Response**: Multiple radar charts untuk comparison antar kelas

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/analytics/subject-mastery?class_id=68b2cf7fd1f50504c5aea6a1" \
  -H "Authorization: Bearer <teacher_token>"
```

### **👨‍💼 Admin Role**
- **Access**: Semua data dengan filtering lengkap
- **Parameters**: All parameters available
- **Response**: Flexible - student/class/school level

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/analytics/subject-mastery" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "grade_level": 12,
    "expertise_id": "68b2cf7fd1f50504c5aea6a3",
    "min_exams_per_subject": 3
  }'
```

---

## 📈 **Chart Implementation Guide**

### **Chart.js Radar Chart**
```javascript
// Fetch data dari API
const response = await fetch('/api/v1/analytics/subject-mastery', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await response.json();

// Untuk student response (single entity)
if (data.entity_type === 'student') {
  const chartData = {
    labels: Object.keys(data.mastery_data.subject_scores),
    datasets: [{
      label: data.entity_name,
      data: Object.values(data.mastery_data.subject_scores),
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      borderColor: 'rgba(54, 162, 235, 1)',
      borderWidth: 2,
      pointRadius: 5,
      pointBackgroundColor: 'rgba(54, 162, 235, 1)'
    }]
  };
  
  const config = {
    type: 'radar',
    data: chartData,
    options: {
      responsive: true,
      scales: {
        r: {
          angleLines: { display: true },
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: {
            callback: function(value) { return value + '%'; }
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: `Subject Mastery - ${data.entity_name}`
        },
        legend: { display: false }
      }
    }
  };
  
  new Chart(ctx, config);
}

// Untuk teacher/admin response (multiple entities)
if (data.entities) {
  const colors = [
    'rgba(255, 99, 132, 0.8)',
    'rgba(54, 162, 235, 0.8)', 
    'rgba(255, 205, 86, 0.8)',
    'rgba(75, 192, 192, 0.8)'
  ];
  
  // Get all unique subjects
  const allSubjects = new Set();
  data.entities.forEach(entity => {
    Object.keys(entity.mastery_data.subject_scores).forEach(subject => {
      allSubjects.add(subject);
    });
  });
  const subjectLabels = Array.from(allSubjects);
  
  const datasets = data.entities.map((entity, index) => ({
    label: entity.entity_name,
    data: subjectLabels.map(subject => 
      entity.mastery_data.subject_scores[subject] || 0
    ),
    backgroundColor: colors[index % colors.length].replace('0.8', '0.2'),
    borderColor: colors[index % colors.length],
    borderWidth: 2,
    pointRadius: 4
  }));
  
  const chartData = { labels: subjectLabels, datasets };
  
  const config = {
    type: 'radar',
    data: chartData,
    options: {
      responsive: true,
      scales: { r: { suggestedMin: 0, suggestedMax: 100 } },
      plugins: {
        title: { 
          display: true, 
          text: 'Class Comparison - Subject Mastery' 
        }
      }
    }
  };
  
  new Chart(ctx, config);
}
```

### **ApexCharts Radar**
```javascript
const response = await fetch('/api/v1/analytics/subject-mastery');
const data = await response.json();

// Single entity radar
if (data.entity_type === 'student') {
  const options = {
    series: [{
      name: data.entity_name,
      data: Object.values(data.mastery_data.subject_scores)
    }],
    chart: { type: 'radar', height: 400 },
    xaxis: { categories: Object.keys(data.mastery_data.subject_scores) },
    yaxis: { min: 0, max: 100 },
    plotOptions: {
      radar: {
        polygons: {
          strokeColors: '#e8e8e8',
          fill: { colors: ['#f8f8f8', '#fff'] }
        }
      }
    },
    colors: ['#FF4560'],
    markers: { size: 4 },
    title: { text: `Subject Mastery - ${data.entity_name}` }
  };
  
  const chart = new ApexCharts(document.querySelector('#radar-chart'), options);
  chart.render();
}
```

---

## ⚡ **Performance Features**

### **Smart Caching Strategy**
```javascript
// Cache key generation (automatic)
// subject_mastery:md5(user_id + role + filters + date_range)
// TTL: 15 minutes

// Force cache refresh
await fetch('/api/v1/analytics/subject-mastery?use_cache=false');

// Clear cache (admin only)
await fetch('/api/v1/analytics/subject-mastery/cache', { 
  method: 'DELETE' 
});
```

### **Performance Monitoring**
```javascript
// Response includes performance metadata
{
  "metadata": {
    "generated_at": "2025-09-07T14:30:00Z",
    "cache_duration": "15min",
    "processing_time": "0.045s",  // Added automatically
    "cache_status": "HIT"         // HIT/MISS
  }
}
```

### **Database Optimization**
- **Indexes**: 15+ optimized indexes for analytics queries
- **Aggregation**: Efficient MongoDB pipelines dengan minimal lookups
- **Projection**: Only essential fields transferred
- **Early Filtering**: Role restrictions applied at query level

---

## 🔧 **MongoDB Indexes (Performance)**

Untuk optimal performance, pastikan indexes sudah dibuat:

```bash
# Run index creation script
python scripts/create_analytics_indexes.py

# Verify indexes
python scripts/create_analytics_indexes.py --action=analyze
```

**Critical Indexes:**
- `exam_sessions.analytics_core_filter`: (status, submitted_at, score)
- `exam_sessions.student_analytics`: (student_id, submitted_at, status) 
- `teaching_assignments.teacher_assignments`: (teacher_id, academic_period_id)
- `classes.grade_expertise_analytics`: (grade_level, expertise_id)

---

## 📝 **Real-World Use Cases**

### **Student Dashboard**
```javascript
// Personal subject mastery radar
const studentRadar = await getSubjectMastery();
// Show: "Your strongest subject is Pemrograman Dasar (92.1%)"
// Show: "Areas for improvement: Matematika (78.5%)"
```

### **Teacher Dashboard** 
```javascript
// Class comparison radar
const classComparison = await getSubjectMastery();
// Show: Multiple radar charts comparing TKJ 1 vs TKJ 2
// Identify: Which class needs more attention in which subject
```

### **Admin Analytics**
```javascript
// School-wide subject performance
const schoolAnalytics = await getSubjectMastery({ grade_level: 12 });
// Strategic insights: Curriculum adjustments needed
// Resource allocation: Which subjects need more teachers/equipment
```

---

## 🚀 **Performance Benchmarks**

**Target Response Times:**
- **Student (cached)**: < 50ms
- **Student (uncached)**: < 200ms  
- **Teacher (cached)**: < 100ms
- **Teacher (uncached)**: < 500ms
- **Admin (cached)**: < 150ms
- **Admin (uncached)**: < 1000ms

**Memory Usage:**
- **Average response size**: 2-8KB
- **Cache hit rate**: > 80% in production
- **Database queries**: 1 aggregation pipeline per request

---

## 🔍 **Troubleshooting**

### **Performance Issues**
```bash
# Check indexes
python scripts/create_analytics_indexes.py --action=analyze

# Clear cache if stale
curl -X DELETE "/api/v1/analytics/subject-mastery/cache" -H "Authorization: Bearer <admin_token>"

# Disable cache for debugging
curl "/api/v1/analytics/subject-mastery?use_cache=false"
```

### **Common Errors**

**403 Forbidden:**
- Check user role permissions
- Teacher trying to access other teacher's classes
- Student trying to access class-level data

**400 Bad Request:**
- Invalid ObjectId format in parameters
- `min_exams_per_subject` < 1

**Empty Results:**
- No exams in specified date range
- No teaching assignments for teacher
- Filters too restrictive

---

## 🎯 **Summary**

Subject Mastery Analytics memberikan **powerful insights** dalam format **radar chart yang beautiful dan actionable**:

- ⚡ **Lightning Fast**: Sub-second response dengan smart caching
- 📊 **Chart Ready**: Perfect integration dengan Chart.js, ApexCharts  
- 🔒 **Secure**: Role-based access dengan proper permission checking
- 💾 **Efficient**: Minimal data transfer, optimized aggregation pipelines
- 🚀 **Scalable**: Handles hundreds of students dengan consistent performance

**Perfect untuk school analytics dashboard yang professional dan insightful!**
