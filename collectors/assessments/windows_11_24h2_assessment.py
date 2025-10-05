#!/usr/bin/env python3
"""
Windows 11 24H2 Capability Assessment Script

This script assesses Windows devices for Windows 11 24H2 compatibility based on:
- 64-bit OS requirement
- Memory requirement (≥ 4 GiB)
- Storage requirement (≥ 64 GB)
- CPU support (Intel 8th gen+, AMD Zen 2+, Qualcomm Snapdragon)
- TPM 2.0 requirement
- Secure Boot requirement

The script runs after the Ninja collector completes and updates the database
with assessment results.
"""

import os
import sys
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

# Add the project root to the Python path
sys.path.insert(0, '/opt/es-inventory-hub')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from common.config import get_dsn

# Database connection
DSN = get_dsn()
engine = create_engine(DSN)
Session = sessionmaker(bind=engine)

def get_session():
    """Get database session."""
    return Session()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/es-inventory-hub/logs/windows_11_24h2_assessment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def assess_cpu_support(cpu_model: str) -> Tuple[bool, str]:
    """Assess CPU support for Windows 11 24H2"""
    if not cpu_model or cpu_model == 'N/A':
        return False, "CPU model not available"
    
    cpu_lower = cpu_model.lower()
    
    # Intel CPU support (8th gen or newer)
    if 'intel' in cpu_lower:
        # Check for generation indicators
        if any(gen in cpu_lower for gen in ['8th gen', '9th gen', '10th gen', '11th gen', '12th gen', '13th gen', '14th gen']):
            return True, "Intel generation meets requirement"
        
        # Check for Intel Core Ultra series (newer than 14th gen)
        if 'ultra' in cpu_lower:
            return True, "Intel Core Ultra series meets requirement"
        
        # Parse CPU model number
        # Look for patterns like i7-8565U, i5-1185G7, etc.
        match = re.search(r'i[3579]-(\d{4})', cpu_model)
        if match:
            cpu_number = int(match.group(1))
            if cpu_number >= 8000:  # 8th gen or newer
                return True, f"Intel CPU {cpu_number} meets requirement"
            else:
                return False, f"Intel CPU {cpu_number} is below minimum requirement (8th gen)"
    
    # AMD CPU support (Zen 2+ = Ryzen 3000/4000/5000+)
    elif 'amd' in cpu_lower or 'ryzen' in cpu_lower:
        if any(gen in cpu_lower for gen in ['3000', '4000', '5000', '6000', '7000']):
            return True, "AMD Ryzen generation meets requirement"
        elif '2000' in cpu_lower:
            return False, "AMD Ryzen 2000 series may not be fully supported"
        else:
            return False, "AMD CPU generation below minimum requirement"
    
    # Qualcomm/ARM support
    elif 'qualcomm' in cpu_lower or 'snapdragon' in cpu_lower:
        return True, "Qualcomm Snapdragon meets requirement"
    
    return False, f"Unsupported CPU: {cpu_model}"


def is_tpm_2_0(tpm_version: str) -> bool:
    """Check if TPM version is 2.0 or higher"""
    if not tpm_version or tpm_version == 'N/A':
        return False
    
    # Parse TPM version string (e.g., "2.0, 1.38, 0")
    try:
        versions = [v.strip() for v in tpm_version.split(',')]
        # Remove "0" entries and check for "2.0"
        versions = [v for v in versions if v != '0']
        return '2.0' in versions
    except:
        return False


def calculate_storage_from_volumes(volumes_text: str) -> float:
    """Calculate total storage from volumes text"""
    if not volumes_text:
        return 0.0
    
    total_gb = 0.0
    try:
        # Parse volumes text to extract storage sizes
        # Format: "C: 2793.4GB, D: 500.0GB"
        volumes = volumes_text.split(', ')
        for volume in volumes:
            if 'GB' in volume:
                # Extract number before GB
                match = re.search(r'(\d+(?:\.\d+)?)GB', volume)
                if match:
                    total_gb += float(match.group(1))
            elif 'TB' in volume:
                # Extract number before TB and convert to GB
                match = re.search(r'(\d+(?:\.\d+)?)TB', volume)
                if match:
                    total_gb += float(match.group(1)) * 1024
    except Exception as e:
        logger.warning(f"Error parsing volumes: {e}")
    
    return total_gb


