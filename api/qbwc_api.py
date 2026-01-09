#!/usr/bin/env python3
"""
QuickBooks Web Connector API Blueprint

Provides Flask integration for the QBWC SOAP service and REST endpoints
for managing account mappings and viewing sync status.
"""

import os
import sys
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, Response, session

# Add project root to path
sys.path.insert(0, '/opt/es-inventory-hub')

from common.db import session_scope
from storage.schema import (
    QBWCSyncSession, QBWCAccountMapping, QBWCSyncHistory, QBRAuditLog
)
from api.auth_microsoft import require_auth
from api.qbwc_service import process_qbwc_request, get_wsdl, log_audit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
qbwc_api = Blueprint('qbwc_api', __name__)


def get_client_ip():
    """Get the client IP address from the request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


# ==============================================================================
# SOAP Endpoint - QuickBooks Web Connector
# ==============================================================================

@qbwc_api.route('/api/qbwc', methods=['POST'])
def qbwc_soap_endpoint():
    """
    SOAP endpoint for QuickBooks Web Connector.

    This endpoint receives SOAP requests from the QBWC and processes them.
    """
    logger.info(f"QBWC SOAP request received from {get_client_ip()}")

    try:
        # Get request body
        soap_request = request.data

        # Process the SOAP request
        soap_response = process_qbwc_request(soap_request)

        return Response(
            soap_response,
            content_type='text/xml; charset=utf-8'
        )

    except Exception as e:
        logger.error(f"QBWC SOAP error: {e}", exc_info=True)
        return Response(
            f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Server</faultcode>
      <faultstring>Internal server error: {str(e)}</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>''',
            status=500,
            content_type='text/xml; charset=utf-8'
        )


@qbwc_api.route('/api/qbwc', methods=['GET'])
def qbwc_wsdl():
    """
    Return WSDL for the QBWC service.
    The Web Connector uses this to understand the service interface.
    """
    return Response(
        get_wsdl(),
        content_type='text/xml; charset=utf-8'
    )


# ==============================================================================
# REST Endpoints - Status and Configuration
# ==============================================================================

@qbwc_api.route('/api/qbwc/status', methods=['GET'])
@require_auth
def get_qbwc_status():
    """
    Get QBWC sync status and last sync time.
    """
    user_email = session.get('user_email', 'anonymous')
    log_audit(
        user_email=user_email,
        action='qbwc_status_view',
        success=True,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent')
    )

    with session_scope() as db_session:
        # Get most recent completed sync
        last_sync = db_session.query(QBWCSyncSession).filter(
            QBWCSyncSession.status == 'completed'
        ).order_by(QBWCSyncSession.completed_at.desc()).first()

        # Get currently active sync if any
        active_sync = db_session.query(QBWCSyncSession).filter(
            QBWCSyncSession.status == 'active'
        ).first()

        # Get recent sync history
        recent_syncs = db_session.query(QBWCSyncSession).order_by(
            QBWCSyncSession.created_at.desc()
        ).limit(10).all()

        return jsonify({
            'success': True,
            'data': {
                'last_sync': {
                    'completed_at': last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None,
                    'queries_completed': last_sync.queries_completed if last_sync else 0,
                    'status': last_sync.status if last_sync else None
                } if last_sync else None,
                'active_sync': {
                    'ticket': active_sync.ticket,
                    'started_at': active_sync.created_at.isoformat(),
                    'progress': (active_sync.queries_completed / active_sync.queries_total * 100)
                               if active_sync and active_sync.queries_total > 0 else 0,
                    'current_query_type': active_sync.current_query_type,
                    'current_period': active_sync.current_period
                } if active_sync else None,
                'recent_syncs': [{
                    'id': s.id,
                    'status': s.status,
                    'created_at': s.created_at.isoformat(),
                    'completed_at': s.completed_at.isoformat() if s.completed_at else None,
                    'queries_total': s.queries_total,
                    'queries_completed': s.queries_completed,
                    'error_message': s.error_message
                } for s in recent_syncs]
            }
        })


@qbwc_api.route('/api/qbwc/mappings', methods=['GET'])
@require_auth
def get_account_mappings():
    """
    Get list of account mappings.
    """
    user_email = session.get('user_email', 'anonymous')
    log_audit(
        user_email=user_email,
        action='qbwc_mappings_view',
        success=True,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent')
    )

    organization_id = request.args.get('organization_id', 1, type=int)

    with session_scope() as db_session:
        mappings = db_session.query(QBWCAccountMapping).filter(
            QBWCAccountMapping.organization_id == organization_id
        ).order_by(
            QBWCAccountMapping.qbr_metric_key,
            QBWCAccountMapping.qb_account_pattern
        ).all()

        return jsonify({
            'success': True,
            'data': [{
                'id': m.id,
                'organization_id': m.organization_id,
                'qbr_metric_key': m.qbr_metric_key,
                'qb_account_pattern': m.qb_account_pattern,
                'match_type': m.match_type,
                'is_active': m.is_active,
                'notes': m.notes,
                'created_at': m.created_at.isoformat() if m.created_at else None,
                'updated_at': m.updated_at.isoformat() if m.updated_at else None
            } for m in mappings]
        })


@qbwc_api.route('/api/qbwc/mappings', methods=['POST'])
@require_auth
def create_account_mapping():
    """
    Create a new account mapping.
    """
    user_email = session.get('user_email', 'anonymous')

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    required_fields = ['qbr_metric_key', 'qb_account_pattern']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

    with session_scope() as db_session:
        mapping = QBWCAccountMapping(
            organization_id=data.get('organization_id', 1),
            qbr_metric_key=data['qbr_metric_key'],
            qb_account_pattern=data['qb_account_pattern'],
            match_type=data.get('match_type', 'contains'),
            is_active=data.get('is_active', True),
            notes=data.get('notes')
        )
        db_session.add(mapping)
        db_session.commit()

        log_audit(
            user_email=user_email,
            action='qbwc_mapping_create',
            success=True,
            details={'mapping_id': mapping.id, 'metric_key': data['qbr_metric_key']},
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent')
        )

        return jsonify({
            'success': True,
            'data': {
                'id': mapping.id,
                'qbr_metric_key': mapping.qbr_metric_key,
                'qb_account_pattern': mapping.qb_account_pattern
            }
        }), 201


@qbwc_api.route('/api/qbwc/mappings/<int:mapping_id>', methods=['PUT'])
@require_auth
def update_account_mapping(mapping_id):
    """
    Update an existing account mapping.
    """
    user_email = session.get('user_email', 'anonymous')

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    with session_scope() as db_session:
        mapping = db_session.query(QBWCAccountMapping).filter_by(id=mapping_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404

        # Update fields
        if 'qbr_metric_key' in data:
            mapping.qbr_metric_key = data['qbr_metric_key']
        if 'qb_account_pattern' in data:
            mapping.qb_account_pattern = data['qb_account_pattern']
        if 'match_type' in data:
            mapping.match_type = data['match_type']
        if 'is_active' in data:
            mapping.is_active = data['is_active']
        if 'notes' in data:
            mapping.notes = data['notes']

        mapping.updated_at = datetime.utcnow()
        db_session.commit()

        log_audit(
            user_email=user_email,
            action='qbwc_mapping_update',
            success=True,
            details={'mapping_id': mapping_id},
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent')
        )

        return jsonify({
            'success': True,
            'data': {
                'id': mapping.id,
                'qbr_metric_key': mapping.qbr_metric_key,
                'qb_account_pattern': mapping.qb_account_pattern
            }
        })


@qbwc_api.route('/api/qbwc/mappings/<int:mapping_id>', methods=['DELETE'])
@require_auth
def delete_account_mapping(mapping_id):
    """
    Delete an account mapping.
    """
    user_email = session.get('user_email', 'anonymous')

    with session_scope() as db_session:
        mapping = db_session.query(QBWCAccountMapping).filter_by(id=mapping_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404

        db_session.delete(mapping)
        db_session.commit()

        log_audit(
            user_email=user_email,
            action='qbwc_mapping_delete',
            success=True,
            details={'mapping_id': mapping_id},
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent')
        )

        return jsonify({'success': True})


@qbwc_api.route('/api/qbwc/history', methods=['GET'])
@require_auth
def get_sync_history():
    """
    Get sync history with optional filtering.
    """
    user_email = session.get('user_email', 'anonymous')
    log_audit(
        user_email=user_email,
        action='qbwc_history_view',
        success=True,
        ip_address=get_client_ip(),
        user_agent=request.headers.get('User-Agent')
    )

    organization_id = request.args.get('organization_id', 1, type=int)
    limit = request.args.get('limit', 50, type=int)

    with session_scope() as db_session:
        history = db_session.query(QBWCSyncHistory).filter(
            QBWCSyncHistory.organization_id == organization_id
        ).order_by(QBWCSyncHistory.created_at.desc()).limit(limit).all()

        return jsonify({
            'success': True,
            'data': [{
                'id': h.id,
                'session_id': h.session_id,
                'sync_type': h.sync_type,
                'period_start': h.period_start.isoformat() if h.period_start else None,
                'period_end': h.period_end.isoformat() if h.period_end else None,
                'parsed_data': h.parsed_data,
                'metrics_updated': h.metrics_updated,
                'created_at': h.created_at.isoformat() if h.created_at else None
            } for h in history]
        })


# ==============================================================================
# Debug Endpoints (TEMPORARY - for account mapping setup)
# ==============================================================================

@qbwc_api.route('/api/qbwc/debug/clear-period/<period>', methods=['DELETE'])
def debug_clear_period(period):
    """
    TEMPORARY DEBUG: Clear sync history for a specific period to force re-sync.
    Period format: YYYY-MM (e.g., 2025-01)
    """
    try:
        year, month = map(int, period.split('-'))
        from datetime import date
        period_start = date(year, month, 1)
    except:
        return jsonify({'success': False, 'error': 'Invalid period format. Use YYYY-MM'}), 400

    with session_scope() as db_session:
        deleted = db_session.query(QBWCSyncHistory).filter(
            QBWCSyncHistory.period_start == period_start,
            QBWCSyncHistory.sync_type == 'profit_loss'
        ).delete()
        db_session.commit()

    return jsonify({
        'success': True,
        'message': f'Cleared {deleted} sync record(s) for period {period}. Run QBWC Update to re-sync.'
    })


@qbwc_api.route('/api/qbwc/debug/raw-response/<period>', methods=['GET'])
def debug_raw_response(period):
    """
    TEMPORARY DEBUG: View raw QB response for a period.
    Period format: YYYY-MM (e.g., 2025-01)
    """
    try:
        year, month = map(int, period.split('-'))
        from datetime import date
        period_start = date(year, month, 1)
    except:
        return jsonify({'success': False, 'error': 'Invalid period format. Use YYYY-MM'}), 400

    with session_scope() as db_session:
        history = db_session.query(QBWCSyncHistory).filter(
            QBWCSyncHistory.period_start == period_start,
            QBWCSyncHistory.sync_type == 'profit_loss'
        ).order_by(QBWCSyncHistory.created_at.desc()).first()

        if not history:
            return jsonify({'success': False, 'error': f'No sync history for period {period}'}), 404

        return jsonify({
            'success': True,
            'period': period,
            'parsed_data': history.parsed_data,
            'metrics_updated': history.metrics_updated,
            'raw_response_length': len(history.raw_response) if history.raw_response else 0,
            'raw_response_preview': history.raw_response[:5000] if history.raw_response else None
        })


@qbwc_api.route('/api/qbwc/debug/add-mapping', methods=['POST'])
def debug_add_mapping():
    """
    TEMPORARY DEBUG: Add account mapping without auth.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    required = ['qbr_metric_key', 'qb_account_pattern']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing: {field}'}), 400

    with session_scope() as db_session:
        # Check if mapping already exists
        existing = db_session.query(QBWCAccountMapping).filter_by(
            qbr_metric_key=data['qbr_metric_key'],
            qb_account_pattern=data['qb_account_pattern']
        ).first()

        if existing:
            return jsonify({'success': False, 'error': 'Mapping already exists'}), 409

        mapping = QBWCAccountMapping(
            organization_id=data.get('organization_id', 1),
            qbr_metric_key=data['qbr_metric_key'],
            qb_account_pattern=data['qb_account_pattern'],
            match_type=data.get('match_type', 'contains'),
            is_active=True,
            notes=data.get('notes', 'Added via debug endpoint')
        )
        db_session.add(mapping)
        db_session.commit()

        return jsonify({
            'success': True,
            'mapping': {
                'id': mapping.id,
                'qbr_metric_key': mapping.qbr_metric_key,
                'qb_account_pattern': mapping.qb_account_pattern
            }
        }), 201


