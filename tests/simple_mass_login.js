import http from 'k6/http';
import { check, sleep } from 'k6';

// Configuration
const BASE_URL = 'http://localhost:8080/api/v1';
const TOTAL_USERS = 941; // Jumlah user yang berhasil dibuat dari setup sebelumnya

// Generate user list berdasarkan user yang udah dibuat
const users = [];
for (let i = 1; i <= TOTAL_USERS; i++) {
  const userId = String(i).padStart(7, '0'); // 0000001, 0000002, dst
  users.push({
    login_id: userId,
    password: userId, // Password sama dengan login_id
  });
}

export let options = {
  scenarios: {
    // Phase 1: Mass Login untuk dapet semua token
    mass_login: {
      executor: 'shared-iterations',
      vus: TOTAL_USERS, // 941 VUs bersamaan
      iterations: TOTAL_USERS, // 941 iterations
      maxDuration: '3m', // Kasih waktu 3 menit untuk login semua
      tags: { phase: 'login' },
      exec: 'loginPhase',
    },
    
    // Phase 2: Test endpoint dengan token yang udah didapat
    endpoint_test: {
      executor: 'shared-iterations', 
      vus: TOTAL_USERS, // 941 VUs bersamaan
      iterations: TOTAL_USERS, // 941 iterations
      maxDuration: '2m',
      startTime: '4m', // Mulai 1 menit setelah login phase selesai
      tags: { phase: 'endpoint_test' },
      exec: 'endpointTestPhase',
    },
  },
  thresholds: {
    'http_req_duration{phase:login}': ['p(95)<10000'], // Login harus < 10s
    'http_req_duration{phase:endpoint_test}': ['p(95)<5000'], // API call harus < 5s
    'http_req_failed{phase:login}': ['rate<0.05'], // Max 5% login failure
    'http_req_failed{phase:endpoint_test}': ['rate<0.02'], // Max 2% API failure
  },
};

// Global storage untuk tokens (hack tapi works di k6)
let userTokens = [];

// Phase 1: Mass Login
export function loginPhase() {
  const vuIndex = __VU - 1; // VU mulai dari 1, array mulai dari 0
  const currentUser = users[vuIndex];
  
  if (!currentUser) {
    console.log(`VU ${__VU}: No user assigned for login, skipping...`);
    return;
  }

  console.log(`🔐 VU ${__VU}: Login ${currentUser.login_id}`);
  
  // Login request
  let loginPayload = {
    grant_type: 'password',
    username: currentUser.login_id,
    password: currentUser.password,
    scope: '',
    client_id: 'string',
    client_secret: '********',
  };

  let formBody = Object.entries(loginPayload)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');

  let loginRes = http.post(`${BASE_URL}/auth/login`, formBody, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json',
    },
  });

  let loginSuccess = check(loginRes, {
    'login berhasil': (res) => res.status === 200,
    'dapat access token': (res) => res.json('access_token') !== undefined,
    'login response time OK': (res) => res.timings.duration < 10000,
  });

  if (loginSuccess) {
    let token = loginRes.json('access_token');
    userTokens[vuIndex] = token; // Simpan token untuk phase berikutnya
    console.log(`✅ ${currentUser.login_id}: Login SUCCESS! Token saved.`);
  } else {
    console.log(`❌ ${currentUser.login_id}: Login FAILED - Status: ${loginRes.status}`);
    if (loginRes.body && loginRes.body.length < 500) {
      console.log(`📝 ${currentUser.login_id}: Error: ${loginRes.body}`);
    }
  }
}

// Phase 2: Test Endpoint dengan Token
export function endpointTestPhase() {
  const vuIndex = __VU - 1;
  const currentUser = users[vuIndex];
  const token = userTokens[vuIndex];
  
  if (!currentUser) {
    console.log(`VU ${__VU}: No user assigned for endpoint test, skipping...`);
    return;
  }
  
  if (!token) {
    console.log(`VU ${__VU}: No token available for ${currentUser.login_id}, skipping...`);
    return;
  }

  console.log(`🎯 VU ${__VU}: Testing endpoint for ${currentUser.login_id}`);
  
  // GET request ke endpoint target
  let apiRes = http.get(`${BASE_URL}/users/?role=student`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/json',
    },
  });

  let apiSuccess = check(apiRes, {
    'endpoint berhasil diakses': (res) => res.status === 200,
    'response time OK': (res) => res.timings.duration < 5000,
    'response valid JSON': (res) => {
      try {
        const body = res.json();
        return body !== null && body !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (apiSuccess) {
    console.log(`✅ ${currentUser.login_id}: Endpoint test SUCCESS!`);
    
    // Log info tentang response data
    try {
      const responseData = apiRes.json();
      let studentCount = 0;
      
      if (Array.isArray(responseData)) {
        studentCount = responseData.length;
      } else if (responseData.data && Array.isArray(responseData.data)) {
        studentCount = responseData.data.length;
      } else if (responseData.total !== undefined) {
        studentCount = responseData.total;
      } else if (responseData.count !== undefined) {
        studentCount = responseData.count;
      }
      
      console.log(`📊 ${currentUser.login_id}: Found ${studentCount} students`);
    } catch (e) {
      console.log(`📊 ${currentUser.login_id}: Response OK but couldn't parse student count`);
    }
  } else {
    console.log(`❌ ${currentUser.login_id}: Endpoint test FAILED - Status: ${apiRes.status}`);
    if (apiRes.body && apiRes.body.length < 500) {
      console.log(`📝 ${currentUser.login_id}: Error: ${apiRes.body}`);
    }
  }
}

// Default function (tidak dipakai tapi required oleh k6)
export default function () {
  // Kosong karena kita pakai exec functions
}

// Summary handler untuk report
export function handleSummary(data) {
  // Login phase metrics
  const loginMetrics = data.metrics;
  const loginSuccessRate = loginMetrics.http_req_failed ? 
    (1 - loginMetrics.http_req_failed.values.rate) * 100 : 0;
  
  console.log('\n🎯 === MASS LOGIN & ENDPOINT TEST SUMMARY ===');
  console.log(`📊 Total Users Tested: ${TOTAL_USERS}`);
  console.log(`✅ Overall Success Rate: ${loginSuccessRate.toFixed(2)}%`);
  console.log(`⏱️  Average Response Time: ${loginMetrics.http_req_duration?.values.avg.toFixed(2)}ms`);
  console.log(`🔥 95th Percentile: ${loginMetrics.http_req_duration?.values['p(95)'].toFixed(2)}ms`);
  console.log(`🌐 Total Requests: ${loginMetrics.http_reqs?.values.count}`);
  
  return {
    'test-summary.json': JSON.stringify(data, null, 2),
  };
}