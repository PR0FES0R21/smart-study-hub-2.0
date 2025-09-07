# Analytics API - Quick Reference Card

**🚀 Ready-to-Use Analytics Endpoints - Frontend Team**

---

## 📊 **Score Trend Analytics** (Line Charts)

### **Endpoints:**
```
GET  /api/v1/analytics/score-trend
POST /api/v1/analytics/score-trend
```

### **Quick Parameters:**
```bash
# Student - Personal trend
GET /analytics/score-trend

# Teacher - Class comparison  
GET /analytics/score-trend?group_by=class

# Admin - Grade comparison
GET /analytics/score-trend?group_by=grade&grade_level=12
```

### **Response Format:**
- `series[]`: Array of chart lines
- `series[].label`: Line name (e.g., "Kelas 12 TKJ 1")
- `series[].data[]`: Array of data points
- `data[].date`: X-axis (timestamp)
- `data[].score`: Y-axis (0-100)
- `data[].exam_title`: Tooltip info

---

## 🎯 **Subject Mastery Analytics** (Radar Charts)

### **Endpoints:**
```
GET    /api/v1/analytics/subject-mastery
POST   /api/v1/analytics/subject-mastery  
DELETE /api/v1/analytics/subject-mastery/cache (admin)
```

### **Quick Parameters:**
```bash
# Student - Personal radar
GET /analytics/subject-mastery

# Teacher - Class average
GET /analytics/subject-mastery?class_id={id}

# Admin - School overview  
GET /analytics/subject-mastery?grade_level=12
```

### **Response Format:**
- `entity_type`: "student" | "class" | "school"
- `mastery_data.subject_scores`: Object {subject: score}
- `mastery_data.overall_average`: Overall GPA
- `entities[]`: Array for multi-entity responses

---

## 🔒 **Authentication**

### **Headers Required:**
```javascript
{
  'Authorization': 'Bearer <jwt_token>',
  'Content-Type': 'application/json'
}
```

### **Role Access:**
- **Student**: Own data only
- **Teacher**: Classes taught only  
- **Admin**: Full school access

---

## ⚡ **Performance**

### **Response Times:**
- **Cached**: < 100ms
- **Uncached**: 200ms - 1.5s
- **Cache TTL**: 15 minutes

### **Optimization:**
- Use `use_cache=true` (default)
- Implement loading states
- Add retry logic
- Debounce filter changes (300ms)

---

## 🎨 **Chart Integration**

### **Line Chart (Score Trend):**
```javascript
// X-axis: data.series[0].data.map(d => d.date)
// Y-axis: data.series[0].data.map(d => d.score)  
// Labels: data.series.map(s => s.label)
```

### **Radar Chart (Subject Mastery):**
```javascript
// Axes: Object.keys(data.mastery_data.subject_scores)
// Values: Object.values(data.mastery_data.subject_scores)
// Scale: 0-100
```

---

## 🚨 **Error Handling**

### **HTTP Status Codes:**
- `400`: Invalid parameters
- `401`: Missing/invalid token
- `403`: Insufficient permissions
- `404`: No data found
- `500`: Server error

### **Common Issues:**
- **Empty Response**: Check date range, user permissions
- **403 Error**: Verify user role and entity access
- **Slow Response**: Use caching, check network

---

## 🛠 **Development Tools**

### **API Documentation:**
- **Interactive Docs**: `{API_BASE_URL}/docs`
- **Schema Reference**: Auto-generated Swagger UI

### **Testing:**
- **Postman Collection**: Available from backend team
- **Sample Data**: Test datasets provided
- **Role Testing**: Use different JWT tokens

---

## 📱 **Mobile Considerations**

### **Responsive Design:**
- **Response Size**: 2-15KB (lightweight)
- **Chart Libraries**: Ensure mobile-friendly
- **Touch Interactions**: Implement for radar charts
- **Loading States**: Show on slower connections

---

## 💡 **Implementation Tips**

### **Best Practices:**
1. **Cache API responses** locally for better UX
2. **Implement progressive loading** (charts first, details later)
3. **Use role-based UI rendering** 
4. **Add export functionality** (PNG/PDF/CSV)
5. **Implement accessibility features** (screen readers)

### **Performance Tips:**
1. **Debounce filter inputs** to avoid excessive API calls
2. **Use Chart.js or ApexCharts** for optimal performance
3. **Implement virtual scrolling** for large datasets
4. **Add skeleton loading states** for better perceived performance

---

## 📞 **Support**

### **Need Help?**
- **Technical Issues**: Contact backend analytics team
- **API Questions**: Check `/docs` endpoint first
- **Performance Issues**: Report with specific examples
- **Feature Requests**: Discuss with product team

### **Resources:**
- **Full Documentation**: `docs/subject_mastery_analytics_api.md`
- **Implementation Guide**: `docs/FRONTEND_IMPLEMENTATION_REPORT.md`
- **Code Examples**: Available in documentation files

---

**🎯 Quick Start: Authentication → API Call → Parse Response → Render Chart → Add Interactions**

**⚡ Performance First: Always use caching, implement loading states, handle errors gracefully**