@qbwc_api.route('/api/qbwc/debug/list-mappings', methods=['GET'])
def debug_list_mappings():
    """TEMPORARY DEBUG: List all mappings without auth."""
    with session_scope() as db_session:
        mappings = db_session.query(QBWCAccountMapping).filter_by(is_active=True).order_by(
            QBWCAccountMapping.qbr_metric_key
        ).all()

        return jsonify({
            'success': True,
            'count': len(mappings),
            'mappings': [{
                'id': m.id,
                'qbr_metric_key': m.qbr_metric_key,
                'qb_account_pattern': m.qb_account_pattern,
                'match_type': m.match_type
            } for m in mappings]
        })


@qbwc_api.route('/api/qbwc/debug/reparse/<period>', methods=['GET'])
def debug_reparse(period):
    """
    TEMPORARY DEBUG: Re-parse raw QB response for a period with updated parser.
    Shows all parsed accounts/subtotals to verify expense totals.
    """
    from api.qbwc_service import parse_pl_response

    try:
        year, month = map(int, period.split('-'))
        from datetime import date
        period_start = date(year, month, 1)
    except:
        return jsonify({'success': False, 'error': 'Invalid period format. Use YYYY-MM'}), 400

    with session_scope() as db_session:
        history = db_session.query(QBWCSyncHistory).filter(
            QBWCSyncHistory.period_start == period_start,
            QBWCSyncHistory.sync_type == 'profit_loss'
        ).order_by(QBWCSyncHistory.created_at.desc()).first()

        if not history or not history.raw_response:
            return jsonify({'success': False, 'error': f'No raw response for period {period}'}), 404

        # Re-parse with updated parser
        parsed = parse_pl_response(history.raw_response)

        # Separate subtotals from individual accounts
        subtotals = {k: str(v) for k, v in parsed.items() if 'Total' in k}
        individual = {k: str(v) for k, v in parsed.items() if 'Total' not in k}

        return jsonify({
            'success': True,
            'period': period,
            'subtotals': subtotals,
            'subtotals_count': len(subtotals),
            'individual_accounts_count': len(individual),
            'key_expense_totals': {
                'Total 6300': subtotals.get('Total 6300 · Payroll Expenses', 'NOT FOUND'),
                'Total 5000': subtotals.get('Total 5000 · Cost of Goods Sold', 'NOT FOUND'),
                'Total COGS': subtotals.get('Total COGS', 'NOT FOUND'),
                'Total Expenses': subtotals.get('Total Expenses', 'NOT FOUND')
            }
        })


