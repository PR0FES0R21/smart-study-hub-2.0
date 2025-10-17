# Embedded Components - Complete Guide

**Panduan Lengkap Penggunaan Komponen Interaktif di Lesson Pages**

---

## 📋 Apa Itu Embedded Components?

**Embedded components** adalah komponen **interaktif** yang bisa disisipkan di dalam lesson page untuk membuat pembelajaran lebih engaging dan interactive.

**Contoh:** Quiz, Assignment, Simulasi, Discussion Forum, dll.

---

## 🎯 6 Type Komponen yang Tersedia

| Type | Icon | Kegunaan | Student Action | Graded? |
|------|------|----------|----------------|---------|
| **quiz** | 🎯 | Multiple choice test | Answer questions | ✅ Yes |
| **assignment** | 📝 | Essay/project submission | Upload/write answer | ✅ Yes |
| **interactive** | 🎮 | Simulation/playground | Interact with tool | ❌ Optional |
| **survey** | 📊 | Feedback/polling | Select options | ❌ No |
| **reflection** | 💭 | Personal journal | Write reflection | ❌ Optional |
| **discussion** | 💬 | Forum discussion | Post & reply | ❌ Optional |

---

## 1. Quiz 🎯

### **Kegunaan:**
Kuis untuk test pemahaman student terhadap materi (multiple choice, true/false, etc)

### **When to Use:**
- Setelah menjelaskan konsep untuk test pemahaman
- Quick check untuk self-assessment
- Formative assessment

### **Payload Structure:**

```json
{
  "component_id": "quiz_matriks_001",
  "type": "quiz",
  "position": 1,
  "title": "Quiz: Operasi Matriks Dasar",
  "required": true,
  "estimated_duration": 10,
  "data": {
    "quiz_id": "68f123abc456def789012345",
    "passing_score": 70,
    "max_attempts": 3,
    "show_results": true,
    "shuffle_questions": true,
    "shuffle_options": true
  }
}
```

### **Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `quiz_id` | string | ✅ Yes | ID quiz yang sudah dibuat di database |
| `passing_score` | integer | ✅ Yes | Nilai minimal untuk lulus (0-100) |
| `max_attempts` | integer | ❌ No | Maksimal berapa kali bisa retry (default: unlimited) |
| `show_results` | boolean | ❌ No | Tampilkan hasil setelah submit (default: true) |
| `shuffle_questions` | boolean | ❌ No | Acak urutan soal (default: false) |
| `shuffle_options` | boolean | ❌ No | Acak urutan opsi jawaban (default: false) |

### **Workflow:**

```bash
# 1. Create quiz first
POST /api/v1/quizzes
{
  "title": "Quiz Matriks Dasar",
  "questions": [
    {
      "question": "Apa itu matriks?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A"
    }
  ]
}
# Response: { "id": "68f123abc..." }

# 2. Embed di lesson page
POST /api/v1/lessons/{lesson_id}/pages
{
  "embedded_components": [
    {
      "type": "quiz",
      "data": {
        "quiz_id": "68f123abc..."  # ← ID dari step 1
      }
    }
  ]
}
```

### **Use Case Examples:**
- Post-lecture knowledge check
- Pre-test untuk check prior knowledge
- Practice quiz dengan instant feedback
- Final assessment untuk lesson

---

## 2. Assignment 📝

### **Kegunaan:**
Tugas yang membutuhkan jawaban panjang, essay, atau upload file (project, report, dll)

### **When to Use:**
- Tugas yang butuh analisis mendalam
- Project submission
- Essay writing
- Case study analysis
- File upload (PDF, Word, Excel, etc)

### **Payload Structure:**

```json
{
  "component_id": "assignment_matriks_001",
  "type": "assignment",
  "position": 1,
  "title": "Tugas: Aplikasi Matriks dalam Kehidupan Nyata",
  "required": true,
  "estimated_duration": 120,
  "data": {
    "assignment_id": "68f456def789abc123456789",
    "due_date": "2025-01-30T23:59:59Z",
    "max_score": 100,
    "allow_late_submission": false,
    "late_penalty_percent": 10,
    "submission_type": "file",
    "allowed_file_types": ["pdf", "docx", "pptx"],
    "max_file_size_mb": 10,
    "instructions": "Upload analisis penggunaan matriks di bidang..."
  }
}
```

