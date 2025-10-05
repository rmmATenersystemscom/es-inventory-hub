#!/usr/bin/env python3
"""
Test script for ES Inventory Hub API Server
"""

import requests
import json
from datetime import date

API_BASE = "https://db-api.enersystems.com:5400"

def test_endpoint(endpoint, method="GET", data=None):
    """Test an API endpoint."""
    url = f"{API_BASE}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing {method} {endpoint}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("Response (formatted):")
                print(json.dumps(data, indent=2))
            except:
                print("Response (text):")
                print(response.text)
        else:
            print("Error Response:")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    """Run API tests."""
    print("ES Inventory Hub API Test Suite")
    print("=" * 60)
    
    # Test health check
    test_endpoint("/api/health")
    
    # Test system status
    test_endpoint("/api/status")
    
    # Test latest variance report
    test_endpoint("/api/variance-report/latest")
    
    # Test collector status
    test_endpoint("/api/collectors/status")
    
    # Test exceptions endpoint
    test_endpoint("/api/exceptions?limit=5")
    
    # Test specific date variance report (if data exists)
    test_endpoint("/api/variance-report/2025-09-13")
    
    print(f"\n{'='*60}")
    print("API Test Suite Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