def is_windows_11_24h2_installed(os_name: str, os_release_id: str = None, os_build: str = None) -> bool:
    """Check if the device already has Windows 11 24H2 installed"""
    print(f"DEBUG: is_windows_11_24h2_installed called with: os_name='{os_name}', os_release_id='{os_release_id}', os_build='{os_build}'")
    
    if not os_name:
        print("DEBUG: No OS name, returning False")
        return False
    
    os_lower = os_name.lower()
    print(f"DEBUG: OS name lower: '{os_lower}'")
    
    # Check if it's Windows 11
    if 'windows 11' not in os_lower:
        print("DEBUG: Not Windows 11, returning False")
        return False
    
    print("DEBUG: Is Windows 11, checking version...")
    
    # Method 1: Check release ID if available
    if os_release_id and os_release_id.strip():
        print(f"DEBUG: Checking release ID: '{os_release_id}'")
        result = '24h2' in os_release_id.lower()
        print(f"DEBUG: Release ID check result: {result}")
        return result
    
    # Method 2: Check build number for Windows 11 24H2
    # Windows 11 24H2: Build 26100.x (based on actual API data)
    if os_build and os_build.strip():
        print(f"DEBUG: Checking build number: '{os_build}'")
        try:
            # Extract the major build number (e.g., "26100" -> 26100)
            build_parts = os_build.split('.')
            if len(build_parts) >= 1:
                major_build = int(build_parts[0])
                print(f"DEBUG: Major build number: {major_build}")
                # Windows 11 24H2 is build 26100.x
                result = major_build == 26100
                print(f"DEBUG: Build number check result: {result}")
                return result
        except (ValueError, IndexError) as e:
            print(f"DEBUG: Error parsing build number: {e}")
            # If we can't parse the build number, fall through to False
            pass
    
    print("DEBUG: No valid version info, returning False")
    # If we can't determine the version, assume it's not 24H2
    return False


def has_newer_windows_version(os_name: str, os_release_id: str = None, os_build: str = None) -> bool:
    """Check if the device has a newer Windows version than 24H2 (e.g., 25H2, 26H2, etc.)"""
    print(f"DEBUG: has_newer_windows_version called with: os_name='{os_name}', os_release_id='{os_release_id}', os_build='{os_build}'")
    
    if not os_name:
        print("DEBUG: No OS name, returning False")
        return False
    
    os_lower = os_name.lower()
    print(f"DEBUG: OS name lower: '{os_lower}'")
    
    # Check if it's Windows 11
    if 'windows 11' not in os_lower:
        print("DEBUG: Not Windows 11, returning False")
        return False
    
    print("DEBUG: Is Windows 11, checking for newer version...")
    
    # Method 1: Check release ID for newer versions
    if os_release_id and os_release_id.strip():
        print(f"DEBUG: Checking release ID: '{os_release_id}'")
        release_lower = os_release_id.lower()
        
        # Check for known newer versions
        newer_versions = ['25h2', '26h2', '27h2', '28h2', '29h2', '30h2']
        for version in newer_versions:
            if version in release_lower:
                print(f"DEBUG: Found newer version {version} in release ID")
                return True
        
        # Check for any version higher than 24H2 (e.g., 25H2, 26H2, etc.)
        # Extract year from release ID (e.g., "25H2" -> 25)
        import re
        version_match = re.search(r'(\d+)h2', release_lower)
        if version_match:
            year = int(version_match.group(1))
            if year > 24:  # Any year after 2024
                print(f"DEBUG: Found version year {year} which is newer than 24H2")
                return True
    
    # Method 2: Check build number for newer versions
    # Windows 11 24H2: Build 26100.x
    # Newer versions will have higher build numbers
    if os_build and os_build.strip():
        print(f"DEBUG: Checking build number: '{os_build}'")
        try:
            # Extract the major build number (e.g., "26100" -> 26100)
            build_parts = os_build.split('.')
            if len(build_parts) >= 1:
                major_build = int(build_parts[0])
                print(f"DEBUG: Major build number: {major_build}")
                # Windows 11 24H2 is build 26100.x, newer versions will be higher
                if major_build > 26100:
                    print(f"DEBUG: Build number {major_build} is newer than 24H2 (26100)")
                    return True
        except (ValueError, IndexError) as e:
            print(f"DEBUG: Error parsing build number: {e}")
            # If we can't parse the build number, fall through to False
            pass
    
    print("DEBUG: No newer version detected, returning False")
    return False


