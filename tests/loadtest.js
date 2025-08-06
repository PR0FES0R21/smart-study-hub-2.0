import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

// Configuration
const BASE_URL = 'http://localhost:8080/api/v1';
const ADMIN_LOGIN_ID = '79111953'; // Admin login_id lo
const ADMIN_PASSWORD = 'sayoga2019'; // Admin password lo
const TOTAL_USERS = 1000;

// Shared array untuk menyimpan user credentials yang akan dibuat
const generatedUsers = new SharedArray('users', function () {
  const users = [];
  for (let i = 1; i <= TOTAL_USERS; i++) {
    const userId = String(i).padStart(7, '0'); // 0000001, 0000002, dst
    users.push({
      login_id: userId, // Unique login_id
      email: `${userId}@loadtest.com`, // Unique email
      username: userId, // Untuk login nanti
      password: userId, // Untuk login nanti (asumsi password = login_id)
    });
  }
  return users;
});

export let options = {
  scenarios: {
    // Phase 1: Setup - Login admin dan buat 1000 users
    setup_phase: {
      executor: 'shared-iterations',
      vus: 1, // Cuma 1 VU untuk setup
      iterations: 1,
      maxDuration: '30m', // Kasih waktu cukup untuk buat 1000 user
      tags: { phase: 'setup' },
      exec: 'setupPhase',
    },
    
    // Phase 2: Mass Login - 1000 user login bersamaan
    mass_login_phase: {
      executor: 'shared-iterations',
      vus: TOTAL_USERS, // 1000 VUs
      iterations: TOTAL_USERS, // 1000 iterations
      maxDuration: '2m',
      startTime: '31m', // Mulai setelah setup selesai
      tags: { phase: 'mass_login' },
      exec: 'massLoginPhase',
    },
    
    // Phase 3: Load Test - Akses endpoint bersamaan
    load_test_phase: {
      executor: 'shared-iterations',
      vus: TOTAL_USERS, // 1000 VUs
      iterations: TOTAL_USERS, // 1000 iterations
      maxDuration: '2m',
      startTime: '34m', // Mulai setelah mass login selesai
      tags: { phase: 'load_test' },
      exec: 'loadTestPhase',
    },
  },
  thresholds: {
    'http_req_duration{phase:setup}': ['p(95)<30000'], // Setup bisa lebih lama
    'http_req_duration{phase:mass_login}': ['p(95)<10000'], // Login harus cepat
    'http_req_duration{phase:load_test}': ['p(95)<5000'], // API call harus responsif
    'http_req_failed{phase:mass_login}': ['rate<0.1'], // Max 10% failure untuk login
    'http_req_failed{phase:load_test}': ['rate<0.05'], // Max 5% failure untuk API call
  },
};

// Global variable untuk menyimpan tokens (ini hack, tapi works untuk k6)
let userTokens = [];

// Phase 1: Setup - Login admin dan buat users
export function setupPhase() {
  console.log('🚀 PHASE 1: Starting setup phase...');
  
  // Step 1: Login sebagai admin
  console.log('👤 Logging in as admin...');
  let adminLoginPayload = {
    grant_type: 'password',
    username: ADMIN_LOGIN_ID,
    password: ADMIN_PASSWORD,
    scope: '',
    client_id: 'string',
    client_secret: '********',
  };

  let formBody = Object.entries(adminLoginPayload)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');

  let adminLoginRes = http.post(`${BASE_URL}/auth/login`, formBody, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json',
    },
  });

  let adminLoginSuccess = check(adminLoginRes, {
    'admin login berhasil': (res) => res.status === 200,
    'admin mendapat token': (res) => res.json('access_token') !== undefined,
  });

  if (!adminLoginSuccess) {
    console.error('❌ Admin login failed! Stopping test...');
    return;
  }

  let adminToken = adminLoginRes.json('access_token');
  console.log('✅ Admin login successful!');

  // Step 2: Buat 1000 users dengan role admin
  console.log(`👥 Creating ${TOTAL_USERS} users with admin role...`);
  let successCount = 0;
  let failCount = 0;

  for (let i = 0; i < TOTAL_USERS; i++) {
    const user = generatedUsers[i];
    
    let createUserPayload = {
      login_id: user.login_id, // 0000001, 0000002, dst (unique)
      email: user.email, // 0000001@loadtest.com, dst (unique)
      roles: ["admin"], // Set role sebagai admin dalam array
      is_active: true,
      profile: {
        full_name: "string",
        gender: "string", 
        birth_date: "2025-08-03T11:58:51.159Z",
        birth_place: "string",
        address: "string",
        phone_number: "string",
        department_id: "68824cd9ed968052635f41b9", // Pakai department_id yang sama
        start_year: 0,
        end_year: 0
      }
    };

    let createUserRes = http.post(`${BASE_URL}/users/`, JSON.stringify(createUserPayload), {
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });

    let userCreated = check(createUserRes, {
      'user berhasil dibuat': (res) => res.status === 200 || res.status === 201,
    });

    if (userCreated) {
      successCount++;
      if (successCount % 100 === 0) {
        console.log(`✅ Progress: ${successCount}/${TOTAL_USERS} users created`);
      }
    } else {
      failCount++;
      if (failCount <= 10) { // Log hanya 10 error pertama
        console.log(`❌ Failed to create user ${user.login_id}: Status ${createUserRes.status}`);
        console.log(`📝 Error body: ${createUserRes.body.substring(0, 300)}`);
      }
    }

    // Small delay untuk tidak overwhelm server
    if (i % 50 === 0) {
      sleep(0.1);
    }
  }

  console.log(`🎯 Setup completed! Success: ${successCount}, Failed: ${failCount}`);
  console.log('⏳ Waiting for mass login phase...');
}

