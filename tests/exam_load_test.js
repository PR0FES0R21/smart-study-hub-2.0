import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

// Configuration
const BASE_URL = 'http://localhost:8000';
const EXAM_ID = '68b5406b3c28dc76c69d0f45';
const CLASS_ID = '687e01044593234141867820';

// Admin credentials
const ADMIN_USERNAME = '79111953';
const ADMIN_PASSWORD = '@Admin123';

// Shared array to store student data
const students = new SharedArray('students', function () {
  // This will be populated by the setup function
  return [];
});

export let options = {
  stages: [
    { duration: '30s', target: 1 }, // Setup phase: get students data
    { duration: '2m', target: 60 }, // Ramp up to 60 virtual users
    { duration: '5m', target: 60 }, // Stay at 60 users
    { duration: '30s', target: 0 }, // Ramp down
  ],
};

// Setup function to get student data
export function setup() {
  console.log('Setting up: Getting student data...');
  
  // Admin login
  const adminLoginPayload = {
    grant_type: 'password',
    username: ADMIN_USERNAME,
    password: ADMIN_PASSWORD,
    scope: '',
    client_id: 'string',
    client_secret: '********'
  };

  const adminLoginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    adminLoginPayload,
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'accept': 'application/json'
      }
    }
  );

  check(adminLoginRes, {
    'Admin login successful': (r) => r.status === 200,
  });

  if (adminLoginRes.status !== 200) {
    console.error('Admin login failed:', adminLoginRes.body);
    return { students: [] };
  }

  const adminToken = JSON.parse(adminLoginRes.body).access_token;

  // Get students data
  const studentsRes = http.get(
    `${BASE_URL}/api/v1/users/?role=student&class_id=${CLASS_ID}&page=1&limit=60`,
    {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      }
    }
  );

  check(studentsRes, {
    'Students data retrieved': (r) => r.status === 200,
  });

  if (studentsRes.status !== 200) {
    console.error('Failed to get students data:', studentsRes.body);
    return { students: [] };
  }

  const studentsData = JSON.parse(studentsRes.body);
  console.log(`Found ${studentsData.data.length} students`);

  return { students: studentsData.data };
}

// Helper function to generate random answers
function generateRandomAnswers(questionMap) {
  const answers = {};
  const interactionLogs = [];
  const baseTimestamp = Date.now();

  questionMap.forEach((question, index) => {
    // Random answer selection
    const randomOptionIndex = Math.floor(Math.random() * question.shuffled_option_ids.length);
    const selectedAnswer = question.shuffled_option_ids[randomOptionIndex];
    
    answers[question.question_id] = selectedAnswer;

    // Generate interaction log for this answer
    const timestamp = new Date(baseTimestamp + (index + 1) * (Math.random() * 30000 + 10000)); // Random time between 10-40 seconds apart
    interactionLogs.push({
      timestamp: timestamp.toISOString(),
      question_id: question.question_id,
      displayed_position: index + 1,
      action: 'answer_submitted',
      student_answer: selectedAnswer
    });
  });

  return { answers, interactionLogs };
}

// Helper function to generate violation logs (template-based)
function generateViolationLogs(examId, studentId) {
  const baseTimestamp = Date.now();
  const violations = [];
  
  // Generate 2-5 random violations
  const violationCount = Math.floor(Math.random() * 4) + 2;
  
  for (let i = 0; i < violationCount; i++) {
    const timestamp = new Date(baseTimestamp - Math.random() * 300000); // Random time in last 5 minutes
    const violationTypes = ['page_hidden', 'page_visible', 'fullscreen_exit'];
    const severities = ['medium', 'high'];
    
    violations.push({
      violation_id: `${examId}_${studentId}_${timestamp.getTime()}_${Math.random().toString(36).substr(2, 9)}`,
      type: violationTypes[Math.floor(Math.random() * violationTypes.length)],
      timestamp: timestamp.toISOString(),
      context: {
        user_agent: 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        page_url: `http://192.168.64.9:5173/exam-taking/${studentId}?s=MTc1NjY4MzcyMDAwMA&e=MTc1OTI3NTkwMDAwMA&d=MzYwMDAwMA&examId=${examId}`,
        tab_active: true,
        device_type: 'mobile',
        screen_info: {
          original_height: 831,
          current_height: Math.floor(Math.random() * 100) + 775,
          reduction_percentage: 0
        },
        mouse_position: {
          x: Math.floor(Math.random() * 400) + 200,
          y: Math.floor(Math.random() * 400) + 300,
          clicks: Math.floor(Math.random() * 20) + 1
        },
        keyboard_stats: {
          keystrokes: Math.floor(Math.random() * 10),
          suspicious_keys: 0
        }
      },
      auto_detected: true,
      severity: severities[Math.floor(Math.random() * severities.length)],
      details: `{"full_name":"Student Test","timestamp":${timestamp.getTime()},"visibilityState":"hidden"}`
    });
  }

  return violations;
}