def is_windows_server(os_name: str) -> bool:
    """Check if the device is running Windows Server"""
    if not os_name:
        return False
    
    os_lower = os_name.lower()
    return 'server' in os_lower


def assess_windows_11_24h2_capability(device_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess Windows 11 24H2 capability based on device hardware data
    
    Input fields required:
    - os_name (string, e.g., "Windows 11 Professional")
    - os_architecture (string, e.g., "64-bit")
    - memory_gib (float, total RAM in GiB) 
    - volumes (string, storage information)
    - cpu_model (string, e.g., "Intel(R) Core(TM) i7-8565U")
    - has_tpm (bool)
    - tpm_enabled (bool) 
    - tpm_version (string, e.g., "2.0, 1.38, 0")
    - secure_boot_available (bool)
    - secure_boot_enabled (bool)
    """
    
    deficiencies = []
    passed_requirements = []
    verdict = "Yes"
    
    # Check if device already has Windows 11 24H2 installed
    os_name = device_data.get('os_name', '')
    os_release_id = device_data.get('os_release_id', '')
    os_build = device_data.get('os_build', '')
    
    # Debug logging
    print(f"DEBUG: Device {device_data.get('hostname', 'Unknown')} - OS: {os_name}, Release: '{os_release_id}', Build: '{os_build}'")
    
    is_24h2 = is_windows_11_24h2_installed(os_name, os_release_id, os_build)
    print(f"DEBUG: is_windows_11_24h2_installed returned: {is_24h2}")
    
    if is_24h2:
        print("DEBUG: Device has 24H2 - returning early with 'Already Installed' status")
        return {
            "verdict": "Yes",
            "deficiencies": [],
            "passed_requirements": [{
                "requirement": "Windows 11 24H2 Already Installed",
                "status": "PASS",
                "current_value": os_name,
                "reason": "Device already has Windows 11 24H2 installed"
            }],
            "assessment_date": datetime.utcnow().isoformat() + 'Z'
        }
    
    # Check if device has a newer Windows version than 24H2 (e.g., 25H2, 26H2, etc.)
    has_newer = has_newer_windows_version(os_name, os_release_id, os_build)
    print(f"DEBUG: has_newer_windows_version returned: {has_newer}")
    
    if has_newer:
        print("DEBUG: Device has newer Windows version - excluding from assessment")
        return {
            "verdict": "N/A",
            "deficiencies": [],
            "passed_requirements": [{
                "requirement": "Windows Version Check",
                "status": "EXCLUDED",
                "current_value": f"{os_name} ({os_release_id or os_build or 'Unknown version'})",
                "reason": "Device has a newer Windows version than 24H2 and is excluded from assessment"
            }],
            "assessment_date": datetime.utcnow().isoformat() + 'Z'
        }
    
    print("DEBUG: Device does not have 24H2 or newer version - continuing with hardware assessment")
    
    # Check if device is running Windows Server (assessment does not apply)
    if is_windows_server(os_name):
        return {
            "verdict": "N/A",
            "deficiencies": [],
            "passed_requirements": [{
                "requirement": "Windows Server OS",
                "status": "N/A",
                "current_value": os_name,
                "reason": "Windows Server operating systems are not assessed for Windows 11 24H2 compatibility"
            }],
            "assessment_date": datetime.utcnow().isoformat() + 'Z'
        }
    
    try:
        # 1. 64-bit OS requirement
        os_arch = device_data.get('os_architecture', '')
        if os_arch != '64-bit':
            deficiencies.append({
                "requirement": "64-bit OS",
                "status": "FAIL",
                "current_value": os_arch or 'Unknown',
                "required": "64-bit",
                "reason": "Operating system must be 64-bit",
                "remediation": "Reinstall with 64-bit Windows"
            })
            verdict = "No"
        else:
            passed_requirements.append({
                "requirement": "64-bit OS", 
                "status": "PASS",
                "current_value": os_arch
            })
        
        # 2. Memory requirement (≥ 4 GiB, 8 GiB recommended)
        memory_gib = device_data.get('memory_gib', 0)
        if memory_gib and memory_gib < 4:
            deficiencies.append({
                "requirement": "Memory",
                "status": "FAIL",
                "current_value": f"{memory_gib} GiB",
                "required": "≥ 4 GiB (8 GiB recommended)",
                "reason": f"Insufficient memory: {memory_gib} GiB < 4 GiB minimum",
                "remediation": "Add more RAM to meet minimum requirement"
            })
            verdict = "No"
        elif memory_gib and memory_gib >= 4:
            passed_requirements.append({
                "requirement": "Memory",
                "status": "PASS", 
                "current_value": f"{memory_gib} GiB",
                "required": "≥ 4 GiB"
            })
        else:
            deficiencies.append({
                "requirement": "Memory",
                "status": "INSUFFICIENT_DATA",
                "current_value": "Unknown",
                "required": "≥ 4 GiB",
                "reason": "Memory information not available",
                "remediation": "Ensure device is online and Ninja agent is reporting data"
            })
            verdict = "No"
        
        # 3. Storage requirement (≥ 64 GB)
        volumes_text = device_data.get('volumes', '')
        storage_gb = calculate_storage_from_volumes(volumes_text)
        
        if storage_gb > 0 and storage_gb < 64:
            deficiencies.append({
                "requirement": "Storage",
                "status": "FAIL",
                "current_value": f"{storage_gb:.1f} GB",
                "required": "≥ 64 GB",
                "reason": f"Insufficient storage: {storage_gb:.1f} GB < 64 GB minimum",
                "remediation": "Add more storage or free up space"
            })
            verdict = "No"
        elif storage_gb >= 64:
            passed_requirements.append({
                "requirement": "Storage",
                "status": "PASS",
                "current_value": f"{storage_gb:.1f} GB",
                "required": "≥ 64 GB"
            })
        else:
            deficiencies.append({
                "requirement": "Storage",
                "status": "INSUFFICIENT_DATA",
                "current_value": "Unknown",
                "required": "≥ 64 GB",
                "reason": "Storage information not available",
                "remediation": "Ensure device is online and Ninja agent is reporting data"
            })
            verdict = "No"
        
        # 4. CPU support requirement
        cpu_model = device_data.get('cpu_model', '')
        cpu_supported, cpu_reason = assess_cpu_support(cpu_model)
        if not cpu_supported:
            deficiencies.append({
                "requirement": "CPU Support",
                "status": "FAIL",
                "current_value": cpu_model or 'Unknown',
                "required": "Intel 8th gen+, AMD Zen 2+, or Qualcomm Snapdragon",
                "reason": cpu_reason,
                "remediation": "Hardware upgrade required - cannot be resolved via software"
            })
            verdict = "No"
        else:
            passed_requirements.append({
                "requirement": "CPU Support",
                "status": "PASS",
                "current_value": cpu_model
            })
        
        # 5. TPM 2.0 requirement
        tpm_has = device_data.get('has_tpm', False)
        tpm_enabled = device_data.get('tpm_enabled', False)
        tpm_version = device_data.get('tpm_version', '')
        
        if not tpm_has:
            deficiencies.append({
                "requirement": "TPM 2.0",
                "status": "FAIL",
                "current_value": "No TPM detected",
                "required": "TPM 2.0 present and enabled",
                "reason": "No TPM module detected on device",
                "remediation": "Enable TPM in BIOS/UEFI or hardware upgrade required"
            })
            verdict = "No"
        elif not tpm_enabled:
            deficiencies.append({
                "requirement": "TPM 2.0", 
                "status": "FAIL",
                "current_value": "TPM present but disabled",
                "required": "TPM 2.0 present and enabled",
                "reason": "TPM is present but not enabled",
                "remediation": "Enable TPM in BIOS/UEFI settings"
            })
            verdict = "No"
        elif not is_tpm_2_0(tpm_version):
            deficiencies.append({
                "requirement": "TPM 2.0",
                "status": "FAIL", 
                "current_value": f"TPM {tpm_version}",
                "required": "TPM 2.0",
                "reason": f"TPM version {tpm_version} is below minimum requirement of 2.0",
                "remediation": "BIOS/UEFI update may enable TPM 2.0, otherwise hardware upgrade required"
            })
            verdict = "No"
        else:
            passed_requirements.append({
                "requirement": "TPM 2.0",
                "status": "PASS",
                "current_value": f"TPM {tpm_version} enabled"
            })
        
        # 6. Secure Boot requirement
        secure_boot_available = device_data.get('secure_boot_available', False)
        secure_boot_enabled = device_data.get('secure_boot_enabled', False)
        
        if not secure_boot_available:
            deficiencies.append({
                "requirement": "Secure Boot",
                "status": "FAIL",
                "current_value": "Secure Boot not available",
                "required": "Secure Boot supported and enabled",
                "reason": "Secure Boot is not supported on this device",
                "remediation": "Hardware upgrade required - device does not support Secure Boot"
            })
            verdict = "No"
        elif not secure_boot_enabled:
            deficiencies.append({
                "requirement": "Secure Boot",
                "status": "FAIL",
                "current_value": "Secure Boot available but disabled", 
                "required": "Secure Boot supported and enabled",
                "reason": "Secure Boot is available but not enabled",
                "remediation": "Enable Secure Boot in BIOS/UEFI settings"
            })
            verdict = "No"
        else:
            passed_requirements.append({
                "requirement": "Secure Boot",
                "status": "PASS",
                "current_value": "Secure Boot enabled"
            })
        
    except Exception as e:
        logger.error(f"Error during assessment: {e}")
        deficiencies.append({
            "requirement": "Assessment Error",
            "status": "ERROR",
            "current_value": "Assessment failed",
            "required": "Complete assessment",
            "reason": f"Assessment script error: {str(e)}",
            "remediation": "Check logs and retry assessment"
        })
        verdict = "No"
    
    return {
        "verdict": verdict,
        "deficiencies": deficiencies,
        "passed_requirements": passed_requirements,
        "assessment_date": datetime.utcnow().isoformat() + 'Z'
    }


def get_windows_devices(session) -> List[Dict[str, Any]]:
    """Get all Windows devices that need assessment from the latest available data"""
    try:
        # Get Windows devices (desktops and laptops only) from the latest snapshot
        # Exclude Windows Server and non-Windows devices
        query = text("""
        SELECT
            ds.id,
            ds.hostname,
            ds.os_name,
            ds.os_architecture,
            ds.memory_gib,
            ds.volumes,
            ds.cpu_model,
            ds.has_tpm,
            ds.tpm_enabled,
            ds.tpm_version,
            ds.secure_boot_available,
            ds.secure_boot_enabled,
            ds.organization_name,
            ds.display_name,
            ds.os_release_id,
            ds.os_build
        FROM device_snapshot ds
        JOIN vendor v ON ds.vendor_id = v.id
        JOIN device_type dt ON ds.device_type_id = dt.id
        WHERE v.name = 'Ninja'
        AND ds.snapshot_date = (
            SELECT MAX(snapshot_date)
            FROM device_snapshot ds2
            JOIN vendor v2 ON ds2.vendor_id = v2.id
            WHERE v2.name = 'Ninja'
        )
        AND ds.os_name ILIKE '%windows%'
        AND ds.os_name NOT ILIKE '%server%'
        AND dt.code IN ('Desktop', 'Laptop', 'workstation')
        """)
        
        result = session.execute(query)
        devices = []
        
        for row in result:
            device_data = {
                'id': row.id,
                'hostname': row.hostname,
                'os_name': row.os_name,
                'os_architecture': row.os_architecture,
                'memory_gib': float(row.memory_gib) if row.memory_gib else None,
                'volumes': row.volumes,
                'cpu_model': row.cpu_model,
                'has_tpm': row.has_tpm,
                'tpm_enabled': row.tpm_enabled,
                'tpm_version': row.tpm_version,
                'secure_boot_available': row.secure_boot_available,
                'secure_boot_enabled': row.secure_boot_enabled,
                'organization_name': row.organization_name,
                'display_name': row.display_name,
                'os_release_id': row.os_release_id,
                'os_build': row.os_build
            }
            devices.append(device_data)
        
        # Log which snapshot date we're using
        if devices:
            # Get the snapshot date from the first device (they're all from the same date)
            snapshot_query = text("""
            SELECT MAX(snapshot_date) as latest_snapshot
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE v.name = 'Ninja'
            """)
            snapshot_result = session.execute(snapshot_query).fetchone()
            latest_snapshot = snapshot_result.latest_snapshot if snapshot_result else 'Unknown'
            logger.info(f"Using snapshot data from: {latest_snapshot}")
        
        return devices
        
    except Exception as e:
        logger.error(f"Error getting Windows devices: {e}")
        return []


def update_device_assessment(session, device_id: int, assessment_result: Dict[str, Any]) -> bool:
    """Update device with assessment result"""
    try:
        # Convert verdict to boolean - Updated logic for "Already Compatible" devices
        capable = None
        if assessment_result['verdict'] == 'Yes':
            # Check if it's "Already Compatible" (has 24H2) or "Compatible" (can be upgraded)
            if 'Windows 11 24H2 Already Installed' in str(assessment_result.get('passed_requirements', [])):
                capable = True  # Mark as capable since they already have 24H2
            else:
                capable = True  # Mark as capable since they can be upgraded
        elif assessment_result['verdict'] == 'No':
            capable = False
        # None for N/A (Windows Server), insufficient data, or errors
        
        update_query = text("""
        UPDATE device_snapshot 
        SET windows_11_24h2_capable = :capable,
            windows_11_24h2_deficiencies = :deficiencies
        WHERE id = :device_id
        """)
        
        session.execute(update_query, {
            'capable': capable,
            'deficiencies': json.dumps(assessment_result),
            'device_id': device_id
        })
        
        session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error updating device {device_id}: {e}")
        session.rollback()
        return False


def main():
    """Main assessment function"""
    logger.info("Starting Windows 11 24H2 capability assessment")
    
    try:
        with get_session() as session:
            # Get all Windows devices
            devices = get_windows_devices(session)
            logger.info(f"Found {len(devices)} Windows devices to assess")
            
            if not devices:
                logger.warning("No Windows devices found for assessment")
                return
            
            # Assess each device
            assessed_count = 0
            compatible_count = 0
            incompatible_count = 0
            already_installed_count = 0
            server_os_count = 0
            
            for device in devices:
                try:
                    logger.info(f"Assessing device: {device['hostname']} ({device['organization_name']}) - {device['os_name']}")
                    
                    # Perform assessment
                    assessment_result = assess_windows_11_24h2_capability(device)
                    
                    # Update database
                    if update_device_assessment(session, device['id'], assessment_result):
                        assessed_count += 1
                        
                        if assessment_result['verdict'] == 'Yes':
                            if 'Windows 11 24H2 Already Installed' in str(assessment_result.get('passed_requirements', [])):
                                already_installed_count += 1
                                logger.info(f"✓ {device['hostname']} - Already has Windows 11 24H2")
                            else:
                                compatible_count += 1
                                logger.info(f"✓ {device['hostname']} - Compatible")
                        elif assessment_result['verdict'] == 'N/A':
                            if 'Windows 11 24H2 Already Installed' in str(assessment_result.get('passed_requirements', [])):
                                already_installed_count += 1
                                logger.info(f"✓ {device['hostname']} - Already has Windows 11 24H2")
                            elif 'Windows Server OS' in str(assessment_result.get('passed_requirements', [])):
                                server_os_count += 1
                                logger.info(f"- {device['hostname']} - Windows Server (assessment not applicable)")
                        else:
                            incompatible_count += 1
                            logger.info(f"✗ {device['hostname']} - Incompatible ({len(assessment_result['deficiencies'])} issues)")
                    else:
                        logger.error(f"Failed to update assessment for {device['hostname']}")
                
                except Exception as e:
                    logger.error(f"Error assessing device {device.get('hostname', 'Unknown')}: {e}")
                    continue
            
            # Log summary
            logger.info(f"Assessment complete:")
            logger.info(f"  - Total devices assessed: {assessed_count}")
            logger.info(f"  - Compatible devices: {compatible_count}")
            logger.info(f"  - Incompatible devices: {incompatible_count}")
            logger.info(f"  - Already have Windows 11 24H2: {already_installed_count}")
            logger.info(f"  - Windows Server (N/A): {server_os_count}")
            logger.info(f"  - Compatibility rate: {(compatible_count/assessed_count*100):.1f}%" if assessed_count > 0 else "  - No devices assessed")
            
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
