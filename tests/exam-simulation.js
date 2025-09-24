import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomItem, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

export let options = {
  vus: 1, // Sequential processing - 1 user at a time
  iterations: 10, // Process 10 students total (adjust as needed)
};

const BASE_URL = 'https://testing.cigarverse.space';
const ADMIN_CREDENTIALS = 'grant_type=password&username=79111953&password=%40Admin123&scope=&client_id=string&client_secret=********';
const ACADEMIC_PERIOD_ID = '6878bebc5084cc17176782a5';

// Shared data untuk semua iterations
let allStudents = [];
let currentStudentIndex = 0;

export function setup() {
  console.log('🔧 === SETUP PHASE: Getting all students ===');
  
  // Admin login
  let adminLoginResponse = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    ADMIN_CREDENTIALS,
    {
      headers: {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    }
  );

  if (adminLoginResponse.status !== 200) {
    console.error('❌ Admin login failed');
    return { students: [] };
  }

  let adminToken = JSON.parse(adminLoginResponse.body).access_token;
  console.log('✅ Admin login successful');

  // Get all students
  let studentsResponse = http.get(
    `${BASE_URL}/api/v1/users/?role=student&page=1&limit=1000`,
    {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${adminToken}`,
      },
    }
  );

  if (studentsResponse.status !== 200) {
    console.error('❌ Failed to get students');
    return { students: [] };
  }

  let students = JSON.parse(studentsResponse.body).data;
  console.log(`✅ Found ${students.length} students`);
  
  return { students: students };
}

export default function (data) {
  if (!data.students || data.students.length === 0) {
    console.error('❌ No students available');
    return;
  }

  // Get current student (sequential)
  let studentIndex = (__ITER % data.students.length);
  let student = data.students[studentIndex];
  
  console.log('');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log(`🎯 ITERATION ${__ITER + 1}: Processing Student ${studentIndex + 1}/${data.students.length}`);
  console.log(`👤 Student: ${student.profile_details.full_name}`);
  console.log(`🆔 Login ID: ${student.login_id}`);
  console.log('═══════════════════════════════════════════════════════════════');

  // 1. STUDENT LOGIN
  console.log('🔐 Step 1: Student login...');
  let studentCreds = `grant_type=password&username=${student.login_id}&password=${student.login_id}&scope=&client_id=string&client_secret=********`;
  
  let studentLoginResponse = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    studentCreds,
    {
      headers: {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    }
  );

  if (studentLoginResponse.status !== 200) {
    console.error(`❌ Student login failed: ${studentLoginResponse.status}`);
    console.error(`   Response: ${studentLoginResponse.body}`);
    return;
  }

  let studentToken = JSON.parse(studentLoginResponse.body).access_token;
  console.log('✅ Student login successful');

  // 2. GET AVAILABLE EXAMS
  console.log('📋 Step 2: Getting available exams...');
  let examsResponse = http.get(
    `${BASE_URL}/api/v1/exams/student?academic_period_id=${ACADEMIC_PERIOD_ID}&status=ongoing&page=1&limit=20`,
    {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${studentToken}`,
      },
    }
  );

  if (examsResponse.status !== 200) {
    console.error(`❌ Failed to get exams: ${examsResponse.status}`);
    console.error(`   Response: ${examsResponse.body}`);
    return;
  }

  let availableExams = JSON.parse(examsResponse.body).data;
  console.log(`✅ Found ${availableExams.length} available exams`);
  
  if (availableExams.length === 0) {
    console.log('⚠️ No exams available for this student');
    return;
  }

  // Show available exams
  availableExams.forEach((exam, index) => {
    console.log(`   ${index + 1}. ${exam.title} (ID: ${exam._id})`);
  });

  // Pick first exam untuk consistency
  let selectedExam = availableExams[0];
  console.log(`🎯 Selected exam: "${selectedExam.title}"`);

  // 3. START EXAM SESSION
  console.log('🚀 Step 3: Starting exam session...');
  let startExamResponse = http.post(
    `${BASE_URL}/api/v1/exams/${selectedExam._id}/start`,
    null,
    {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${studentToken}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (startExamResponse.status !== 200 && startExamResponse.status !== 201) {
    console.error(`❌ Failed to start exam: ${startExamResponse.status}`);
    console.error(`   Response: ${startExamResponse.body}`);
    return;
  }

  let examSession = JSON.parse(startExamResponse.body);
  let examSessionId = examSession._id;
  let questionMap = examSession.question_map;

  console.log(`✅ Exam session started`);
  console.log(`🆔 Session ID: ${examSessionId}`);
  console.log(`📊 Total questions: ${questionMap.length}`);

  // 4. DETAILED QUESTION ANALYSIS & ANSWER GENERATION
  console.log('📝 Step 4: Analyzing and answering questions...');
  console.log('─'.repeat(50));
  
  let answers = {};
  let interactionLogs = [];
  let currentTime = Date.now();
  
  questionMap.forEach((question, index) => {
    let questionNum = question.position;
    let questionId = question.question_id;
    let options = question.shuffled_option_ids;
    
    console.log(`📝 Question ${questionNum}:`);
    console.log(`   🆔 ID: ${questionId}`);
    
    let selectedAnswer;
    
    if (!options || options.length === 0) {
      // Essay/text question
      selectedAnswer = "testing";
      console.log(`   📋 Type: TEXT/ESSAY`);
      console.log(`   ✏️ Answer: "${selectedAnswer}"`);
    } else {
      // Multiple choice question
      selectedAnswer = randomItem(options);
      console.log(`   📋 Type: MULTIPLE CHOICE`);
      console.log(`   🔢 Available options: ${options.length}`);
      options.forEach((opt, optIndex) => {
        let marker = (opt === selectedAnswer) ? '✅' : '  ';
        console.log(`      ${marker} ${optIndex + 1}. ${opt}`);
      });
      console.log(`   🎯 Selected: ${selectedAnswer}`);
    }
    
    // Store answer
    answers[questionId] = selectedAnswer;
    
    // Generate interaction log
    let answerTime = currentTime + (index * randomIntBetween(3000, 8000));
    interactionLogs.push({
      timestamp: new Date(answerTime).toISOString(),
      question_id: questionId,
      displayed_position: questionNum,
      action: "answer_submitted",
      student_answer: selectedAnswer
    });
    
    console.log(`   ⏰ Answer time: ${new Date(answerTime).toISOString()}`);
    console.log('');
    
    // Simulate thinking time
    sleep(randomIntBetween(1, 3));
  });

  console.log('─'.repeat(50));
  console.log(`📊 ANSWERS SUMMARY:`);
  console.log(`   📝 Total questions: ${questionMap.length}`);
  console.log(`   ✅ Total answered: ${Object.keys(answers).length}`);
  console.log(`   📋 Interaction logs: ${interactionLogs.length}`);

  // Verify all questions are answered
  if (Object.keys(answers).length !== questionMap.length) {
    console.error(`❌ INCOMPLETE: Only answered ${Object.keys(answers).length}/${questionMap.length} questions`);
    return;
  }

  // 5. PREPARE SUBMISSION PAYLOAD
  console.log('📦 Step 5: Preparing submission payload...');
  
  let endTime = Date.now();
  let payload = {
    answers: answers,
    interaction_logs: interactionLogs,
    violations: [],
    client_metadata: {
      device_fingerprint: "",
      submission_type: "manual",
      timing: {
        start_time: currentTime,
        end_time: endTime,
        duration_ms: endTime - currentTime
      },
      environment: {
        user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        timezone: "Asia/Jakarta",
        screen_resolution: {
          width: 1280,
          height: 800
        }
      },
      security_summary: {
        total_violations: 0,
        violations_by_severity: {
          low: 0,
          medium: 0,
          high: 0,
          critical: 0
        },
        tab_switches: 0,
        time_spent_inactive: 0,
        suspicious_activity: false
      }
    }
  };

  console.log(`✅ Payload prepared - Duration: ${(endTime - currentTime) / 1000}s`);

  // 6. SUBMIT ANSWERS
  console.log('📤 Step 6: Submitting answers...');
  
  let jsonPayload = JSON.stringify(payload);
  
  let submitResponse = http.post(
    `${BASE_URL}/api/v1/exam-sessions/${examSessionId}/submit-all`,
    jsonPayload,
    {
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${studentToken}`,
        'Content-Type': 'application/json; charset=utf-8',
      }
    }
  );

  console.log(`📊 Submit response: ${submitResponse.status}`);
  
  if (submitResponse.status === 200) {
    console.log('🎉 SUCCESS! Answers submitted successfully');
    console.log(`✅ Student "${student.profile_details.full_name}" completed exam "${selectedExam.title}"`);
  } else {
    console.error('❌ SUBMISSION FAILED!');
    console.error(`   Status: ${submitResponse.status}`);
    console.error(`   Response: ${submitResponse.body}`);
  }

  // Brief pause before next student
  sleep(2);
}

export function teardown(data) {
  console.log('');
  console.log('🏁 === TEARDOWN: All students processed ===');
  console.log(`📈 Total students available: ${data.students.length}`);
  console.log('✅ Load test completed');
}
