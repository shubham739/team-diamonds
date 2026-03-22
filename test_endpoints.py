"""Test all endpoints of the FastAPI service."""
import logging

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def test_health() -> None:
    """Test health check endpoint."""
    logger.info("1. GET /health")
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        logger.info("   Status: %s", r.status_code)
        logger.info("   Response: %s\n", r.json())
    except Exception:
        logger.exception("   ERROR")


def test_root() -> None:
    """Test root endpoint (Jira issues)."""
    logger.info("2. GET / (Jira issues)")
    try:
        r = requests.get("http://localhost:8000/", timeout=10)
        logger.info("   Status: %s", r.status_code)
        data = r.json()
        if "issues" in data:
            issues = data["issues"]
            logger.info("   Issues found: %s", len(issues))
            for issue in issues:
                logger.info("     - %s: %s (%s)", issue["id"], issue["title"], issue["status"])
        else:
            logger.info("   Response: %s", data)
        logger.info("")
    except Exception:
        logger.exception("   ERROR")


def test_login() -> None:
    """Test login endpoint."""
    logger.info("3. GET /auth/login")
    try:
        r = requests.get("http://localhost:8000/auth/login", allow_redirects=False, timeout=5)
        logger.info("   Status: %s", r.status_code)
        if "location" in r.headers:
            redirect_url = r.headers["location"]
            logger.info("   Redirects to: %s...", redirect_url[:80])
        logger.info("")
    except Exception:
        logger.exception("   ERROR")


def test_logout() -> None:
    """Test logout endpoint."""
    logger.info("4. GET /auth/logout (without user_id)")
    try:
        r = requests.get("http://localhost:8000/auth/logout", timeout=5)
        logger.info("   Status: %s", r.status_code)
        logger.info("   Response: %s\n", r.json())
    except Exception:
        logger.exception("   ERROR")


def test_callback() -> None:
    """Test callback endpoint."""
    logger.info("5. GET /auth/callback (without code/state)")
    try:
        r = requests.get("http://localhost:8000/auth/callback", timeout=5)
        logger.info("   Status: %s", r.status_code)
        logger.info("   Response: %s\n", r.json())
    except Exception:
        logger.exception("   ERROR")


def main() -> None:
    """Run all endpoint tests."""
    logger.info("Testing all endpoints...\n")
    test_health()
    test_root()
    test_login()
    test_logout()
    test_callback()
    logger.info("All endpoint tests completed!")


if __name__ == "__main__":
    main()
