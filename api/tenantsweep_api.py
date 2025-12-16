"""
TenantSweep API Endpoints

Provides REST API endpoints for M365 Tenant Sweep security audit results:
1. Creating and managing audit runs
2. Recording individual security findings
3. Bulk importing findings
4. Retrieving audit data with filtering
5. Exporting findings to CSV
"""

import sys
import csv
import io
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import unquote

from flask import Blueprint, jsonify, request, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import authentication decorator
from api.auth_microsoft import require_auth

from storage.schema import TenantSweepAudit, TenantSweepFinding

# Create Blueprint for TenantSweep API
tenantsweep_api = Blueprint('tenantsweep_api', __name__)


# Valid values for validation
VALID_AUDIT_STATUSES = ['running', 'completed', 'failed']
VALID_SEVERITIES = ['Critical', 'High', 'Medium', 'Low', 'Info']
VALID_FINDING_STATUSES = ['pass', 'fail', 'warning', 'error']


def validate_severity(severity: str) -> bool:
    """Validate severity value (case-insensitive)."""
    return severity.lower() in [s.lower() for s in VALID_SEVERITIES]


def normalize_severity(severity: str) -> str:
    """Normalize severity to proper case."""
    mapping = {s.lower(): s for s in VALID_SEVERITIES}
    return mapping.get(severity.lower(), severity)


def validate_finding_status(status: str) -> bool:
    """Validate finding status value."""
    return status.lower() in VALID_FINDING_STATUSES


def audit_to_dict(audit: TenantSweepAudit, include_findings: bool = False) -> Dict:
    """Convert audit model to dictionary."""
    result = {
        "id": audit.id,
        "tenant_name": audit.tenant_name,
        "tenant_id": audit.tenant_id,
        "status": audit.status,
        "started_at": audit.started_at.isoformat() if audit.started_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
        "summary": audit.summary,
        "error_message": audit.error_message,
        "initiated_by": audit.initiated_by,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
    }

    if include_findings:
        result["findings"] = [finding_to_dict(f) for f in audit.findings]
        result["findings_count"] = len(audit.findings)

    return result


def finding_to_dict(finding: TenantSweepFinding) -> Dict:
    """Convert finding model to dictionary."""
    return {
        "id": finding.id,
        "audit_id": finding.audit_id,
        "check_id": finding.check_id,
        "check_name": finding.check_name,
        "severity": finding.severity,
        "status": finding.status,
        "current_value": finding.current_value,
        "expected_value": finding.expected_value,
        "details": finding.details,
        "recommendation": finding.recommendation,
        "created_at": finding.created_at.isoformat() if finding.created_at else None,
    }


