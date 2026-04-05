"""Load testing for the URL shortener API."""

import os
import random

from locust import HttpUser, between, task

API_KEY = os.environ.get("API_KEY", "dev-api-key-change-me")


class URLShortenerUser(HttpUser):
    """Simulates a typical user hitting all endpoints."""

    wait_time = between(0.5, 2)

    def on_start(self):
        """Fetch some short codes to use for redirect tests."""
        self.short_codes = []
        response = self.client.get("/urls", name="/urls")
        if response.status_code == 200:
            urls = response.json()
            self.short_codes = [u["short_code"] for u in urls[:50]]

    @task(5)
    def redirect_url(self):
        """Most common action: follow a short link."""
        if self.short_codes:
            code = random.choice(self.short_codes)
            with self.client.get(f"/{code}", name="/<short_code>", allow_redirects=False, catch_response=True) as response:
                if response.status_code in (301, 410):
                    response.success()  # 301 = redirect, 410 = inactive — both correct

    @task(3)
    def list_urls(self):
        """Browse URLs."""
        self.client.get("/urls", name="/urls")

    @task(2)
    def get_url_detail(self):
        """View a specific URL's details."""
        url_id = random.randint(1, 100)
        self.client.get(f"/urls/{url_id}", name="/urls/<id>")

    @task(2)
    def list_users(self):
        """List users."""
        self.client.get("/users", name="/users")

    @task(1)
    def get_user_detail(self):
        """View a specific user."""
        user_id = random.randint(1, 50)
        self.client.get(f"/users/{user_id}", name="/users/<id>")

    @task(1)
    def create_short_url(self):
        """Create a new short URL."""
        user_id = random.randint(1, 50)
        with self.client.post(
            "/shorten",
            json={
                "original_url": f"https://example.com/load-test/{random.randint(1, 100000)}",
                "title": "Load test URL",
                "user_id": user_id,
            },
            headers={"X-API-Key": API_KEY},
            name="/shorten",
            catch_response=True,
        ) as response:
            if response.status_code == 429:
                response.success()  # Rate limiting is correct behavior

    @task(1)
    def health_check(self):
        """Verify service is alive."""
        self.client.get("/health", name="/health")
