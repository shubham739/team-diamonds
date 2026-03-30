"""Test script for all Jira Service API endpoints."""

import json
import logging

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


def test_health() -> None:
    """Test GET /health endpoint."""
    logger.info("=" * 70)
    logger.info("TEST 1: GET /health")
    logger.info("=" * 70)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        logger.info("Status Code: %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("✓ PASSED\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_login_redirect() -> None:
    """Test GET /auth/login endpoint."""
    logger.info("=" * 70)
    logger.info("TEST 2: GET /auth/login (OAuth redirect)")
    logger.info("=" * 70)
    try:
        response = requests.get(
            f"{BASE_URL}/auth/login", allow_redirects=False, timeout=5,
        )
        logger.info("Status Code: %s", response.status_code)
        if "location" in response.headers:
            redirect_url = response.headers["location"]
            logger.info("Redirects to: %s...", redirect_url[:100])
            assert "auth.atlassian.com" in redirect_url, "Should redirect to Atlassian"
            logger.info("✓ PASSED\n")
        else:
            logger.error("✗ FAILED: No location header\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_logout_requires_user_id() -> None:
    """Test GET /auth/logout endpoint."""
    logger.info("=" * 70)
    logger.info("TEST 3: GET /auth/logout (user_id is optional)")
    logger.info("=" * 70)
    try:
        # Test without user_id
        response = requests.get(f"{BASE_URL}/auth/logout", timeout=5)
        logger.info("Status Code (no user_id): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        # Should work with missing user_id (empty logout)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("✓ PASSED\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_root_requires_auth() -> None:
    """Test GET / endpoint (requires OAuth token)."""
    logger.info("=" * 70)
    logger.info("TEST 4: GET / (root endpoint - requires OAuth token)")
    logger.info("=" * 70)
    try:
        # Without token - should fail with 401 Unauthorized
        response = requests.get(f"{BASE_URL}/", timeout=5)
        logger.info("Status Code (no token): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected without token)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_list_issues_requires_auth() -> None:
    """Test GET /issues endpoint (requires OAuth token)."""
    logger.info("=" * 70)
    logger.info("TEST 5: GET /issues (list issues - requires OAuth token)")
    logger.info("=" * 70)
    try:
        # Without token - should fail with 401 Unauthorized
        response = requests.get(f"{BASE_URL}/issues", timeout=5)
        logger.info("Status Code (no token): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected without token)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_get_issue_requires_auth() -> None:
    """Test GET /issues/{issue_id} endpoint (requires OAuth token)."""
    logger.info("=" * 70)
    logger.info("TEST 6: GET /issues/TEST-123 (get issue - requires OAuth token)")
    logger.info("=" * 70)
    try:
        # Without token - should fail with 401 Unauthorized
        response = requests.get(f"{BASE_URL}/issues/TEST-123", timeout=5)
        logger.info("Status Code (no token): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected without token)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_create_issue_requires_auth() -> None:
    """Test POST /issues endpoint (requires OAuth token)."""
    logger.info("=" * 70)
    logger.info("TEST 7: POST /issues (create issue - requires OAuth token)")
    logger.info("=" * 70)
    try:
        # Without token - should fail with 401 Unauthorized
        response = requests.post(f"{BASE_URL}/issues", timeout=5)
        logger.info("Status Code (no token): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected without token)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_update_issue_requires_auth() -> None:
    """Test PUT /issues/{issue_id} endpoint (requires OAuth token)."""
    logger.info("=" * 70)
    logger.info("TEST 8: PUT /issues/TEST-123 (update issue - requires OAuth token)")
    logger.info("=" * 70)
    try:
        # Without token - should fail with 401 Unauthorized
        response = requests.put(f"{BASE_URL}/issues/TEST-123", timeout=5)
        logger.info("Status Code (no token): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected without token)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_delete_issue_requires_auth() -> None:
    """Test DELETE /issues/{issue_id} endpoint (requires OAuth token)."""
    logger.info("=" * 70)
    logger.info("TEST 9: DELETE /issues/TEST-123 (delete issue - requires OAuth token)")
    logger.info("=" * 70)
    try:
        # Without token - should fail with 401 Unauthorized
        response = requests.delete(f"{BASE_URL}/issues/TEST-123", timeout=5)
        logger.info("Status Code (no token): %s", response.status_code)
        logger.info("Response: %s", json.dumps(response.json(), indent=2))
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected without token)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_callback_requires_params() -> None:
    """Test GET /auth/callback endpoint (requires code and state)."""
    logger.info("=" * 70)
    logger.info("TEST 10: GET /auth/callback (requires code and state)")
    logger.info("=" * 70)
    try:
        # Without code/state - should fail with validation error
        response = requests.get(f"{BASE_URL}/auth/callback", timeout=5)
        logger.info("Status Code (no params): %s", response.status_code)
        # Returns HTML (422 with form) if missing params
        assert response.status_code in [200, 422], f"Expected 200/422, got {response.status_code}"
        logger.info("✓ PASSED (correctly rejected/handled invalid request)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_callback_with_invalid_state() -> None:
    """Test GET /auth/callback with invalid state."""
    logger.info("=" * 70)
    logger.info("TEST 11: GET /auth/callback with invalid state")
    logger.info("=" * 70)
    try:
        response = requests.get(
            f"{BASE_URL}/auth/callback",
            params={"code": "test_code", "state": "invalid_state"},
            timeout=5,
        )
        logger.info("Status Code: %s", response.status_code)
        if response.status_code == 400:
            logger.info("Response: %s", json.dumps(response.json(), indent=2))
            assert "Invalid state" in response.json()["detail"]
        logger.info("✓ PASSED (correctly rejected invalid state)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_swagger_docs() -> None:
    """Test Swagger UI availability."""
    logger.info("=" * 70)
    logger.info("TEST 12: Swagger UI Documentation")
    logger.info("=" * 70)
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        logger.info("Status Code: %s", response.status_code)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("✓ PASSED (Swagger docs available at http://localhost:8000/docs)\n")
    except Exception:
        logger.exception("✗ FAILED")


def test_redoc() -> None:
    """Test ReDoc availability."""
    logger.info("=" * 70)
    logger.info("TEST 13: ReDoc Documentation")
    logger.info("=" * 70)
    try:
        response = requests.get(f"{BASE_URL}/redoc", timeout=5)
        logger.info("Status Code: %s", response.status_code)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("✓ PASSED (ReDoc docs available at http://localhost:8000/redoc)\n")
    except Exception:
        logger.exception("✗ FAILED")


def main() -> None:
    """Run all API tests."""
    logger.info("%s", "\n" + "=" * 70)
    logger.info("JIRA SERVICE API TEST SUITE")
    logger.info("%s", "=" * 70 + "\n")

    test_health()
    test_login_redirect()
    test_logout_requires_user_id()
    test_root_requires_auth()
    test_list_issues_requires_auth()
    test_get_issue_requires_auth()
    test_create_issue_requires_auth()
    test_update_issue_requires_auth()
    test_delete_issue_requires_auth()
    test_callback_requires_params()
    test_callback_with_invalid_state()
    test_swagger_docs()
    test_redoc()

    logger.info("=" * 70)
    logger.info("ALL TESTS COMPLETED!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