### **Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assignment_id` | string | ✅ Yes | ID assignment yang sudah dibuat |
| `due_date` | string | ✅ Yes | Deadline (ISO 8601 format) |
| `max_score` | integer | ✅ Yes | Nilai maksimal (default: 100) |
| `allow_late_submission` | boolean | ❌ No | Boleh submit setelah deadline? (default: false) |
| `late_penalty_percent` | integer | ❌ No | Penalty per hari jika late (default: 0) |
| `submission_type` | string | ✅ Yes | `file` \| `text` \| `link` |
| `allowed_file_types` | array | ❌ No | File extensions allowed (jika type=file) |
| `max_file_size_mb` | integer | ❌ No | Max file size (default: 10MB) |
| `instructions` | string | ❌ No | Additional instructions |

### **Submission Types:**

**Type: `file`**
```json
"data": {
  "submission_type": "file",
  "allowed_file_types": ["pdf", "docx"],
  "max_file_size_mb": 10
}
```
Student upload file (PDF, Word, etc)

**Type: `text`**
```json
"data": {
  "submission_type": "text",
  "min_words": 500,
  "max_words": 1500
}
```
Student write essay di text editor

**Type: `link`**
```json
"data": {
  "submission_type": "link",
  "allowed_domains": ["github.com", "docs.google.com"]
}
```
Student submit link (GitHub repo, Google Docs, etc)

### **Use Case Examples:**
- Essay writing assignments
- Project submission (PDF report)
- Coding project (GitHub link)
- Presentation slides (PPTX)
- Case study analysis

---

## 3. Interactive 🎮

### **Kegunaan:**
Simulasi, playground, atau tools interaktif untuk hands-on practice

### **When to Use:**
- Mathematical simulations
- Coding playground
- Virtual lab
- Drag & drop exercises
- Calculator/converter tools

### **Payload Structure:**

```json
{
  "component_id": "interactive_matriks_001",
  "type": "interactive",
  "position": 1,
  "title": "Simulasi: Operasi Matriks",
  "required": false,
  "estimated_duration": 20,
  "data": {
    "interactive_id": "68f789ghi123def456789012",
    "interactive_type": "simulation",
    "config": {
      "matrix_size": [3, 3],
      "operations": ["add", "multiply", "transpose", "inverse"],
      "show_steps": true,
      "allow_custom_input": true
    }
  }
}
```

### **Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `interactive_id` | string | ✅ Yes | ID interactive component |
| `interactive_type` | string | ✅ Yes | `simulation` \| `playground` \| `calculator` \| `game` |
| `config` | object | ✅ Yes | Configuration spesifik untuk type |

### **Interactive Types:**

**Simulation:**
```json
"data": {
  "interactive_type": "simulation",
  "config": {
    "simulation_name": "matrix_operations",
    "parameters": {...},
    "visualization": "2d" | "3d"
  }
}
```

**Playground (Coding):**
```json
"data": {
  "interactive_type": "playground",
  "config": {
    "language": "python",
    "starter_code": "# Write your code here\n",
    "test_cases": [...],
    "allow_import": false
  }
}
```

**Calculator:**
```json
"data": {
  "interactive_type": "calculator",
  "config": {
    "calculator_type": "matrix",
    "features": ["add", "multiply", "determinant"]
  }
}
```

### **Use Case Examples:**
- Math simulator (matrix operations, calculus, geometry)
- Physics virtual lab
- Chemistry molecule builder
- Coding exercises dengan auto-check
- Interactive graphs/charts

---

## 4. Survey 📊

### **Kegunaan:**
Survey atau polling untuk collect feedback dari students

### **When to Use:**
- Feedback tentang materi
- Quick poll
- Self-assessment rating
- Course satisfaction survey

