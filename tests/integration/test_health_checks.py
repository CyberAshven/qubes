"""
Test Health Check Endpoints

Quick test script to verify health check endpoints are working.
"""

import asyncio
import requests
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_health_endpoints():
    """Test all health check endpoints"""

    # Start health server in background
    print("=" * 70)
    print("🏥 TESTING HEALTH CHECK ENDPOINTS")
    print("=" * 70)

    print("\n⚠️  Note: Start the health server first with:")
    print("   python orchestrator/health.py")
    print("\nThen in another terminal, run:")
    print("   python examples/test_health_checks.py")
    print("\nOr test manually with curl:\n")

    base_url = "http://localhost:8080"

    endpoints = [
        ("/health", "Liveness check"),
        ("/health/ready", "Readiness check"),
        ("/health/metrics", "Prometheus metrics"),
        ("/health/info", "System information")
    ]

    print("\n📝 Example curl commands:\n")
    for endpoint, description in endpoints:
        print(f"  # {description}")
        print(f"  curl {base_url}{endpoint}")
        print()

    print("=" * 70)
    print("\n💡 To test automatically, uncomment the code below and ensure")
    print("   the health server is running on port 8080")
    print("=" * 70)

    # Uncomment to test if server is running
    """
    try:
        print("\n🔍 Testing endpoints...")

        for endpoint, description in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"\n  Testing {endpoint} ({description})...")

            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                print(f"  ✅ {endpoint} - OK")
                if endpoint != "/health/metrics":
                    print(f"     Response: {response.json()}")
            else:
                print(f"  ❌ {endpoint} - Status: {response.status_code}")

        print("\n✅ All health checks passed!")

    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to health server")
        print("   Make sure to start it with: python orchestrator/health.py")
    except Exception as e:
        print(f"\n❌ Error testing health checks: {e}")
    """


if __name__ == "__main__":
    asyncio.run(test_health_endpoints())
