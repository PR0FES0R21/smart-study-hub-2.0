import http from 'k6/http';
import { check, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export let options = {
  vus: 1000,      // Jumlah user virtual (1000 user baru)
  duration: '30s' // Sesuaikan durasi (opsional)
};

export default function () {
  // Langkah 1: Login admin atau user yang punya akses tambah user
  let loginPayload = {
    grant_type: 'password',
    username: '79111953', // ganti kalau perlu
    password: 'admin123',
    scope: '',
    client_id: 'string',
    client_secret: '********',
  };

  let formBody = Object.entries(loginPayload)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');

  let loginRes = http.post('http://localhost:8000/api/v1/auth/login', formBody, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json',
    },
  });

  check(loginRes, {
    'login berhasil': (res) => res.status === 200,
  });

  let token = loginRes.json('access_token');

  // Langkah 2: Buat data user baru dengan ID unik
  let uniqueId = uuidv4(); // bikin UUID untuk jamin keunikan
  let login_id = uniqueId.slice(0, 8); // potong jadi 8 karakter
  let email = `${login_id}@example.com`;

  let payload = JSON.stringify({
    login_id: login_id,
    email: email,
    roles: ["student"],
    is_active: true,
    profile: {
      full_name: "string",
      gender: "string",
      birth_date: "2025-08-03T06:08:37.401Z",
      birth_place: "string",
      address: "string",
      phone_number: "string",
      class_id: "687e01044593234141867820", // sesuaikan dengan real ID
      start_year: 2025,
      end_year: 2026
    }
  });

  let createRes = http.post('http://localhost:8000/api/v1/users/', payload, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  check(createRes, {
    'user created': (res) => res.status === 201 || res.status === 200,
  });

  sleep(1); // simulasi jeda antar user
}
