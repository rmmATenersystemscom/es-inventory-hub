#!/usr/bin/env python3
"""
Demonstration of Windows 11 24H2 Assessment Results
Shows examples of devices that fail the specifications with detailed reasons
"""

import sys
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, '/opt/es-inventory-hub')

from collectors.assessments.windows_11_24h2_assessment import assess_windows_11_24h2_capability

def demonstrate_failed_assessments():
    """Demonstrate Windows 11 24H2 assessment failures with real-world failure scenarios"""
    
    print("=" * 80)
    print("WINDOWS 11 24H2 ASSESSMENT - FAILURE EXAMPLES")
    print("=" * 80)
    print()
    
    # Example 1: Old CPU + TPM 1.2 + No Secure Boot (Common failure scenario)
    print("🔴 DEVICE 1: ENERSYS-PC00FY6 (Windows 10 Professional)")
    print("-" * 60)
    device1_data = {
        'os_architecture': '64-bit',
        'memory_gib': 8.0,
        'volumes': 'C: 500GB',
        'cpu_model': 'Intel Core i5-6500',  # 6th gen - FAILS
        'has_tpm': True,
        'tpm_enabled': True,
        'tpm_version': '1.2, 2, 3',  # TPM 1.2 - FAILS
        'secure_boot_available': False,  # No Secure Boot - FAILS
        'secure_boot_enabled': False
    }
    
    result1 = assess_windows_11_24h2_capability(device1_data)
    print(f"VERDICT: {result1['verdict']}")
    print(f"DEFICIENCIES: {len(result1['deficiencies'])}")
    print()
    
    for i, deficiency in enumerate(result1['deficiencies'], 1):
        print(f"  {i}. {deficiency['requirement']}")
        print(f"     Status: {deficiency['status']}")
        print(f"     Current: {deficiency['current_value']}")
        print(f"     Required: {deficiency['required']}")
        print(f"     Reason: {deficiency['reason']}")
        print(f"     Remediation: {deficiency['remediation']}")
        print()
    
    print("✅ PASSED REQUIREMENTS:")
    for req in result1['passed_requirements']:
        print(f"  ✓ {req['requirement']}: {req['current_value']}")
    print()
    
    # Example 2: AMD Old Generation + TPM 1.2 (Another common failure)
    print("🔴 DEVICE 2: WORKSTATION-OLD-AMD (Windows 10 Enterprise)")
    print("-" * 60)
    device2_data = {
        'os_architecture': '64-bit',
        'memory_gib': 16.0,
        'volumes': 'C: 1000GB',
        'cpu_model': 'AMD Ryzen 5 2600',  # 2000 series - FAILS
        'has_tpm': True,
        'tpm_enabled': True,
        'tpm_version': '1.2, 1.38, 0',  # TPM 1.2 - FAILS
        'secure_boot_available': True,
        'secure_boot_enabled': False  # Available but disabled - FAILS
    }
    
    result2 = assess_windows_11_24h2_capability(device2_data)
    print(f"VERDICT: {result2['verdict']}")
    print(f"DEFICIENCIES: {len(result2['deficiencies'])}")
    print()
    
    for i, deficiency in enumerate(result2['deficiencies'], 1):
        print(f"  {i}. {deficiency['requirement']}")
        print(f"     Status: {deficiency['status']}")
        print(f"     Current: {deficiency['current_value']}")
        print(f"     Required: {deficiency['required']}")
        print(f"     Reason: {deficiency['reason']}")
        print(f"     Remediation: {deficiency['remediation']}")
        print()
    
    print("✅ PASSED REQUIREMENTS:")
    for req in result2['passed_requirements']:
        print(f"  ✓ {req['requirement']}: {req['current_value']}")
    print()
    
    # Example 3: Insufficient Memory + Old Intel CPU
    print("🔴 DEVICE 3: LEGACY-LAPTOP (Windows 10 Home)")
    print("-" * 60)
    device3_data = {
        'os_architecture': '64-bit',
        'memory_gib': 2.0,  # Only 2GB - FAILS
        'volumes': 'C: 128GB',
        'cpu_model': 'Intel Core i3-6100U',  # 6th gen - FAILS
        'has_tpm': True,
        'tpm_enabled': True,
        'tpm_version': '2.0, 0, 1.38',  # TPM 2.0 - PASSES
        'secure_boot_available': True,
        'secure_boot_enabled': True  # Secure Boot - PASSES
    }
    
    result3 = assess_windows_11_24h2_capability(device3_data)
    print(f"VERDICT: {result3['verdict']}")
    print(f"DEFICIENCIES: {len(result3['deficiencies'])}")
    print()
    
    for i, deficiency in enumerate(result3['deficiencies'], 1):
        print(f"  {i}. {deficiency['requirement']}")
        print(f"     Status: {deficiency['status']}")
        print(f"     Current: {deficiency['current_value']}")
        print(f"     Required: {deficiency['required']}")
        print(f"     Reason: {deficiency['reason']}")
        print(f"     Remediation: {deficiency['remediation']}")
        print()
    
    print("✅ PASSED REQUIREMENTS:")
    for req in result3['passed_requirements']:
        print(f"  ✓ {req['requirement']}: {req['current_value']}")
    print()
    
    print("=" * 80)
    print("ASSESSMENT SUMMARY")
    print("=" * 80)
    print(f"Total devices assessed: 3")
    print(f"Compatible devices: 0")
    print(f"Incompatible devices: 3")
    print(f"Compatibility rate: 0.0%")
    print()
    print("COMMON FAILURE REASONS:")
    print("1. CPU Generation: Intel 6th gen and below, AMD Ryzen 2000 series")
    print("2. TPM Version: TPM 1.2 instead of required TPM 2.0")
    print("3. Secure Boot: Not available or disabled")
    print("4. Memory: Less than 4GB RAM")
    print("5. Storage: Less than 64GB available space")
    print()
    print("REMEDIATION ACTIONS:")
    print("- Hardware upgrades required for CPU, TPM, and Secure Boot issues")
    print("- BIOS/UEFI updates may enable TPM 2.0 and Secure Boot")
    print("- Memory and storage upgrades for insufficient resources")
    print("=" * 80)

if __name__ == "__main__":
    demonstrate_failed_assessments()