### **Payload Structure:**

```json
{
  "component_id": "survey_feedback_001",
  "type": "survey",
  "position": 1,
  "title": "Seberapa Paham Anda dengan Materi Ini?",
  "required": false,
  "estimated_duration": 5,
  "data": {
    "survey_id": "68fabc123def456ghi789012",
    "survey_type": "rating",
    "anonymous": true,
    "show_results": false,
    "questions": [
      {
        "question": "Bagaimana penilaian Anda tentang materi ini?",
        "type": "scale",
        "scale": [1, 2, 3, 4, 5],
        "labels": ["Sangat Sulit", "Sulit", "Sedang", "Mudah", "Sangat Mudah"]
      }
    ]
  }
}
```

### **Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `survey_id` | string | ✅ Yes | ID survey yang sudah dibuat |
| `survey_type` | string | ✅ Yes | `rating` \| `multiple_choice` \| `open_ended` |
| `anonymous` | boolean | ❌ No | Anonim atau tampilkan nama (default: true) |
| `show_results` | boolean | ❌ No | Tampilkan hasil ke student (default: false) |
| `questions` | array | ✅ Yes | Array of survey questions |

### **Use Case Examples:**
- Lesson difficulty rating (1-5 scale)
- Topic interest polling
- Teaching effectiveness feedback
- Self-confidence assessment
- Course evaluation

---

## 5. Reflection 💭

### **Kegunaan:**
Jurnal refleksi pribadi untuk metacognitive learning

### **When to Use:**
- End of lesson reflection
- Critical thinking prompts
- Self-assessment
- Learning journal

### **Payload Structure:**

```json
{
  "component_id": "reflection_001",
  "type": "reflection",
  "position": 1,
  "title": "Refleksi: Apa yang Sudah Anda Pelajari?",
  "required": false,
  "estimated_duration": 15,
  "data": {
    "reflection_id": "68fdef456ghi789jkl012345",
    "prompts": [
      "Apa konsep paling menarik yang Anda pelajari hari ini?",
      "Apa yang masih membingungkan atau perlu dipelajari lebih lanjut?",
      "Bagaimana Anda akan menerapkan pengetahuan ini?"
    ],
    "min_words": 100,
    "max_words": 500,
    "private": true,
    "allow_edit": true
  }
}
```

### **Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reflection_id` | string | ✅ Yes | ID reflection component |
| `prompts` | array | ✅ Yes | Array of reflection questions/prompts |
| `min_words` | integer | ❌ No | Minimum word count (default: 0) |
| `max_words` | integer | ❌ No | Maximum word count (default: unlimited) |
| `private` | boolean | ❌ No | Only visible to student & teacher (default: true) |
| `allow_edit` | boolean | ❌ No | Can edit after submit? (default: true) |

### **Use Case Examples:**
- Daily learning journal
- What-I-Learned summary
- Confusion points identification
- Connection to prior knowledge
- Application planning

---

## 6. Discussion 💬

### **Kegunaan:**
Forum diskusi untuk peer learning dan collaboration

### **When to Use:**
- Class discussion
- Debate topics
- Peer help forum
- Question & Answer
- Project collaboration

### **Payload Structure:**

```json
{
  "component_id": "discussion_001",
  "type": "discussion",
  "position": 1,
  "title": "Diskusi: Aplikasi Matriks di Dunia Nyata",
  "required": false,
  "estimated_duration": 30,
  "data": {
    "discussion_id": "68fghi789jkl012mno345678",
    "discussion_topic": "Bagaimana matriks digunakan dalam kehidupan sehari-hari?",
    "discussion_type": "open",
    "allow_replies": true,
    "allow_reactions": true,
    "min_posts": 1,
    "min_replies": 2,
    "moderated": false
  }
}
```

