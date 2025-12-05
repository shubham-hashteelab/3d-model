#!/usr/bin/env python3
"""
Basic tests for WebSocket API functionality.
"""

import requests
import json
import time


def test_session_creation(base_url="http://localhost:8000"):
    """Test creating a WebSocket session."""
    print("Testing session creation...")
    
    response = requests.post(
        f"{base_url}/ws/session/create",
        params={
            "max_images": 50,
            "process_res": 504,
        }
    )
    
    assert response.status_code == 200, f"Failed to create session: {response.status_code}"
    
    data = response.json()
    assert "session_id" in data, "Response missing session_id"
    assert "success" in data and data["success"], "Session creation not successful"
    
    session_id = data["session_id"]
    print(f"✓ Created session: {session_id}")
    
    return session_id


def test_get_session(base_url, session_id):
    """Test retrieving session information."""
    print(f"Testing get session info for {session_id}...")
    
    response = requests.get(f"{base_url}/ws/session/{session_id}")
    
    assert response.status_code == 200, f"Failed to get session: {response.status_code}"
    
    data = response.json()
    assert data["session_id"] == session_id
    assert data["status"] == "active"
    assert data["image_count"] == 0
    
    print(f"✓ Retrieved session info")
    print(f"  Status: {data['status']}")
    print(f"  Images: {data['image_count']}/{data['max_images']}")
    
    return data


def test_list_sessions(base_url):
    """Test listing all sessions."""
    print("Testing list sessions...")
    
    response = requests.get(f"{base_url}/ws/sessions")
    
    assert response.status_code == 200, f"Failed to list sessions: {response.status_code}"
    
    data = response.json()
    assert "stats" in data
    assert "sessions" in data
    
    print(f"✓ Listed sessions")
    print(f"  Total: {data['stats']['total_sessions']}")
    print(f"  Active: {data['stats']['active_sessions']}")
    
    return data


def test_delete_session(base_url, session_id):
    """Test deleting a session."""
    print(f"Testing delete session {session_id}...")
    
    response = requests.delete(f"{base_url}/ws/session/{session_id}")
    
    assert response.status_code == 200, f"Failed to delete session: {response.status_code}"
    
    data = response.json()
    assert data["success"], "Delete not successful"
    
    print(f"✓ Deleted session")
    
    # Verify session is gone
    response = requests.get(f"{base_url}/ws/session/{session_id}")
    assert response.status_code == 404, "Session still exists after deletion"
    
    print(f"✓ Verified session is deleted")


def test_session_not_found(base_url):
    """Test handling of non-existent session."""
    print("Testing session not found...")
    
    fake_session_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{base_url}/ws/session/{fake_session_id}")
    
    assert response.status_code == 404, "Should return 404 for non-existent session"
    
    print(f"✓ Correctly returns 404 for non-existent session")


def run_all_tests(base_url="http://localhost:8000"):
    """Run all tests."""
    print("=" * 60)
    print("WebSocket API Tests")
    print("=" * 60)
    print(f"Testing against: {base_url}\n")
    
    try:
        # Check server is running
        print("Checking server status...")
        response = requests.get(f"{base_url}/status")
        if response.status_code != 200:
            print(f"❌ Server not responding properly: {response.status_code}")
            return False
        print(f"✓ Server is running\n")
        
        # Run tests
        test_session_not_found(base_url)
        print()
        
        session_id = test_session_creation(base_url)
        print()
        
        test_get_session(base_url, session_id)
        print()
        
        # Create a second session to test listing
        session_id2 = test_session_creation(base_url)
        print()
        
        test_list_sessions(base_url)
        print()
        
        test_delete_session(base_url, session_id)
        print()
        
        test_delete_session(base_url, session_id2)
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test WebSocket API")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the server")
    
    args = parser.parse_args()
    
    success = run_all_tests(args.base_url)
    exit(0 if success else 1)

