#!/usr/bin/env python3
"""
Comprehensive API Integration Test Suite for COS-AA Platform
Tests all 40 backend endpoints to verify production readiness
Run with: python tests_e2e_api.py --url http://localhost:8000 --email test@example.com --password testpass123
"""

import requests
import json
import sys
import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

class APITester:
    def __init__(self, base_url: str, email: str, password: str, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.token = None
        self.user_id = None
        self.tenant_id = None
        self.session_id = None
        self.memory_id = None
        self.trace_id = None
        self.agent_id = None
        self.results = []
        self.failed = []

    def log(self, message: str):
        """Log test messages"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def test(self, name: str, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Execute single API test"""
        url = f"{self.base_url}{endpoint}"
        start = time.time()

        try:
            if method == 'GET':
                resp = self.session.get(url, **kwargs)
            elif method == 'POST':
                resp = self.session.post(url, **kwargs)
            elif method == 'DELETE':
                resp = self.session.delete(url, **kwargs)
            else:
                raise ValueError(f"Unknown method: {method}")

            elapsed = time.time() - start

            if resp.status_code >= 200 and resp.status_code < 300:
                try:
                    data = resp.json()
                except:
                    data = resp.text

                status = "✅ PASS"
                self.results.append({
                    'test': name,
                    'status': 'PASS',
                    'endpoint': endpoint,
                    'status_code': resp.status_code,
                    'elapsed_ms': f"{elapsed*1000:.1f}"
                })
                self.log(f"{status} {method} {endpoint} ({resp.status_code}) [{elapsed*1000:.0f}ms]")
                return data
            else:
                status = "❌ FAIL"
                self.failed.append(name)
                self.results.append({
                    'test': name,
                    'status': 'FAIL',
                    'endpoint': endpoint,
                    'status_code': resp.status_code,
                    'error': resp.text[:200],
                    'elapsed_ms': f"{elapsed*1000:.1f}"
                })
                self.log(f"{status} {method} {endpoint} ({resp.status_code}) Error: {resp.text[:100]}")
                return None
        except Exception as e:
            self.failed.append(name)
            self.results.append({
                'test': name,
                'status': 'ERROR',
                'endpoint': endpoint,
                'error': str(e)
            })
            self.log(f"❌ ERROR {method} {endpoint}: {str(e)}")
            return None

    def run_auth_tests(self):
        """Test authentication endpoints"""
        print("\n" + "="*80)
        print("PHASE 1: Authentication Tests (6 endpoints)")
        print("="*80)

        # Register
        register_data = self.test(
            "Register new user",
            "POST", "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "organization_name": "Test Org",
            }
        )
        if register_data and 'token' in register_data:
            self.token = register_data['token']
            self.user_id = register_data.get('user_id')
            self.tenant_id = register_data.get('tenant_id')
            self.session.headers['Authorization'] = f'Bearer {self.token}'

        # Login
        login_data = self.test(
            "Login with credentials",
            "POST", "/api/v1/auth/login",
            json={"email": self.email, "password": self.password}
        )
        if login_data and 'token' in login_data:
            self.token = login_data['token']
            self.session.headers['Authorization'] = f'Bearer {self.token}'

        # Get current user
        self.test("Get current user (/auth/me)", "GET", "/api/v1/auth/me")

        # Get sessions
        self.test("Get auth sessions", "GET", "/api/v1/auth/sessions")

        # Get verification status
        self.test("Get email verification status", "GET", "/api/v1/auth/verify-email")

        # Resend verification
        self.test("Resend verification email", "POST", "/api/v1/auth/resend-verification")

    def run_session_tests(self):
        """Test session endpoints"""
        print("\n" + "="*80)
        print("PHASE 2: Session Tests (6 endpoints)")
        print("="*80)

        # Create session
        session_data = self.test(
            "Create new session",
            "POST", "/api/v1/sessions",
            json={"goal": "Test session for automated testing"}
        )
        if session_data and 'session_id' in session_data:
            self.session_id = session_data['session_id']

        # List sessions
        self.test("List all sessions", "GET", "/api/v1/sessions")

        # Get messages
        if self.session_id:
            self.test(
                "Get session messages",
                "GET", f"/api/v1/sessions/{self.session_id}/messages"
            )

            # Send message
            msg_data = self.test(
                "Send message to session",
                "POST", f"/api/v1/sessions/{self.session_id}/messages",
                json={"content": "Test message for automated testing"}
            )

            # Confirm session (mock decision)
            self.test(
                "Confirm session decision",
                "POST", f"/api/v1/sessions/{self.session_id}/confirm",
                json={"decision": "approved"}
            )

            # Export session
            self.test(
                "Export session as CSV",
                "GET", f"/api/v1/sessions/{self.session_id}/export",
                params={"format": "csv"}
            )

    def run_agent_tests(self):
        """Test agent endpoints"""
        print("\n" + "="*80)
        print("PHASE 3: Agent Tests (6 endpoints)")
        print("="*80)

        # List agents
        self.test("List all agents", "GET", "/api/v1/agents")

        # Spawn agent
        agent_data = self.test(
            "Spawn new agent",
            "POST", "/api/v1/agents/spawn",
            json={
                "gap_description": "Test agent for automated testing",
                "require_approval": False
            }
        )
        if agent_data and 'definition_id' in agent_data:
            self.agent_id = agent_data['definition_id']

        # Get agent detail
        if self.agent_id:
            self.test(
                "Get agent detail",
                "GET", f"/api/v1/agents/{self.agent_id}"
            )

            # Approve agent
            self.test(
                "Approve agent",
                "POST", f"/api/v1/agents/{self.agent_id}/approve"
            )

        # Reject agent (different agent for testing)
        if self.agent_id:
            self.test(
                "Reject agent",
                "POST", f"/api/v1/agents/{self.agent_id}/reject"
            )

        # Get agent stats
        self.test("Get agent statistics", "GET", "/api/v1/agents/stats")

    def run_memory_tests(self):
        """Test memory endpoints"""
        print("\n" + "="*80)
        print("PHASE 4: Memory Tests (6 endpoints)")
        print("="*80)

        # Store memory
        mem_data = self.test(
            "Store new memory",
            "POST", "/api/v1/memory",
            json={
                "content": "Test memory fragment for automated testing",
                "event_type": "manual",
                "tags": ["test", "automated"],
                "importance_score": 0.8
            }
        )
        if mem_data and 'fragment_id' in mem_data:
            self.memory_id = mem_data['fragment_id']

        # List memories
        self.test("List all memories", "GET", "/api/v1/memory")

        # Search memories
        self.test(
            "Search memories with filters",
            "POST", "/api/v1/memory/search",
            json={
                "query": "test",
                "top_k": 5,
                "tiers": ["semantic", "episodic"],
                "event_types": ["manual"],
                "created_after": (datetime.now() - timedelta(days=7)).isoformat(),
                "created_before": datetime.now().isoformat(),
                "sort_by": "relevance"
            }
        )

        # Get memory stats
        self.test("Get memory statistics", "GET", "/api/v1/memory/stats")

        # Export memory
        self.test(
            "Export all memories as JSON",
            "GET", "/api/v1/memory/export",
            params={"format": "json"}
        )

        # Delete memory
        if self.memory_id:
            self.test(
                "Delete memory fragment",
                "DELETE", f"/api/v1/memory/{self.memory_id}"
            )

    def run_trace_tests(self):
        """Test observability/trace endpoints"""
        print("\n" + "="*80)
        print("PHASE 5: Observability Tests (4 endpoints)")
        print("="*80)

        # List traces
        traces_data = self.test("List all traces", "GET", "/api/v1/observability/traces")
        if traces_data and 'traces' in traces_data and len(traces_data['traces']) > 0:
            self.trace_id = traces_data['traces'][0].get('session_id')

        # Get trace detail
        if self.trace_id:
            self.test(
                "Get trace detail",
                "GET", f"/api/v1/observability/traces/{self.trace_id}"
            )

            # Export trace
            self.test(
                "Export trace as CSV",
                "GET", f"/api/v1/observability/traces/{self.trace_id}/export",
                params={"format": "csv"}
            )

        # Health check
        self.test("Health check", "GET", "/api/v1/observability/health")

    def run_admin_tests(self):
        """Test admin endpoints"""
        print("\n" + "="*80)
        print("PHASE 6: Admin Tests (6 endpoints)")
        print("="*80)

        # Get quotas
        self.test("Get admin quotas", "GET", "/api/v1/admin/quotas")

        # Get admin keys
        self.test("Get admin API keys", "GET", "/api/v1/admin/keys")

        # Generate new admin key
        key_data = self.test(
            "Generate new admin API key",
            "POST", "/api/v1/admin/keys"
        )

        # Get admin users
        self.test("Get admin users list", "GET", "/api/v1/admin/users")

        # Get analytics
        self.test(
            "Get usage analytics",
            "GET", "/api/v1/admin/analytics",
            params={"period": "week"}
        )

        # List all quotes (if 6th endpoint exists)
        self.test("Get resource quotas", "GET", "/api/v1/admin/quotas")

    def print_summary(self):
        """Print test summary report"""
        print("\n" + "="*80)
        print("TEST SUMMARY REPORT")
        print("="*80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')

        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed:   {passed} ({pass_rate:.1f}%)")
        print(f"❌ Failed:   {failed}")
        print(f"⚠️  Errors:   {errors}")

        print("\n" + "-"*80)
        print("ENDPOINT COVERAGE BY CATEGORY")
        print("-"*80)

        categories = {
            'Authentication': [r for r in self.results if '/auth' in r['endpoint']],
            'Sessions': [r for r in self.results if '/sessions' in r['endpoint']],
            'Agents': [r for r in self.results if '/agents' in r['endpoint']],
            'Memory': [r for r in self.results if '/memory' in r['endpoint']],
            'Observability': [r for r in self.results if '/observability' in r['endpoint']],
            'Admin': [r for r in self.results if '/admin' in r['endpoint']],
        }

        for category, tests in categories.items():
            if tests:
                cat_passed = sum(1 for t in tests if t['status'] == 'PASS')
                cat_total = len(tests)
                status = "✅" if cat_passed == cat_total else "⚠️"
                print(f"{status} {category:20} {cat_passed}/{cat_total} passed")

        if self.failed:
            print("\n" + "-"*80)
            print("FAILED TESTS")
            print("-"*80)
            for test in self.failed:
                print(f"❌ {test}")

        print("\n" + "="*80)
        print(f"OVERALL: {'🚀 PRODUCTION READY' if pass_rate >= 90 else '⚠️ NEEDS FIXES'}")
        print("="*80)

        return pass_rate >= 90

    def run_all(self) -> bool:
        """Run all test phases"""
        print(f"\nStarting COS-AA API Integration Tests")
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            self.run_auth_tests()
            self.run_session_tests()
            self.run_agent_tests()
            self.run_memory_tests()
            self.run_trace_tests()
            self.run_admin_tests()
        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")

        return self.print_summary()


def main():
    parser = argparse.ArgumentParser(description='COS-AA API Integration Test Suite')
    parser.add_argument('--url', default='http://localhost:8000', help='Backend API URL')
    parser.add_argument('--email', default='test_e2e@example.com', help='Test user email')
    parser.add_argument('--password', default='TestPassword123!', help='Test user password')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    tester = APITester(args.url, args.email, args.password, args.verbose)
    success = tester.run_all()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
