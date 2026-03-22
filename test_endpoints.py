"""Test all endpoints of the FastAPI service."""
import requests
import json

print('Testing all endpoints...\n')

# Test 1: Health check
print('1. GET /health')
try:
    r = requests.get('http://localhost:8000/health', timeout=5)
    print(f'   Status: {r.status_code}')
    print(f'   Response: {r.json()}\n')
except Exception as e:
    print(f'   ERROR: {e}\n')

# Test 2: Root endpoint (Jira issues)
print('2. GET / (Jira issues)')
try:
    r = requests.get('http://localhost:8000/', timeout=10)
    print(f'   Status: {r.status_code}')
    data = r.json()
    if 'issues' in data:
        issues = data['issues']
        print(f'   Issues found: {len(issues)}')
        for issue in issues:
            print(f"     - {issue['id']}: {issue['title']} ({issue['status']})")
    else:
        print(f'   Response: {data}')
    print()
except Exception as e:
    print(f'   ERROR: {e}\n')

# Test 3: Login endpoint
print('3. GET /auth/login')
try:
    r = requests.get('http://localhost:8000/auth/login', allow_redirects=False, timeout=5)
    print(f'   Status: {r.status_code}')
    if 'location' in r.headers:
        redirect_url = r.headers['location']
        print(f'   Redirects to: {redirect_url[:80]}...')
    print()
except Exception as e:
    print(f'   ERROR: {e}\n')

# Test 4: Logout endpoint (without user_id)
print('4. GET /auth/logout (without user_id)')
try:
    r = requests.get('http://localhost:8000/auth/logout', timeout=5)
    print(f'   Status: {r.status_code}')
    print(f'   Response: {r.json()}\n')
except Exception as e:
    print(f'   ERROR: {e}\n')

# Test 5: Callback endpoint (missing code/state should fail)
print('5. GET /auth/callback (without code/state)')
try:
    r = requests.get('http://localhost:8000/auth/callback', timeout=5)
    print(f'   Status: {r.status_code}')
    print(f'   Response: {r.json()}\n')
except Exception as e:
    print(f'   ERROR: {e}\n')

print('All endpoint tests completed!')
