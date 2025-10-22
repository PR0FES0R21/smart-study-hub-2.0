# Completion Criteria Guide - Module Completion Rules

**Purpose:** Menentukan kapan siswa dianggap **selesai menyelesaikan module**.

---

## 📋 Overview

`completion_criteria` adalah aturan yang menentukan requirement untuk menyelesaikan sebuah module. Ini mengontrol:
- Berapa persen lessons yang harus diselesaikan
- Skor minimal yang harus dicapai
- Aturan custom tambahan

---

## 🏗️ Structure

```json
{
  "type": "all_required | percentage | points | custom",
  "required_percentage": 0-100,
  "minimum_score": 0-100,
  "custom_rules": []
}
```

---

## 🎯 Type Options

### **1. `"all_required"` - Selesaikan Semua (Default)**

**Meaning:** Siswa **harus menyelesaikan semua lessons** yang ditandai `required: true`.

**Example:**
```json
{
  "type": "all_required",
  "required_percentage": 100,
  "minimum_score": 0
}
```

**Use Case:**
```
Module: Matematika Dasar
├─ Lesson 1: Pengenalan (required) ✅ Must complete
├─ Lesson 2: Operasi Dasar (required) ✅ Must complete
├─ Lesson 3: Latihan (required) ✅ Must complete
└─ Lesson 4: Bonus (optional) ⚪ Can skip

Student completion: 3/3 required lessons = ✅ Module completed
```

**When to use:**
- Basic modules yang semua materi penting
- Course fundamental yang tidak boleh dilewat
- Sequential learning path

---

### **2. `"percentage"` - Selesaikan X Persen**

**Meaning:** Siswa cukup menyelesaikan **X% dari total lessons**.

**Example:**
```json
{
  "type": "percentage",
  "required_percentage": 80,
  "minimum_score": 70
}
```

**Use Case:**
```
Module: Enrichment Materials (10 lessons)
Required: 80% = 8 lessons
Minimum score per lesson: 70

Student progress:
- Completed 8 lessons with score ≥ 70 = ✅ Module completed
- Completed 7 lessons = ❌ Not yet (need 1 more)
- Completed 8 lessons but 2 scored < 70 = ❌ Not yet (score too low)
```

**When to use:**
- Enrichment/optional content
- Self-paced learning
- Modules dengan banyak alternatif materi

---

### **3. `"points"` - Kumpulkan X Poin Total**

**Meaning:** Siswa harus mengumpulkan **total poin minimal** dari semua lessons/assessments.

**Example:**
```json
{
  "type": "points",
  "required_percentage": 100,
  "minimum_score": 500
}
```

**Use Case:**
```
Module: Project-Based Learning
Total points available: 1000

Scoring:
- Lesson 1: 100 points (scored 80)
- Lesson 2: 200 points (scored 150)
- Lesson 3: 300 points (scored 280)
- Assessment: 400 points (scored 0 - not taken)

Total: 80 + 150 + 280 = 510 points ≥ 500 = ✅ Module completed
```

**When to use:**
- Gamified learning
- Flexible completion paths
- Weighted assessments

---

### **4. `"custom"` - Aturan Custom**

**Meaning:** Siswa harus memenuhi **aturan-aturan custom** yang didefinisikan.

**Example:**
```json
{
  "type": "custom",
  "required_percentage": 100,
  "minimum_score": 0,
  "custom_rules": [
    {
      "rule_type": "must_complete_lessons",
      "lesson_ids": ["lesson1_id", "lesson2_id"],
      "description": "Must complete core lessons"
    },
    {
      "rule_type": "minimum_assessment_score",
      "assessment_id": "final_exam_id",
      "score": 80,
      "description": "Must score 80+ on final exam"
    },
    {
      "rule_type": "time_based",
      "minimum_time_spent": 3600,
      "description": "Must spend at least 1 hour"
    }
  ]
}
```

**Use Case:**
```
Module: Advanced Course with Final Exam

Requirements:
1. Complete core lessons (Lesson 1 & 2)
2. Score 80+ on final exam
3. Spend minimum 1 hour in module

Student status:
- Core lessons: ✅ Completed
- Final exam: ✅ Score 85
- Time spent: ❌ 45 minutes (need 15 more)
= ❌ Module not completed yet
```

**When to use:**
- Complex certification courses
- Multi-requirement modules
- Adaptive learning paths

---

## 📝 Field Descriptions

### **`type`** (string) - Required
**Options:** `"all_required"` | `"percentage"` | `"points"` | `"custom"`  
**Description:** Tipe kriteria completion

---

### **`required_percentage`** (number) - Required
**Range:** 0-100  
**Description:** 
- For `"all_required"`: Usually 100 (all required lessons)
- For `"percentage"`: Percentage of lessons to complete
- For `"points"`: Usually 100 (consider all possible points)
- For `"custom"`: Usually 100

---

### **`minimum_score`** (number) - Required
**Range:** 0-100  
**Description:**
- For `"all_required"`: Minimum score per lesson (0 = no minimum)
- For `"percentage"`: Minimum score per lesson
- For `"points"`: Total minimum points to collect
- For `"custom"`: Usually 0 (defined in custom_rules)

---

### **`custom_rules`** (array) - Optional
**Type:** Array of rule objects  
**Description:** Custom rules untuk advanced scenarios

**Rule Object Structure:**
```json
{
  "rule_type": "string",
  "description": "string",
  // ... other fields depending on rule_type
}
```

---

## 🎨 Complete Examples

### **Example 1: Basic Course (No Grading)**

```json
{
  "type": "all_required",
  "required_percentage": 100,
  "minimum_score": 0
}
```

