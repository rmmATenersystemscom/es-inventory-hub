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
        # This is a simplified parser - may need adjustment based on actual format
        lines = volumes_text.split('\n')
        for line in lines:
            if 'GB' in line or 'TB' in line:
                # Extract numbers and convert to GB
                numbers = re.findall(r'(\d+(?:\.\d+)?)', line)
                for num in numbers:
                    if 'TB' in line:
                        total_gb += float(num) * 1024  # Convert TB to GB
                    else:
                        total_gb += float(num)
    except Exception as e:
        logger.warning(f"Error parsing volumes: {e}")
    
    return total_gb


def assess_windows_11_24h2_capability(device_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess Windows 11 24H2 capability based on device hardware data
    
    Input fields required:
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
    """Get all Windows devices that need assessment"""
    try:
        # Get Windows devices (desktops and laptops only) from today's snapshot
        query = text("""
        SELECT 
            ds.id,
            ds.hostname,
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
            ds.display_name
        FROM device_snapshot ds
        JOIN vendor v ON ds.vendor_id = v.id
        JOIN device_type dt ON ds.device_type_id = dt.id
        WHERE v.name = 'Ninja'
        AND ds.snapshot_date = CURRENT_DATE
        AND ds.os_name ILIKE '%windows%'
        AND dt.code IN ('Desktop', 'Laptop')
        """)
        
        result = session.execute(query)
        devices = []
        
        for row in result:
            device_data = {
                'id': row.id,
                'hostname': row.hostname,
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
                'display_name': row.display_name
            }
            devices.append(device_data)
        
        return devices
        
    except Exception as e:
        logger.error(f"Error getting Windows devices: {e}")
        return []


def update_device_assessment(session, device_id: int, assessment_result: Dict[str, Any]) -> bool:
    """Update device with assessment result"""
    try:
        # Convert verdict to boolean
        capable = None
        if assessment_result['verdict'] == 'Yes':
            capable = True
        elif assessment_result['verdict'] == 'No':
            capable = False
        # None for insufficient data or errors
        
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
            
            for device in devices:
                try:
                    logger.info(f"Assessing device: {device['hostname']} ({device['organization_name']})")
                    
                    # Perform assessment
                    assessment_result = assess_windows_11_24h2_capability(device)
                    
                    # Update database
                    if update_device_assessment(session, device['id'], assessment_result):
                        assessed_count += 1
                        
                        if assessment_result['verdict'] == 'Yes':
                            compatible_count += 1
                            logger.info(f"✓ {device['hostname']} - Compatible")
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
            logger.info(f"  - Compatibility rate: {(compatible_count/assessed_count*100):.1f}%" if assessed_count > 0 else "  - No devices assessed")
            
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