// Phase 2: Mass Login - 1000 user login bersamaan
export function massLoginPhase() {
  const vuIndex = __VU - 1;
  const currentUser = generatedUsers[vuIndex];
  
  if (!currentUser) {
    console.log(`VU ${__VU}: No user assigned, skipping...`);
    return;
  }

  console.log(`🔐 VU ${__VU}: Attempting login for ${currentUser.login_id}`);
  
  let loginPayload = {
    grant_type: 'password',
    username: currentUser.login_id, // Pakai login_id untuk username
    password: currentUser.login_id, // Password sama dengan login_id
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
    'mass login berhasil': (res) => res.status === 200,
    'mendapat token': (res) => res.json('access_token') !== undefined,
    'response time < 10s': (res) => res.timings.duration < 10000,
  });

  if (loginSuccess) {
    let token = loginRes.json('access_token');
    console.log(`✅ ${currentUser.login_id}: Login SUCCESS!`);
    
    // Simpan token untuk phase berikutnya (ini hack, tapi works)
    userTokens[vuIndex] = token;
  } else {
    console.log(`❌ ${currentUser.login_id}: Login FAILED - Status: ${loginRes.status}`);
    if (loginRes.status !== 200) {
      console.log(`📝 ${currentUser.login_id}: Error: ${loginRes.body.substring(0, 200)}`);
    }
  }
}

// Phase 3: Load Test - Akses endpoint /api/v1/users/?role=student
export function loadTestPhase() {
  const vuIndex = __VU - 1;
  const currentUser = generatedUsers[vuIndex];
  const token = userTokens[vuIndex];
  
  if (!currentUser || !token) {
    console.log(`VU ${__VU}: No user or token available, skipping...`);
    return;
  }

  console.log(`🎯 VU ${__VU}: Testing API call for ${currentUser.login_id}`);
  
  // GET request ke /api/v1/users/?role=student
  let apiRes = http.get(`${BASE_URL}/users/?role=student`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/json',
    },
  });

  let apiSuccess = check(apiRes, {
    'API call berhasil': (res) => res.status === 200,
    'response time < 5s': (res) => res.timings.duration < 5000,
    'response has data': (res) => {
      try {
        const body = res.json();
        return body !== null && body !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (apiSuccess) {
    console.log(`✅ ${currentUser.login_id}: API call SUCCESS!`);
    
    // Optional: Log response info
    try {
      const responseData = apiRes.json();
      if (Array.isArray(responseData)) {
        console.log(`📊 ${currentUser.login_id}: Found ${responseData.length} students`);
      } else if (responseData.data && Array.isArray(responseData.data)) {
        console.log(`📊 ${currentUser.login_id}: Found ${responseData.data.length} students`);
      }
    } catch (e) {
      console.log(`📊 ${currentUser.username}: Response received but not JSON array`);
    }
  } else {
    console.log(`❌ ${currentUser.login_id}: API call FAILED - Status: ${apiRes.status}`);
    if (apiRes.status !== 200) {
      console.log(`📝 ${currentUser.login_id}: Error: ${apiRes.body.substring(0, 200)}`);
    }
  }
}

// Default function (tidak dipakai tapi required)
export default function () {
  // Tidak dipakai karena kita pakai exec functions
}