**Scenario:** Introduction course - siswa cukup membaca/menonton semua materi, tidak perlu skor.

---

### **Example 2: Graded Course**

```json
{
  "type": "all_required",
  "required_percentage": 100,
  "minimum_score": 70
}
```

**Scenario:** Academic course - siswa harus menyelesaikan semua dengan skor minimal 70.

---

### **Example 3: Flexible Learning**

```json
{
  "type": "percentage",
  "required_percentage": 80,
  "minimum_score": 60
}
```

**Scenario:** Elective course - siswa pilih 80% materi favorit dengan skor 60+.

---

### **Example 4: Certification Course**

```json
{
  "type": "custom",
  "required_percentage": 100,
  "minimum_score": 0,
  "custom_rules": [
    {
      "rule_type": "must_complete_lessons",
      "lesson_ids": ["core1", "core2", "core3"],
      "description": "Complete all core lessons"
    },
    {
      "rule_type": "minimum_assessment_score",
      "assessment_id": "certification_exam",
      "score": 85,
      "description": "Pass certification exam with 85+"
    }
  ]
}
```

**Scenario:** Professional certification - core lessons + final exam 85+.

---

## 🔧 How to Set

### **When Creating Module:**

```bash
POST /api/v1/modules
{
  "title": "Advanced Mathematics",
  "description": "...",
  "subject_id": "...",
  "grade_level": 10,
  "completion_criteria": {
    "type": "all_required",
    "required_percentage": 100,
    "minimum_score": 75
  }
}
```

### **When Updating Module:**

```bash
PUT /api/v1/modules/{module_id}
{
  "completion_criteria": {
    "type": "percentage",
    "required_percentage": 80,
    "minimum_score": 70
  }
}
```

---

## ⚠️ Important Notes

### **1. Default Value**
If not specified, uses default:
```json
{
  "type": "all_required",
  "required_percentage": 100,
  "minimum_score": 0
}
```

### **2. Impact on Student Progress**
Completion criteria affects:
- ✅ Student progress calculation
- ✅ Certificate issuance
- ✅ Next module unlock (if sequential)
- ✅ Course completion status

### **3. Cannot Change After Students Enrolled**
⚠️ Best practice: Set completion criteria **before** students enroll to avoid confusion.

If must change:
- Inform students
- Consider grandfather clause
- Update documentation

---

## 🎓 Best Practices

### **1. Match Criteria to Content Type**

| Content Type | Recommended Type | Reasoning |
|--------------|------------------|-----------|
| Introduction | `all_required` + score 0 | Just complete, no grading |
| Academic | `all_required` + score 70-80 | Must master all, graded |
| Enrichment | `percentage` + 70-80% | Flexible, self-paced |
| Certification | `custom` with exam | Specific requirements |

### **2. Set Reasonable Minimums**

**❌ Too Strict:**
```json
{
  "type": "all_required",
  "minimum_score": 95  // Too difficult!
}
```
**Result:** High dropout rate

**✅ Reasonable:**
```json
{
  "type": "all_required",
  "minimum_score": 70  // Passing grade
}
```
**Result:** Achievable but meaningful

### **3. Consider Student Diversity**

For mixed-ability classes:
```json
{
  "type": "percentage",
  "required_percentage": 80,
  "minimum_score": 60
}
```
**Benefit:** Allows flexibility while ensuring core learning

---

## 📊 Monitoring Completion

### **Check Student Progress:**

```bash
GET /api/v1/modules/{module_id}/progress?student_id={student_id}
```

**Example Response:**
```json
{
  "student_id": "...",
  "module_id": "...",
  "completion_status": "in_progress",
  "completion_percentage": 75,
  "lessons_completed": 6,
  "lessons_total": 8,
  "average_score": 82,
  "meets_criteria": false,  // Not yet 80%
  "completion_criteria": {
    "type": "percentage",
    "required_percentage": 80,
    "minimum_score": 70
  }
}
```

---

## 🔗 Related Concepts

### **Lesson Required Flag:**
```json
{
  "lesson_refs": [
    {
      "lesson_id": "...",
      "required": true  // ← Must complete for "all_required" type
    },
    {
      "lesson_id": "...",
      "required": false  // ← Optional, not counted
    }
  ]
}
```

### **Assessment Weights:**
```json
{
  "assessments": [
    {
      "assessment_id": "quiz1",
      "weight": 0.3  // 30% of total
    },
    {
      "assessment_id": "final",
      "weight": 0.7  // 70% of total
    }
  ]
}
```

---

## ❓ FAQ

### **Q: Can I change completion_criteria after module is created?**
**A:** Yes, via `PUT /modules/{id}`, but be careful if students already enrolled.

### **Q: What happens if a student doesn't meet criteria?**
**A:** They cannot:
- Get completion certificate
- Unlock next sequential module
- Mark course as completed

### **Q: Can custom_rules be validated?**
**A:** Custom rules are stored as-is. Validation happens when checking student progress.

### **Q: What's the difference between required_percentage and minimum_score?**
**A:**
- `required_percentage`: How many lessons (80% of 10 = 8 lessons)
- `minimum_score`: Score threshold per lesson (score ≥ 70)

---

## ✅ Summary

**Completion Criteria Controls:**
- ✅ Module completion requirements
- ✅ Student progress tracking
- ✅ Certificate eligibility
- ✅ Course flow logic

**Choose Type Based On:**
- Course complexity
- Grading requirements
- Student flexibility needs
- Certification standards

**Default if Not Set:**
```json
{
  "type": "all_required",
  "required_percentage": 100,
  "minimum_score": 0
}
```

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Status:** COMPLETE