// Main test function
export default function (data) {
  if (!data || !data.students || data.students.length === 0) {
    console.log('No student data available, skipping test');
    return;
  }

  // Each VU gets a unique student (no repeats)
  const studentIndex = (__ITER % data.students.length);
  const student = data.students[studentIndex];
  
  if (!student) {
    console.log(`No student data for iteration ${__ITER}`);
    return;
  }

  console.log(`VU ${__VU} (Iteration ${__ITER}): Testing with student ${student.login_id}`);

  // Student login
  const studentLoginPayload = {
    grant_type: 'password',
    username: student.login_id,
    password: student.login_id, // Password same as login_id
    scope: '',
    client_id: 'string',
    client_secret: '********'
  };

  const studentLoginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    studentLoginPayload,
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'accept': 'application/json'
      }
    }
  );

  check(studentLoginRes, {
    'Student login successful': (r) => r.status === 200,
  });

  if (studentLoginRes.status !== 200) {
    console.error(`Student ${student.login_id} login failed:`, studentLoginRes.body);
    return;
  }

  const studentToken = JSON.parse(studentLoginRes.body).access_token;

  // Start exam
  const startExamRes = http.post(
    `${BASE_URL}/api/v1/exams/${EXAM_ID}/start`,
    '',
    {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${studentToken}`
      }
    }
  );

  check(startExamRes, {
    'Exam started successfully': (r) => r.status === 200,
  });

  if (startExamRes.status !== 200) {
    console.error(`Failed to start exam for student ${student.login_id}:`, startExamRes.body);
    return; // Stop here if exam already taken
  }

  const examSession = JSON.parse(startExamRes.body);
  const examSessionId = examSession._id;
  const questionMap = examSession.question_map;

  console.log(`Student ${student.login_id} started exam session: ${examSessionId}`);

  // Wait a bit to simulate thinking time
  sleep(Math.random() * 5 + 2); // 2-7 seconds

  // Generate random answers and interaction logs
  const { answers, interactionLogs } = generateRandomAnswers(questionMap);
  const violations = generateViolationLogs(EXAM_ID, student._id);

  // Prepare submit payload
  const submitPayload = {
    answers: answers,
    interaction_logs: interactionLogs,
    violations: violations,
    client_metadata: {
      device_fingerprint: '',
      submission_type: 'manual',
      timing: {
        start_time: Date.now() - 180000, // 3 minutes ago
        end_time: Date.now(),
        duration_ms: 180000
      },
      environment: {
        user_agent: 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        timezone: 'Asia/Jakarta',
        screen_resolution: {
          width: 412,
          height: 915
        }
      },
      security_summary: {
        total_violations: violations.length,
        violations_by_severity: {
          low: 0,
          medium: violations.filter(v => v.severity === 'medium').length,
          high: violations.filter(v => v.severity === 'high').length,
          critical: 0
        },
        tab_switches: Math.floor(Math.random() * 3),
        time_spent_inactive: Math.floor(Math.random() * 10000),
        suspicious_activity: false
      }
    }
  };

  // Submit answers
  const submitRes = http.post(
    `${BASE_URL}/api/v1/exam-sessions/${examSessionId}/submit-all`,
    JSON.stringify(submitPayload),
    {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${studentToken}`,
        'Content-Type': 'application/json'
      }
    }
  );

  check(submitRes, {
    'Answers submitted successfully': (r) => r.status === 200,
  });

  if (submitRes.status === 200) {
    console.log(`Student ${student.login_id} submitted answers successfully`);
  } else {
    console.error(`Failed to submit answers for student ${student.login_id}:`, submitRes.status, submitRes.body);
  }

  // Test completed for this student - VU will finish
}

// Teardown function
export function teardown(data) {
  console.log('Test completed');
}