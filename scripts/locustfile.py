"""Veridoc — Locust load test file.

Simulates realistic user behavior against the Veridoc API:
  1. Register a new user (once per worker)
  2. Login to get JWT tokens
  3. List documents (pagination)
  4. List conversations (pagination)
  5. Check health endpoint
  6. Get current user profile

Usage (headless, for CI)::

    locust -f scripts/locustfile.py \\
           --headless \\
           --users 10 --spawn-rate 2 \\
           --run-time 60s \\
           --host http://localhost:8000 \\
           --csv results/load_test

Usage (web UI, for interactive debugging)::

    locust -f scripts/locustfile.py \\
           --host http://localhost:8000

Requires: locust >= 2.30  (pip install locust)
Requires: the full Veridoc stack running at HOST
"""

from __future__ import annotations

import json
import random
import string

from locust import HttpUser, between, task, tag


# ── Helper ────────────────────────────────────────────────────────


def _random_email() -> str:
    """Generate a unique test email using the reserved .example TLD (RFC 2606)."""
    suffix = "".join(random.choices(string.ascii_lowercase, k=8))
    return f"loadtest_{suffix}@veridoc-test.example"


def _random_password() -> str:
    """Generate a password that passes complexity requirements."""
    return "TestPass" + str(random.randint(1000, 9999)) + "!"


# ══════════════════════════════════════════════════════════════════
# User class
# ══════════════════════════════════════════════════════════════════


class VeridocUser(HttpUser):
    """Simulates a Veridoc end-user performing common API operations.

    Each Locust user spawns with its own unique credentials (registered
    at start) and performs a mix of authenticated and unauthenticated
    requests.

    Wait time: 1-3 seconds between tasks (simulates human reading).
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Register and log in once per user."""
        self.email = _random_email()
        self.password = _random_password()
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self._login()

    # ── Auth helpers ─────────────────────────────────────────────

    def _login(self):
        """Register a new user, then log in to get tokens."""
        payload = {
            "email": self.email,
            "password": self.password,
            "full_name": f"Load Test {self.email[:8]}",
        }
        with self.client.post(
            "/api/v1/auth/register",
            json=payload,
            catch_response=True,
            name="auth_register",
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
            elif resp.status_code == 409:
                # Already registered from a previous run — log in instead
                self._login_existing()
            else:
                resp.failure(f"Register failed: {resp.status_code}")

    def _login_existing(self):
        """Log in with existing credentials (when register returns 409)."""
        payload = {"email": self.email, "password": self.password}
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            catch_response=True,
            name="auth_login",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
            else:
                resp.failure(f"Login failed: {resp.status_code}")

    def _ensure_token(self) -> bool:
        """Refresh the access token if needed (silent — no failure reported).

        Returns ``True`` if a valid access token is now available.
        """
        if self.access_token:
            return True
        if not self.refresh_token:
            return False
        return self._refresh_token()

    def _refresh_token(self) -> bool:
        """Attempt to refresh the access token. Returns True on success.

        Does NOT call ``resp.failure()`` — failures are expected during
        token rotation and should not inflate the error rate.  The next
        task will hit a 401 and the user will eventually degrade.
        """
        if not self.refresh_token:
            return False
        payload = {"refresh_token": self.refresh_token}
        with self.client.post(
            "/api/v1/auth/refresh",
            json=payload,
            catch_response=True,
            name="auth_refresh",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                old_refresh = self.refresh_token
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                return True
            # Don't call resp.failure() — token rotation means old tokens
            # expire naturally; this is expected behavior.
            return False

    def _get_headers(self) -> dict:
        """Return auth headers if token is available."""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    # ── Tasks ────────────────────────────────────────────────────

    @task(5)
    @tag("health")
    def health_check(self):
        """Check the health endpoint (no auth required)."""
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
            name="health_check",
        ) as resp:
            if resp.status_code not in (200, 503):
                resp.failure(f"Health check failed: {resp.status_code}")
            else:
                try:
                    data = resp.json()
                    assert "status" in data
                    assert "dependencies" in data
                except (json.JSONDecodeError, AssertionError) as e:
                    resp.failure(f"Health check response malformed: {e}")

    @task(3)
    @tag("auth")
    def get_me(self):
        """Get the current user's profile (authenticated)."""
        if not self._ensure_token():
            return
        with self.client.get(
            "/api/v1/auth/me",
            headers=self._get_headers(),
            catch_response=True,
            name="auth_me",
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    assert "email" in data
                except (json.JSONDecodeError, AssertionError) as e:
                    resp.failure(f"Auth/me response malformed: {e}")
            elif resp.status_code == 401:
                # Silently refresh — don't mark the original task as
                # failed since token expiration is expected under load.
                self._refresh_token()
            else:
                resp.failure(f"Auth/me failed: {resp.status_code}")

    @task(3)
    @tag("documents")
    def list_documents(self):
        """List documents with pagination (authenticated)."""
        if not self._ensure_token():
            return
        params = {"limit": 20, "offset": 0}
        with self.client.get(
            "/api/v1/documents/",
            headers=self._get_headers(),
            params=params,
            catch_response=True,
            name="list_documents",
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    assert "items" in data
                    assert "total" in data
                    assert "limit" in data
                    assert "offset" in data
                except (json.JSONDecodeError, AssertionError) as e:
                    resp.failure(f"List documents response malformed: {e}")
            elif resp.status_code == 401:
                self._refresh_token()
            else:
                resp.failure(f"List documents failed: {resp.status_code}")

    @task(2)
    @tag("conversations")
    def list_conversations(self):
        """List conversations with pagination (authenticated)."""
        if not self._ensure_token():
            return
        params = {"limit": 20, "offset": 0}
        with self.client.get(
            "/api/v1/chat/conversations",
            headers=self._get_headers(),
            params=params,
            catch_response=True,
            name="list_conversations",
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    assert "items" in data
                    assert "total" in data
                except (json.JSONDecodeError, AssertionError) as e:
                    resp.failure(f"List conversations malformed: {e}")
            elif resp.status_code == 401:
                self._refresh_token()
            else:
                resp.failure(f"List conversations failed: {resp.status_code}")

    @task(1)
    @tag("documents")
    def get_single_document(self):
        """Get a single document's details (requires a valid document ID)."""
        if not self._ensure_token():
            return
        # First list to get a document ID
        with self.client.get(
            "/api/v1/documents/",
            headers=self._get_headers(),
            params={"limit": 5, "offset": 0},
            catch_response=True,
            name="list_for_detail",
        ) as resp:
            if resp.status_code != 200:
                # Don't report as failure — this is just to find an ID
                return
            try:
                data = resp.json()
                items = data.get("items", [])
            except Exception:
                return
            if not items:
                return
            doc_id = items[0]["id"]
            with self.client.get(
                f"/api/v1/documents/{doc_id}",
                headers=self._get_headers(),
                catch_response=True,
                name="get_document",
            ) as detail_resp:
                if detail_resp.status_code == 200:
                    try:
                        detail_data = detail_resp.json()
                        assert "id" in detail_data
                    except (json.JSONDecodeError, AssertionError) as e:
                        detail_resp.failure(
                            f"Get document response malformed: {e}"
                        )
                elif detail_resp.status_code == 401:
                    self._refresh_token()
                else:
                    detail_resp.failure(
                        f"Get document failed: {detail_resp.status_code}"
                    )
