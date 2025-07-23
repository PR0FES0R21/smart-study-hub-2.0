from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(0.5, 1)  # waktu antar request user (bisa diatur lebih kecil)

    @task
    def login(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "password",
            "username": "79111953",   # GANTI dengan username valid
            "password": "admin123",   # GANTI dengan password valid
        }

        self.client.post(
            "/api/v1/auth/login",
            data=data,
            headers=headers,
            name="Login"
        )