# ============================================================================
# POST /api/tenantsweep/audits - Create audit run
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits', methods=['POST'])
@require_auth
def create_audit():
    """
    Create a new tenant sweep audit run.

    Request Body:
        {
            "tenant_name": "Contoso Ltd",
            "tenant_id": "12345678-abcd-1234-abcd-1234567890ab",
            "initiated_by": "user@enersystems.com"  (optional)
        }

    Returns:
        JSON response with created audit details
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body is required",
                "status": 400
            }
        }), 400

    tenant_name = data.get('tenant_name')
    tenant_id = data.get('tenant_id')
    initiated_by = data.get('initiated_by')

    if not tenant_name or not tenant_id:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_FIELDS",
                "message": "Both tenant_name and tenant_id are required",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            audit = TenantSweepAudit(
                tenant_name=tenant_name,
                tenant_id=tenant_id,
                status='running',
                initiated_by=initiated_by
            )
            session.add(audit)
            session.flush()  # Get the ID before commit

            result = audit_to_dict(audit)
            session.commit()

            return jsonify({
                "success": True,
                "data": result
            }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# PATCH /api/tenantsweep/audits/<audit_id> - Update audit (complete/fail)
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits/<int:audit_id>', methods=['PATCH'])
@require_auth
def update_audit(audit_id: int):
    """
    Update an audit run (mark as completed or failed).

    Request Body:
        {
            "status": "completed",  // or "failed"
            "summary": {"Critical": 1, "High": 2, "Medium": 3, "Low": 0, "Info": 5},
            "error_message": null  // or error details if failed
        }

    Returns:
        JSON response with updated audit details
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body is required",
                "status": 400
            }
        }), 400

    status = data.get('status')
    if status and status not in VALID_AUDIT_STATUSES:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_STATUS",
                "message": f"Status must be one of: {', '.join(VALID_AUDIT_STATUSES)}",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            audit = session.query(TenantSweepAudit).filter(
                TenantSweepAudit.id == audit_id
            ).first()

            if not audit:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Audit with ID {audit_id} not found",
                        "status": 404
                    }
                }), 404

            # Update fields if provided
            if status:
                audit.status = status
                if status in ['completed', 'failed']:
                    audit.completed_at = datetime.utcnow()

            if 'summary' in data:
                audit.summary = data['summary']

            if 'error_message' in data:
                audit.error_message = data['error_message']

            session.commit()

            return jsonify({
                "success": True,
                "data": audit_to_dict(audit)
            }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# POST /api/tenantsweep/audits/<audit_id>/findings - Add single finding
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits/<int:audit_id>/findings', methods=['POST'])
@require_auth
def add_finding(audit_id: int):
    """
    Add a single finding to an audit.

    Request Body:
        {
            "check_id": "MFA_ENFORCEMENT",
            "check_name": "MFA Enforcement",
            "severity": "Critical",
            "status": "fail",
            "current_value": "MFA not enforced",
            "expected_value": "MFA required for all users",
            "details": {"users_without_mfa": 45},
            "recommendation": "Enable MFA via Conditional Access policy"
        }

    Returns:
        JSON response with created finding details
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body is required",
                "status": 400
            }
        }), 400

    # Validate required fields
    check_id = data.get('check_id')
    check_name = data.get('check_name')
    severity = data.get('severity')
    status = data.get('status')

    if not check_id or not check_name or not severity or not status:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_FIELDS",
                "message": "check_id, check_name, severity, and status are required",
                "status": 400
            }
        }), 400

    if not validate_severity(severity):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_SEVERITY",
                "message": f"Severity must be one of: {', '.join(VALID_SEVERITIES)}",
                "status": 400
            }
        }), 400

    if not validate_finding_status(status):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_STATUS",
                "message": f"Status must be one of: {', '.join(VALID_FINDING_STATUSES)}",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            # Verify audit exists
            audit = session.query(TenantSweepAudit).filter(
                TenantSweepAudit.id == audit_id
            ).first()

            if not audit:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Audit with ID {audit_id} not found",
                        "status": 404
                    }
                }), 404

            finding = TenantSweepFinding(
                audit_id=audit_id,
                check_id=check_id,
                check_name=check_name,
                severity=normalize_severity(severity),
                status=status.lower(),
                current_value=data.get('current_value'),
                expected_value=data.get('expected_value'),
                details=data.get('details'),
                recommendation=data.get('recommendation')
            )
            session.add(finding)
            session.flush()

            result = finding_to_dict(finding)
            session.commit()

            return jsonify({
                "success": True,
                "data": result
            }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# POST /api/tenantsweep/audits/<audit_id>/findings/bulk - Bulk add findings
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits/<int:audit_id>/findings/bulk', methods=['POST'])
@require_auth
def bulk_add_findings(audit_id: int):
    """
    Bulk add findings to an audit.

    Request Body:
        {
            "findings": [
                {
                    "check_id": "MFA_ENFORCEMENT",
                    "check_name": "MFA Enforcement",
                    "severity": "Critical",
                    "status": "fail",
                    ...
                },
                ...
            ]
        }

    Returns:
        JSON response with count of created findings
    """
    from api.api_server import get_session

    data = request.get_json()

    if not data or 'findings' not in data:
        return jsonify({
            "success": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Request body must include 'findings' array",
                "status": 400
            }
        }), 400

    findings_data = data['findings']
    if not isinstance(findings_data, list):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_DATA",
                "message": "'findings' must be an array",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            # Verify audit exists
            audit = session.query(TenantSweepAudit).filter(
                TenantSweepAudit.id == audit_id
            ).first()

            if not audit:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Audit with ID {audit_id} not found",
                        "status": 404
                    }
                }), 404

            created_count = 0
            errors = []

            for idx, finding_data in enumerate(findings_data):
                check_id = finding_data.get('check_id')
                check_name = finding_data.get('check_name')
                severity = finding_data.get('severity')
                status = finding_data.get('status')

                # Validate each finding
                if not check_id or not check_name or not severity or not status:
                    errors.append(f"Finding {idx}: check_id, check_name, severity, and status are required")
                    continue

                if not validate_severity(severity):
                    errors.append(f"Finding {idx}: invalid severity '{severity}'")
                    continue

                if not validate_finding_status(status):
                    errors.append(f"Finding {idx}: invalid status '{status}'")
                    continue

                finding = TenantSweepFinding(
                    audit_id=audit_id,
                    check_id=check_id,
                    check_name=check_name,
                    severity=normalize_severity(severity),
                    status=status.lower(),
                    current_value=finding_data.get('current_value'),
                    expected_value=finding_data.get('expected_value'),
                    details=finding_data.get('details'),
                    recommendation=finding_data.get('recommendation')
                )
                session.add(finding)
                created_count += 1

            session.commit()

            response = {
                "success": True,
                "data": {
                    "audit_id": audit_id,
                    "created_count": created_count,
                    "total_submitted": len(findings_data)
                }
            }

            if errors:
                response["data"]["errors"] = errors

            return jsonify(response), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/tenantsweep/audits/<audit_id> - Get audit with findings
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits/<int:audit_id>', methods=['GET'])
@require_auth
def get_audit(audit_id: int):
    """
    Get an audit with its findings.

    Query Parameters:
        include_findings (optional): Include findings in response (default: true)
        severity (optional): Filter findings by severity

    Returns:
        JSON response with audit details and findings
    """
    from api.api_server import get_session

    include_findings = request.args.get('include_findings', 'true').lower() == 'true'
    severity_filter = request.args.get('severity', '')

    if severity_filter and not validate_severity(severity_filter):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_SEVERITY",
                "message": f"Severity must be one of: {', '.join(VALID_SEVERITIES)}",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            audit = session.query(TenantSweepAudit).filter(
                TenantSweepAudit.id == audit_id
            ).first()

            if not audit:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Audit with ID {audit_id} not found",
                        "status": 404
                    }
                }), 404

            result = audit_to_dict(audit, include_findings=False)

            if include_findings:
                # Query findings with optional severity filter
                findings_query = session.query(TenantSweepFinding).filter(
                    TenantSweepFinding.audit_id == audit_id
                )

                if severity_filter:
                    findings_query = findings_query.filter(
                        TenantSweepFinding.severity == normalize_severity(severity_filter)
                    )

                findings = findings_query.order_by(
                    TenantSweepFinding.severity,
                    TenantSweepFinding.check_id
                ).all()

                result["findings"] = [finding_to_dict(f) for f in findings]
                result["findings_count"] = len(findings)

                # Generate severity summary
                severity_summary = {}
                for sev in VALID_SEVERITIES:
                    count = sum(1 for f in findings if f.severity == sev)
                    if count > 0:
                        severity_summary[sev] = count
                result["severity_summary"] = severity_summary

            return jsonify({
                "success": True,
                "data": result
            }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/tenantsweep/audits - List audits (with filters)
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits', methods=['GET'])
@require_auth
def list_audits():
    """
    List all audits with optional filtering.

    Query Parameters:
        tenant_name (optional): Filter by tenant name (partial match)
        tenant_id (optional): Filter by exact tenant ID
        status (optional): Filter by audit status
        limit (optional): Maximum number of results (default: 50, max: 200)
        offset (optional): Offset for pagination (default: 0)

    Returns:
        JSON response with list of audits
    """
    from api.api_server import get_session

    tenant_name = request.args.get('tenant_name', '')
    tenant_id = request.args.get('tenant_id', '')
    status = request.args.get('status', '')
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = int(request.args.get('offset', 0))

    if status and status not in VALID_AUDIT_STATUSES:
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_STATUS",
                "message": f"Status must be one of: {', '.join(VALID_AUDIT_STATUSES)}",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            query = session.query(TenantSweepAudit)

            # Apply filters
            if tenant_name:
                query = query.filter(TenantSweepAudit.tenant_name.ilike(f'%{tenant_name}%'))

            if tenant_id:
                query = query.filter(TenantSweepAudit.tenant_id == tenant_id)

            if status:
                query = query.filter(TenantSweepAudit.status == status)

            # Get total count before pagination
            total_count = query.count()

            # Apply ordering and pagination
            audits = query.order_by(
                desc(TenantSweepAudit.started_at)
            ).offset(offset).limit(limit).all()

            return jsonify({
                "success": True,
                "data": {
                    "audits": [audit_to_dict(a) for a in audits],
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset
                }
            }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/tenantsweep/tenants/<tenant_name>/latest-audit - Get latest audit
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/tenants/<tenant_name>/latest-audit', methods=['GET'])
@require_auth
def get_latest_audit_for_tenant(tenant_name: str):
    """
    Get the latest completed audit for a specific tenant.

    Path Parameters:
        tenant_name: Name of the tenant (URL encoded if contains special chars)

    Query Parameters:
        include_findings (optional): Include findings in response (default: true)

    Returns:
        JSON response with latest audit details
    """
    from api.api_server import get_session

    tenant_name = unquote(tenant_name)
    include_findings = request.args.get('include_findings', 'true').lower() == 'true'

    try:
        with get_session() as session:
            # Get latest completed audit for tenant
            audit = session.query(TenantSweepAudit).filter(
                TenantSweepAudit.tenant_name == tenant_name,
                TenantSweepAudit.status == 'completed'
            ).order_by(
                desc(TenantSweepAudit.started_at)
            ).first()

            if not audit:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"No completed audit found for tenant '{tenant_name}'",
                        "status": 404
                    }
                }), 404

            result = audit_to_dict(audit, include_findings=False)

            if include_findings:
                findings = session.query(TenantSweepFinding).filter(
                    TenantSweepFinding.audit_id == audit.id
                ).order_by(
                    TenantSweepFinding.severity,
                    TenantSweepFinding.check_id
                ).all()

                result["findings"] = [finding_to_dict(f) for f in findings]
                result["findings_count"] = len(findings)

                # Generate severity summary
                severity_summary = {}
                for sev in VALID_SEVERITIES:
                    count = sum(1 for f in findings if f.severity == sev)
                    if count > 0:
                        severity_summary[sev] = count
                result["severity_summary"] = severity_summary

            return jsonify({
                "success": True,
                "data": result
            }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# ============================================================================
# GET /api/tenantsweep/audits/<audit_id>/export/csv - Export findings to CSV
# ============================================================================

@tenantsweep_api.route('/api/tenantsweep/audits/<int:audit_id>/export/csv', methods=['GET'])
@require_auth
def export_findings_csv(audit_id: int):
    """
    Export audit findings to CSV format.

    Query Parameters:
        severity (optional): Filter by severity

    Returns:
        CSV file download
    """
    from api.api_server import get_session

    severity_filter = request.args.get('severity', '')

    if severity_filter and not validate_severity(severity_filter):
        return jsonify({
            "success": False,
            "error": {
                "code": "INVALID_SEVERITY",
                "message": f"Severity must be one of: {', '.join(VALID_SEVERITIES)}",
                "status": 400
            }
        }), 400

    try:
        with get_session() as session:
            audit = session.query(TenantSweepAudit).filter(
                TenantSweepAudit.id == audit_id
            ).first()

            if not audit:
                return jsonify({
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Audit with ID {audit_id} not found",
                        "status": 404
                    }
                }), 404

            # Query findings with optional severity filter
            findings_query = session.query(TenantSweepFinding).filter(
                TenantSweepFinding.audit_id == audit_id
            )

            if severity_filter:
                findings_query = findings_query.filter(
                    TenantSweepFinding.severity == normalize_severity(severity_filter)
                )

            findings = findings_query.order_by(
                TenantSweepFinding.severity,
                TenantSweepFinding.check_id
            ).all()

            # Generate CSV content
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Check ID', 'Check Name', 'Severity', 'Status', 'Current Value',
                'Expected Value', 'Recommendation', 'Details', 'Created At'
            ])

            # Write data rows
            for finding in findings:
                details_str = ''
                if finding.details:
                    details_str = json.dumps(finding.details)

                writer.writerow([
                    finding.check_id,
                    finding.check_name,
                    finding.severity,
                    finding.status,
                    finding.current_value or '',
                    finding.expected_value or '',
                    finding.recommendation or '',
                    details_str,
                    finding.created_at.isoformat() if finding.created_at else ''
                ])

            # Create response
            output.seek(0)
            safe_tenant_name = audit.tenant_name.replace(' ', '_').replace('/', '-')
            date_str = audit.started_at.strftime('%Y%m%d') if audit.started_at else 'unknown'
            filename = f"tenantsweep_{safe_tenant_name}_{date_str}.csv"

            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'text/csv; charset=utf-8'
                }
            )

    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e),
                "status": 500
            }
        }), 500


# Export blueprint
__all__ = ['tenantsweep_api']
