#!/usr/bin/env python3
"""Test QBR API endpoints"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from api.qbr_api import qbr_api

# Create test app
app = Flask(__name__)
app.register_blueprint(qbr_api)

# Create test client
client = app.test_client()


def test_monthly_metrics():
    """Test GET /api/qbr/metrics/monthly"""
    print("\n" + "="*80)
    print("Testing GET /api/qbr/metrics/monthly")
    print("="*80)

    # Test with period 2025-11
    response = client.get('/api/qbr/metrics/monthly?period=2025-11')
    print(f"Status: {response.status_code}")
    data = json.loads(response.data)
    print(f"Success: {data.get('success')}")

    if data.get('success'):
        metrics = data.get('data', {}).get('metrics', [])
        print(f"Metrics count: {len(metrics)}")
        for metric in metrics[:5]:  # Show first 5
            print(f"  - {metric['metric_name']}: {metric['metric_value']} (vendor_id={metric['vendor_id']})")
    else:
        print(f"Error: {data.get('error')}")

    return data.get('success', False)


def test_quarterly_metrics():
    """Test GET /api/qbr/metrics/quarterly"""
    print("\n" + "="*80)
    print("Testing GET /api/qbr/metrics/quarterly")
    print("="*80)

    # We don't have 3 full months yet, so expect limited data
    response = client.get('/api/qbr/metrics/quarterly?period=2025-Q4')
    print(f"Status: {response.status_code}")
    data = json.loads(response.data)
    print(f"Success: {data.get('success')}")

    if data.get('success'):
        metrics = data.get('data', {}).get('metrics', {})
        print(f"Quarterly metrics count: {len(metrics)}")
        for name, value in list(metrics.items())[:5]:  # Show first 5
            print(f"  - {name}: {value}")
    else:
        print(f"Error: {data.get('error')}")

    return data.get('success', False)


def test_smartnumbers():
    """Test GET /api/qbr/smartnumbers"""
    print("\n" + "="*80)
    print("Testing GET /api/qbr/smartnumbers")
    print("="*80)

    # Test with Q4 2025
    response = client.get('/api/qbr/smartnumbers?period=2025-Q4')
    print(f"Status: {response.status_code}")
    data = json.loads(response.data)
    print(f"Success: {data.get('success')}")

    if data.get('success'):
        smartnumbers = data.get('data', {}).get('smartnumbers', {})
        print(f"SmartNumbers count: {len(smartnumbers)}")
        for name, value in list(smartnumbers.items())[:10]:  # Show first 10
            if value is not None:
                print(f"  - {name}: {value}")
    else:
        print(f"Error: {data.get('error')}")

    return data.get('success', False)


def test_manual_entry():
    """Test POST /api/qbr/metrics/manual"""
    print("\n" + "="*80)
    print("Testing POST /api/qbr/metrics/manual")
    print("="*80)

    # Test manual entry for employees
    test_data = {
        "period": "2025-11",
        "organization_id": 1,
        "metrics": [
            {
                "metric_name": "employees",
                "metric_value": 8.5,
                "notes": "Manual test entry"
            },
            {
                "metric_name": "technical_employees",
                "metric_value": 5.5,
                "notes": "Manual test entry"
            }
        ]
    }

    response = client.post(
        '/api/qbr/metrics/manual',
        data=json.dumps(test_data),
        content_type='application/json'
    )
    print(f"Status: {response.status_code}")
    data = json.loads(response.data)
    print(f"Success: {data.get('success')}")

    if data.get('success'):
        print(f"Updated count: {data.get('data', {}).get('updated_count')}")
    else:
        print(f"Error: {data.get('error')}")

    return data.get('success', False)


def test_thresholds():
    """Test GET /api/qbr/thresholds"""
    print("\n" + "="*80)
    print("Testing GET /api/qbr/thresholds")
    print("="*80)

    response = client.get('/api/qbr/thresholds')
    print(f"Status: {response.status_code}")
    data = json.loads(response.data)
    print(f"Success: {data.get('success')}")

    if data.get('success'):
        thresholds = data.get('data', {}).get('thresholds', [])
        print(f"Thresholds count: {len(thresholds)}")
        for threshold in thresholds[:3]:  # Show first 3
            print(f"  - {threshold['metric_name']}: green={threshold['green_min']}-{threshold['green_max']}")
    else:
        print(f"Error: {data.get('error')}")

    return data.get('success', False)


if __name__ == '__main__':
    print("\n" + "="*80)
    print("QBR API Endpoint Tests")
    print("="*80)

    results = {
        'monthly_metrics': test_monthly_metrics(),
        'quarterly_metrics': test_quarterly_metrics(),
        'smartnumbers': test_smartnumbers(),
        'manual_entry': test_manual_entry(),
        'thresholds': test_thresholds()
    }

    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    sys.exit(0 if passed_count == total_count else 1)