@qbwc_api.route('/api/qbwc/debug/deactivate-mapping/<int:mapping_id>', methods=['POST'])
def debug_deactivate_mapping(mapping_id):
    """TEMPORARY DEBUG: Deactivate a mapping by ID."""
    with session_scope() as db_session:
        mapping = db_session.query(QBWCAccountMapping).filter_by(id=mapping_id).first()
        if not mapping:
            return jsonify({'success': False, 'error': 'Mapping not found'}), 404

        mapping.is_active = False
        db_session.commit()

        return jsonify({
            'success': True,
            'message': f'Deactivated mapping {mapping_id}: {mapping.qb_account_pattern} -> {mapping.qbr_metric_key}'
        })


@qbwc_api.route('/api/qbwc/debug/deactivate-by-metric/<metric_key>', methods=['POST'])
def debug_deactivate_by_metric(metric_key):
    """TEMPORARY DEBUG: Deactivate all mappings for a specific metric key."""
    with session_scope() as db_session:
        mappings = db_session.query(QBWCAccountMapping).filter_by(
            qbr_metric_key=metric_key,
            is_active=True
        ).all()

        count = 0
        for mapping in mappings:
            mapping.is_active = False
            count += 1

        db_session.commit()

        return jsonify({
            'success': True,
            'message': f'Deactivated {count} mappings for metric key: {metric_key}'
        })


# Export blueprint
__all__ = ['qbwc_api']