### **Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `discussion_id` | string | ✅ Yes | ID discussion thread |
| `discussion_topic` | string | ✅ Yes | Topik diskusi |
| `discussion_type` | string | ✅ Yes | `open` \| `structured` \| `debate` |
| `allow_replies` | boolean | ❌ No | Boleh reply ke post lain? (default: true) |
| `allow_reactions` | boolean | ❌ No | Boleh react (like, helpful, etc)? (default: true) |
| `min_posts` | integer | ❌ No | Minimal berapa post harus dibuat (default: 0) |
| `min_replies` | integer | ❌ No | Minimal berapa reply harus dibuat (default: 0) |
| `moderated` | boolean | ❌ No | Posts need approval? (default: false) |

### **Discussion Types:**

**Open Discussion:**
```json
"data": {
  "discussion_type": "open",
  "discussion_topic": "Share your thoughts..."
}
```
Free-form discussion

**Structured Discussion:**
```json
"data": {
  "discussion_type": "structured",
  "discussion_phases": [
    {"phase": "brainstorm", "duration_minutes": 10},
    {"phase": "discussion", "duration_minutes": 20},
    {"phase": "conclusion", "duration_minutes": 10}
  ]
}
```
Phased discussion dengan time limits

**Debate:**
```json
"data": {
  "discussion_type": "debate",
  "debate_sides": ["Pro", "Kontra"],
  "assign_sides": true
}
```
Formal debate dengan sides

### **Use Case Examples:**
- Real-world application discussion
- Problem-solving collaboration
- Peer help/support
- Critical thinking debates
- Project brainstorming

---

## 📊 Comparison Table

| Feature | Quiz | Assignment | Interactive | Survey | Reflection | Discussion |
|---------|------|------------|-------------|--------|------------|-----------|
| **Graded** | ✅ Yes | ✅ Yes | ⚠️ Optional | ❌ No | ⚠️ Optional | ❌ No |
| **Auto-Score** | ✅ Yes | ❌ No | ⚠️ Depends | N/A | N/A | N/A |
| **File Upload** | ❌ No | ✅ Yes | ❌ No | ❌ No | ❌ No | ⚠️ Optional |
| **Peer Visible** | ❌ No | ❌ No | ⚠️ Optional | ⚠️ Optional | ❌ No | ✅ Yes |
| **Deadline** | ⚠️ Optional | ✅ Yes | ❌ No | ⚠️ Optional | ⚠️ Optional | ❌ No |
| **Retry Allowed** | ✅ Yes | ⚠️ Depends | ✅ Yes | ✅ Yes | ✅ Yes | N/A |
| **Best For** | Knowledge Check | Deep Work | Practice | Feedback | Reflection | Collaboration |

---

## 🎨 Recommended Combinations

### **Basic Content Page:**
```json
{
  "embedded_components": []  // No components - just content
}
```
Use for: Theory/explanation pages

---

### **Practice Page:**
```json
{
  "embedded_components": [
    {
      "type": "interactive",
      "position": 1,
      "title": "Try it yourself"
    },
    {
      "type": "quiz",
      "position": 2,
      "title": "Check your understanding"
    }
  ]
}
```
Use for: Skill practice + assessment

---

### **Assessment Page:**
```json
{
  "embedded_components": [
    {
      "type": "quiz",
      "position": 1,
      "title": "Quick Quiz",
      "required": true
    },
    {
      "type": "assignment",
      "position": 2,
      "title": "Project Submission",
      "required": true
    }
  ]
}
```
Use for: Formative + summative assessment

---

### **Collaborative Learning Page:**
```json
{
  "embedded_components": [
    {
      "type": "discussion",
      "position": 1,
      "title": "Group Discussion"
    },
    {
      "type": "reflection",
      "position": 2,
      "title": "Personal Reflection"
    }
  ]
}
```
Use for: Social learning + metacognition

---

### **Feedback Page:**
```json
{
  "embedded_components": [
    {
      "type": "survey",
      "position": 1,
      "title": "How was this lesson?"
    },
    {
      "type": "reflection",
      "position": 2,
      "title": "What did you learn?"
    }
  ]
}
```
Use for: End of lesson feedback

---

## 🚀 Complete Workflow Example

### **Scenario: Create Lesson with Quiz**

```bash
# Step 1: Create Quiz
POST /api/v1/quizzes
{
  "title": "Quiz Matriks Dasar",
  "description": "Test pemahaman matriks",
  "questions": [
    {
      "question": "Apa itu matriks?",
      "type": "multiple_choice",
      "options": [
        "Susunan bilangan berbentuk persegi",
        "Bilangan tunggal",
        "Grafik koordinat",
        "Persamaan linear"
      ],
      "correct_answer": 0,
      "explanation": "Matriks adalah susunan bilangan..."
    }
  ]
}

# Response:
{
  "id": "68f123abc456def789012345",  # ← Save this!
  "title": "Quiz Matriks Dasar",
  ...
}

# Step 2: Create Lesson
POST /api/v1/lessons
{
  "title": "Pengenalan Matriks",
  "description": "Belajar konsep dasar matriks",
  "subject_id": "...",
  "grade_level": 10
}

# Response:
{
  "id": "68e418dae48c804c5986117d",  # ← Lesson ID
  ...
}

# Step 3: Create Page with Quiz Embedded
POST /api/v1/lessons/68e418dae48c804c5986117d/pages
{
  "page_number": 1,
  "title": "Apa Itu Matriks?",
  "content_markdown": "# Pengertian Matriks\n\nMatriks adalah...\n\n## Kerjakan Quiz\n\nSetelah membaca materi, kerjakan quiz berikut:",
  "embedded_components": [
    {
      "component_id": "quiz_matriks_001",
      "type": "quiz",
      "position": 1,
      "title": "Quiz: Pengertian Matriks",
      "required": true,
      "estimated_duration": 10,
      "data": {
        "quiz_id": "68f123abc456def789012345",  # ← Quiz ID from Step 1
        "passing_score": 70,
        "max_attempts": 3,
        "show_results": true
      }
    }
  ],
  "estimated_duration": 20,
  "difficulty_level": "medium",
  "status": "draft"
}

# Step 4: Publish
PUT /api/v1/lessons/68e418dae48c804c5986117d
{
  "status": "published"
}
```

---

## 💡 Best Practices

### **1. Create Components First**
Always create quiz/assignment/etc BEFORE embedding di page.

### **2. Use Meaningful IDs**
```json
"component_id": "quiz_matriks_001"  // ✅ Descriptive
"component_id": "q1"                // ❌ Not clear
```

### **3. Set Appropriate Position**
```json
// Position determines order
[
  {"position": 1, "title": "Try interactive first"},
  {"position": 2, "title": "Then take quiz"}
]
```

### **4. Use Required Wisely**
```json
"required": true   // ✅ For graded assessments
"required": false  // ✅ For optional practice
```

### **5. Estimate Duration Realistically**
```json
"estimated_duration": 10  // ✅ For quiz with 10 questions
"estimated_duration": 1   // ❌ Too short, unrealistic
```

### **6. Test Components Separately**
Create and test quiz/assignment standalone before embedding.

---

## 🔗 Related Documentation

- **Payload Examples:** `docs/LESSON_PAGES_PAYLOAD_EXAMPLES.md`
- **API Guide:** `docs/FRONTEND_LESSON_API_GUIDE.md`
- **Quiz API:** `docs/QUIZ_API_GUIDE.md` (if exists)
- **Assignment API:** `docs/ASSIGNMENT_API_GUIDE.md` (if exists)

---

## 📞 Need Help?

**Common Questions:**

**Q: Bisa embed quiz yang sama di multiple pages?**  
A: ✅ Yes! Satu quiz bisa dipakai di banyak lesson pages.

**Q: Bisa embed multiple components di satu page?**  
A: ✅ Yes! Pakai array, set position berbeda.

**Q: Bisa change component setelah page published?**  
A: ✅ Yes! Update page dengan PUT, replace embedded_components.

**Q: Component auto-score?**  
A: Quiz = ✅ Auto. Assignment = ❌ Manual grading by teacher.

**Q: Student bisa skip required component?**  
A: ❌ No, must complete before proceeding to next page.

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-16  
**Status:** Complete & Ready to Use
