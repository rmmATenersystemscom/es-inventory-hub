#!/usr/bin/env python3
"""
QuickBooks Web Connector (QBWC) SOAP Service

Implements the QBWC protocol to sync financial data from QuickBooks Desktop
to the QBR dashboard. The Web Connector polls this service periodically.

Protocol Flow:
1. authenticate() - Validates credentials, returns session ticket
2. sendRequestXML() - Returns QBXML queries (P&L, employees)
3. receiveResponseXML() - Parses QB response, stores metrics
4. closeConnection() - Cleans up session

This implementation uses manual SOAP handling with lxml instead of spyne
for better Python 3.12 compatibility.
"""

import os
import re
import uuid
import logging
import bcrypt
from datetime import datetime, date, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import List, Dict, Optional, Any, Tuple

from lxml import etree

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

import sys
sys.path.insert(0, '/opt/es-inventory-hub')

from common.db import session_scope
from storage.schema import (
    QBWCSyncSession, QBWCAccountMapping, QBWCSyncHistory,
    QBRAuditLog, QBRMetricsMonthly, Vendor
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# SOAP Namespaces
SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'
QBWC_NS = 'http://developer.intuit.com/'
NSMAP = {
    'soap': SOAP_NS,
    'qb': QBWC_NS
}


# Load configuration
def load_config():
    """Load QBWC configuration from environment"""
    env_file = '/opt/shared-secrets/api-secrets.env'
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_config()

# QBWC Configuration
QBWC_USERNAME = os.getenv('QBWC_USERNAME', 'enersystems_qbr')
QBWC_PASSWORD_HASH = os.getenv('QBWC_PASSWORD_HASH', '')
SESSION_TIMEOUT_MINUTES = 30


def log_audit(user_email: str, action: str, success: bool, resource: str = None,
              details: dict = None, ip_address: str = None, user_agent: str = None,
              failure_reason: str = None):
    """Log access attempt to audit log for compliance"""
    try:
        with session_scope() as session:
            audit_entry = QBRAuditLog(
                user_email=user_email,
                action=action,
                success=success,
                resource=resource,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason=failure_reason
            )
            session.add(audit_entry)
            session.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""
    if not hashed_password:
        logger.warning("No password hash configured for QBWC")
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_periods_to_sync() -> List[str]:
    """
    Get list of periods (YYYY-MM) to sync.
    Returns all months from January 2025 to current month.
    """
    periods = []
    start_date = date(2025, 1, 1)
    current_date = date.today()

    current = start_date
    while current <= current_date:
        periods.append(current.strftime('%Y-%m'))
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return periods


def get_synced_periods(session_db, organization_id: int = 1) -> set:
    """Get set of periods already synced for this organization"""
    result = session_db.execute(
        select(QBWCSyncHistory.period_start)
        .where(QBWCSyncHistory.organization_id == organization_id)
        .where(QBWCSyncHistory.sync_type == 'profit_loss')
        .distinct()
    )
    return {row[0].strftime('%Y-%m') for row in result.fetchall()}


def build_pl_query(start_date: str, end_date: str) -> str:
    """Build QBXML Profit & Loss Detail query"""
    return f'''<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
  <QBXMLMsgsRq onError="continueOnError">
    <GeneralDetailReportQueryRq>
      <GeneralDetailReportType>ProfitAndLossDetail</GeneralDetailReportType>
      <DisplayReport>false</DisplayReport>
      <ReportPeriod>
        <FromReportDate>{start_date}</FromReportDate>
        <ToReportDate>{end_date}</ToReportDate>
      </ReportPeriod>
      <ReportDetailLevelFilter>All</ReportDetailLevelFilter>
      <SummarizeColumnsBy>TotalOnly</SummarizeColumnsBy>
    </GeneralDetailReportQueryRq>
  </QBXMLMsgsRq>
</QBXML>'''


def build_employee_query() -> str:
    """Build QBXML Employee count query"""
    return '''<?xml version="1.0" encoding="utf-8"?>
<?qbxml version="16.0"?>
<QBXML>
  <QBXMLMsgsRq onError="continueOnError">
    <EmployeeQueryRq>
      <ActiveStatus>ActiveOnly</ActiveStatus>
      <IncludeRetElement>Name</IncludeRetElement>
      <IncludeRetElement>IsActive</IncludeRetElement>
    </EmployeeQueryRq>
  </QBXMLMsgsRq>
</QBXML>'''


def parse_pl_response(qbxml_response: str) -> Dict[str, Decimal]:
    """
    Parse Profit & Loss response into account name -> balance dict.
    """
    accounts = {}

    try:
        # Remove XML declaration if present for parsing
        if qbxml_response.startswith('<?xml'):
            qbxml_response = qbxml_response.split('?>', 1)[-1].strip()

        root = etree.fromstring(qbxml_response.encode('utf-8'))

        # Find all data rows in the report
        for data_row in root.findall('.//DataRow'):
            account_name = None
            balance = None

            # Extract account name from RowData
            row_data = data_row.find('.//RowData')
            if row_data is not None:
                account_name = row_data.get('value')

            # Extract balance from ColData
            for col_data in data_row.findall('.//ColData'):
                col_id = col_data.get('colID')
                value = col_data.get('value', '')

                if value and col_id not in ['1']:
                    try:
                        clean_value = value.replace(',', '').replace('$', '').strip()
                        if clean_value and clean_value not in ['-', '']:
                            balance = Decimal(clean_value)
                    except:
                        pass

            if account_name and balance is not None:
                accounts[account_name] = balance

        # Also parse TextRow for totals
        for text_row in root.findall('.//TextRow'):
            row_type = text_row.get('rowType')
            if row_type == 'TextRow':
                value = text_row.get('value', '')
                if 'Total' in value or 'Net' in value:
                    for col_data in text_row.findall('.//ColData'):
                        col_value = col_data.get('value', '')
                        try:
                            clean_value = col_value.replace(',', '').replace('$', '').strip()
                            if clean_value and clean_value not in ['-', '']:
                                accounts[value] = Decimal(clean_value)
                        except:
                            pass

        logger.info(f"Parsed {len(accounts)} accounts from P&L response")

    except Exception as e:
        logger.error(f"Error parsing P&L response: {e}")

    return accounts


def parse_employee_response(qbxml_response: str) -> int:
    """Parse employee query response and return count of active employees"""
    count = 0

    try:
        if qbxml_response.startswith('<?xml'):
            qbxml_response = qbxml_response.split('?>', 1)[-1].strip()

        root = etree.fromstring(qbxml_response.encode('utf-8'))
        employees = root.findall('.//EmployeeRet')
        count = len(employees)
        logger.info(f"Parsed {count} employees from response")

    except Exception as e:
        logger.error(f"Error parsing employee response: {e}")

    return count


def matches_pattern(account_name: str, pattern: str, match_type: str) -> bool:
    """Check if account name matches the given pattern"""
    account_lower = account_name.lower()
    pattern_clean = pattern.replace('%', '').lower()

    if match_type == 'exact':
        return account_lower == pattern_clean
    elif match_type == 'contains':
        return pattern_clean in account_lower
    elif match_type == 'regex':
        try:
            return bool(re.search(pattern, account_name, re.IGNORECASE))
        except:
            return False
    return False


def calculate_qbr_metrics(parsed_accounts: Dict[str, Decimal],
                          mappings: List[QBWCAccountMapping]) -> Dict[str, Decimal]:
    """Apply account mappings to calculate QBR metric values."""
    metrics = defaultdict(Decimal)

    for account_name, balance in parsed_accounts.items():
        for mapping in mappings:
            if not mapping.is_active:
                continue
            if matches_pattern(account_name, mapping.qb_account_pattern, mapping.match_type):
                metrics[mapping.qbr_metric_key] += balance
                logger.debug(f"Mapped '{account_name}' ({balance}) -> {mapping.qbr_metric_key}")
                break

    # Calculate totals
    metrics['total_revenue'] = (
        metrics.get('nrr', Decimal('0')) +
        metrics.get('mrr', Decimal('0')) +
        metrics.get('orr', Decimal('0')) +
        metrics.get('product_sales', Decimal('0')) +
        metrics.get('misc_revenue', Decimal('0'))
    )

    metrics['total_expenses'] = (
        metrics.get('employee_expense', Decimal('0')) +
        metrics.get('owner_comp_taxes', Decimal('0')) +
        metrics.get('owner_comp', Decimal('0')) +
        metrics.get('product_cogs', Decimal('0')) +
        metrics.get('other_expenses', Decimal('0'))
    )

    metrics['net_profit'] = metrics['total_revenue'] - metrics['total_expenses']

    return dict(metrics)


def store_qbr_metrics(organization_id: int, period: str, metrics: Dict[str, Decimal],
                      vendor_id: int = None) -> int:
    """Store calculated metrics in qbr_metrics_monthly table."""
    count = 0

    with session_scope() as session:
        if vendor_id is None:
            vendor = session.query(Vendor).filter_by(name='QuickBooks').first()
            if not vendor:
                vendor = Vendor(name='QuickBooks')
                session.add(vendor)
                session.flush()
            vendor_id = vendor.id

        for metric_name, metric_value in metrics.items():
            if metric_value == 0:
                continue

            stmt = pg_insert(QBRMetricsMonthly).values(
                period=period,
                organization_id=organization_id,
                vendor_id=vendor_id,
                metric_name=metric_name,
                metric_value=metric_value,
                data_source='quickbooks',
                collected_at=datetime.utcnow(),
                notes='Synced via QuickBooks Web Connector'
            )

            stmt = stmt.on_conflict_do_update(
                constraint='uq_metrics_monthly_period_metric_org_vendor',
                set_={
                    'metric_value': stmt.excluded.metric_value,
                    'data_source': 'quickbooks',
                    'collected_at': stmt.excluded.collected_at,
                    'updated_at': datetime.utcnow()
                }
            )

            session.execute(stmt)
            count += 1

        session.commit()

    logger.info(f"Stored {count} metrics for period {period}")
    return count


# ==============================================================================
# SOAP Request/Response Handling
# ==============================================================================

def extract_soap_method(soap_xml: bytes) -> Tuple[str, Dict[str, str]]:
    """
    Extract SOAP method name and parameters from request.

    Returns:
        Tuple of (method_name, {param_name: param_value})
    """
    try:
        root = etree.fromstring(soap_xml)

        # Find the Body element
        body = root.find('.//{%s}Body' % SOAP_NS)
        if body is None:
            return None, {}

        # The first child of Body is the method element
        for child in body:
            method_name = etree.QName(child).localname

            # Extract parameters
            params = {}
            for param in child:
                param_name = etree.QName(param).localname
                params[param_name] = param.text or ''

            return method_name, params

    except Exception as e:
        logger.error(f"Error parsing SOAP request: {e}")
        return None, {}


def build_soap_response(method_name: str, result_values: List[str]) -> bytes:
    """
    Build SOAP response XML for QBWC methods.

    Args:
        method_name: Name of the SOAP method (e.g., 'authenticate')
        result_values: List of string values to return

    Returns:
        SOAP response XML as bytes
    """
    # Build response XML
    envelope = etree.Element('{%s}Envelope' % SOAP_NS, nsmap={'soap': SOAP_NS})
    body = etree.SubElement(envelope, '{%s}Body' % SOAP_NS)

    response_elem = etree.SubElement(body, '{%s}%sResponse' % (QBWC_NS, method_name),
                                     nsmap={None: QBWC_NS})
    result_elem = etree.SubElement(response_elem, '{%s}%sResult' % (QBWC_NS, method_name))

    if method_name == 'authenticate':
        # authenticate returns an array of strings
        for value in result_values:
            string_elem = etree.SubElement(result_elem, '{%s}string' % QBWC_NS)
            string_elem.text = value
    else:
        # Other methods return a single value
        result_elem.text = str(result_values[0]) if result_values else ''

    return etree.tostring(envelope, xml_declaration=True, encoding='utf-8')


def build_soap_fault(fault_code: str, fault_string: str) -> bytes:
    """Build a SOAP Fault response"""
    envelope = etree.Element('{%s}Envelope' % SOAP_NS, nsmap={'soap': SOAP_NS})
    body = etree.SubElement(envelope, '{%s}Body' % SOAP_NS)
    fault = etree.SubElement(body, '{%s}Fault' % SOAP_NS)

    faultcode = etree.SubElement(fault, 'faultcode')
    faultcode.text = fault_code

    faultstring = etree.SubElement(fault, 'faultstring')
    faultstring.text = fault_string

    return etree.tostring(envelope, xml_declaration=True, encoding='utf-8')


# ==============================================================================
# QBWC Protocol Methods
# ==============================================================================

def handle_authenticate(params: Dict[str, str]) -> List[str]:
    """
    Handle authenticate SOAP method.

    Returns:
        List of strings: [ticket, status, delay, min_update]
    """
    username = params.get('strUserName', '')
    password = params.get('strPassword', '')

    logger.info(f"QBWC authenticate called for user: {username}")

    # Validate credentials
    if username != QBWC_USERNAME:
        logger.warning(f"Invalid QBWC username: {username}")
        log_audit(
            user_email=username or 'unknown',
            action='qbwc_auth',
            success=False,
            failure_reason='invalid_username'
        )
        return ['', 'nvu']

    if not verify_password(password, QBWC_PASSWORD_HASH):
        logger.warning(f"Invalid QBWC password for user: {username}")
        log_audit(
            user_email=username,
            action='qbwc_auth',
            success=False,
            failure_reason='invalid_password'
        )
        return ['', 'nvu']

    # Check if there's work to do
    periods_to_sync = get_periods_to_sync()

    with session_scope() as session:
        synced_periods = get_synced_periods(session)

    pending_periods = [p for p in periods_to_sync if p not in synced_periods]

    if not pending_periods:
        logger.info("No pending periods to sync")
        log_audit(
            user_email=username,
            action='qbwc_auth',
            success=True,
            details={'status': 'no_work'}
        )
        return ['', 'none']

    # Create session
    ticket = str(uuid.uuid4())

    with session_scope() as session:
        total_queries = len(pending_periods) + 1  # P&L per month + employees

        sync_session = QBWCSyncSession(
            ticket=ticket,
            organization_id=1,
            status='active',
            queries_total=total_queries,
            queries_completed=0
        )
        session.add(sync_session)
        session.commit()

    logger.info(f"Created QBWC session {ticket} with {len(pending_periods)} periods to sync")
    log_audit(
        user_email=username,
        action='qbwc_auth',
        success=True,
        details={'ticket': ticket, 'pending_periods': len(pending_periods)}
    )

    return [ticket, '']


def handle_send_request_xml(params: Dict[str, str]) -> str:
    """Handle sendRequestXML SOAP method."""
    ticket = params.get('ticket', '')
    company_file = params.get('strCompanyFileName', '')

    logger.info(f"QBWC sendRequestXML called for ticket: {ticket}")

    with session_scope() as session:
        sync_session = session.query(QBWCSyncSession).filter_by(ticket=ticket).first()
        if not sync_session:
            logger.error(f"Invalid session ticket: {ticket}")
            return ''

        if sync_session.status != 'active':
            logger.info(f"Session {ticket} is not active")
            return ''

        if company_file:
            sync_session.company_file = company_file

        synced_periods = get_synced_periods(session, sync_session.organization_id)
        periods_to_sync = get_periods_to_sync()
        pending_periods = [p for p in periods_to_sync if p not in synced_periods]

        if pending_periods:
            period = pending_periods[0]
            year, month = map(int, period.split('-'))
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)

            sync_session.current_query_type = 'profit_loss'
            sync_session.current_period = period
            session.commit()

            query = build_pl_query(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            logger.info(f"Sending P&L query for period {period}")
            return query

        employee_synced = session.query(QBWCSyncHistory).filter(
            QBWCSyncHistory.session_id == sync_session.id,
            QBWCSyncHistory.sync_type == 'employees'
        ).first()

        if not employee_synced:
            sync_session.current_query_type = 'employees'
            sync_session.current_period = date.today().strftime('%Y-%m')
            session.commit()

            logger.info("Sending employee query")
            return build_employee_query()

        logger.info(f"All queries completed for session {ticket}")
        return ''


def handle_receive_response_xml(params: Dict[str, str]) -> str:
    """Handle receiveResponseXML SOAP method."""
    ticket = params.get('ticket', '')
    response = params.get('response', '')
    hresult = params.get('hresult', '')
    message = params.get('message', '')

    logger.info(f"QBWC receiveResponseXML called for ticket: {ticket}")

    with session_scope() as session:
        sync_session = session.query(QBWCSyncSession).filter_by(ticket=ticket).first()
        if not sync_session:
            logger.error(f"Invalid session ticket: {ticket}")
            return '-1'

        if hresult and int(hresult) < 0:
            logger.error(f"QuickBooks returned error: {hresult} - {message}")
            sync_session.error_message = f"{hresult}: {message}"
            sync_session.status = 'failed'
            session.commit()

            log_audit(
                user_email='qbwc',
                action='qbwc_sync',
                success=False,
                details={'ticket': ticket, 'hresult': hresult},
                failure_reason=message
            )
            return '-1'

        query_type = sync_session.current_query_type
        period = sync_session.current_period
        metrics_updated = 0

        if query_type == 'profit_loss':
            parsed_accounts = parse_pl_response(response)

            mappings = session.query(QBWCAccountMapping).filter(
                QBWCAccountMapping.organization_id == sync_session.organization_id,
                QBWCAccountMapping.is_active == True
            ).all()

            metrics = calculate_qbr_metrics(parsed_accounts, mappings)
            session.commit()

            metrics_updated = store_qbr_metrics(
                sync_session.organization_id,
                period,
                metrics
            )

            with session_scope() as session2:
                sync_session2 = session2.query(QBWCSyncSession).filter_by(ticket=ticket).first()

                year, month = map(int, period.split('-'))
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)

                history = QBWCSyncHistory(
                    session_id=sync_session2.id,
                    organization_id=sync_session2.organization_id,
                    sync_type='profit_loss',
                    period_start=start_date,
                    period_end=end_date,
                    raw_response=response[:50000] if response else None,
                    parsed_data={'accounts': len(parsed_accounts), 'metrics': metrics_updated},
                    metrics_updated=metrics_updated
                )
                session2.add(history)
                sync_session2.queries_completed += 1
                session2.commit()

            logger.info(f"Processed P&L for {period}: {metrics_updated} metrics")

        elif query_type == 'employees':
            employee_count = parse_employee_response(response)
            session.commit()

            if employee_count > 0:
                metrics_updated = store_qbr_metrics(
                    sync_session.organization_id,
                    period,
                    {'employees': Decimal(str(employee_count))}
                )

            with session_scope() as session2:
                sync_session2 = session2.query(QBWCSyncSession).filter_by(ticket=ticket).first()

                today = date.today()
                history = QBWCSyncHistory(
                    session_id=sync_session2.id,
                    organization_id=sync_session2.organization_id,
                    sync_type='employees',
                    period_start=today,
                    period_end=today,
                    raw_response=response[:50000] if response else None,
                    parsed_data={'employee_count': employee_count},
                    metrics_updated=1 if employee_count > 0 else 0
                )
                session2.add(history)
                sync_session2.queries_completed += 1
                session2.commit()

            logger.info(f"Processed employees: {employee_count}")

        # Calculate progress
        with session_scope() as session3:
            sync_session3 = session3.query(QBWCSyncSession).filter_by(ticket=ticket).first()
            if sync_session3.queries_total > 0:
                progress = int((sync_session3.queries_completed / sync_session3.queries_total) * 100)
            else:
                progress = 100

            logger.info(f"Sync progress: {progress}%")
            return str(progress)


def handle_get_last_error(params: Dict[str, str]) -> str:
    """Handle getLastError SOAP method."""
    ticket = params.get('ticket', '')
    logger.info(f"QBWC getLastError called for ticket: {ticket}")

    with session_scope() as session:
        sync_session = session.query(QBWCSyncSession).filter_by(ticket=ticket).first()
        if sync_session and sync_session.error_message:
            return sync_session.error_message

    return ''


def handle_close_connection(params: Dict[str, str]) -> str:
    """Handle closeConnection SOAP method."""
    ticket = params.get('ticket', '')
    logger.info(f"QBWC closeConnection called for ticket: {ticket}")

    with session_scope() as session:
        sync_session = session.query(QBWCSyncSession).filter_by(ticket=ticket).first()
        if sync_session:
            if sync_session.status == 'active':
                sync_session.status = 'completed'
            sync_session.completed_at = datetime.utcnow()
            session.commit()

            log_audit(
                user_email='qbwc',
                action='qbwc_sync',
                success=True,
                details={
                    'ticket': ticket,
                    'queries_completed': sync_session.queries_completed,
                    'status': sync_session.status
                }
            )

    return 'OK'


def process_qbwc_request(soap_request: bytes) -> bytes:
    """
    Process a QBWC SOAP request and return the response.

    Args:
        soap_request: Raw SOAP XML request bytes

    Returns:
        SOAP XML response bytes
    """
    method_name, params = extract_soap_method(soap_request)

    if not method_name:
        return build_soap_fault('soap:Client', 'Could not parse SOAP request')

    logger.info(f"Processing QBWC method: {method_name}")

    try:
        if method_name == 'authenticate':
            result = handle_authenticate(params)
            return build_soap_response('authenticate', result)

        elif method_name == 'sendRequestXML':
            result = handle_send_request_xml(params)
            return build_soap_response('sendRequestXML', [result])

        elif method_name == 'receiveResponseXML':
            result = handle_receive_response_xml(params)
            return build_soap_response('receiveResponseXML', [result])

        elif method_name == 'getLastError':
            result = handle_get_last_error(params)
            return build_soap_response('getLastError', [result])

        elif method_name == 'closeConnection':
            result = handle_close_connection(params)
            return build_soap_response('closeConnection', [result])

        else:
            logger.warning(f"Unknown QBWC method: {method_name}")
            return build_soap_fault('soap:Client', f'Unknown method: {method_name}')

    except Exception as e:
        logger.error(f"Error processing QBWC request: {e}", exc_info=True)
        return build_soap_fault('soap:Server', f'Internal error: {str(e)}')


def get_wsdl() -> bytes:
    """
    Generate WSDL for the QBWC service.

    The WSDL defines the SOAP interface that the QuickBooks Web Connector expects.
    """
    wsdl = '''<?xml version="1.0" encoding="utf-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
             xmlns:tns="http://developer.intuit.com/"
             xmlns:s="http://www.w3.org/2001/XMLSchema"
             targetNamespace="http://developer.intuit.com/"
             name="QBWebConnectorSvc">

  <types>
    <s:schema targetNamespace="http://developer.intuit.com/">
      <s:element name="authenticate">
        <s:complexType>
          <s:sequence>
            <s:element name="strUserName" type="s:string" minOccurs="0"/>
            <s:element name="strPassword" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="authenticateResponse">
        <s:complexType>
          <s:sequence>
            <s:element name="authenticateResult" type="tns:ArrayOfString" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="ArrayOfString">
        <s:sequence>
          <s:element name="string" type="s:string" nillable="true" minOccurs="0" maxOccurs="unbounded"/>
        </s:sequence>
      </s:complexType>
      <s:element name="sendRequestXML">
        <s:complexType>
          <s:sequence>
            <s:element name="ticket" type="s:string" minOccurs="0"/>
            <s:element name="strHCPResponse" type="s:string" minOccurs="0"/>
            <s:element name="strCompanyFileName" type="s:string" minOccurs="0"/>
            <s:element name="qbXMLCountry" type="s:string" minOccurs="0"/>
            <s:element name="qbXMLMajorVers" type="s:int"/>
            <s:element name="qbXMLMinorVers" type="s:int"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="sendRequestXMLResponse">
        <s:complexType>
          <s:sequence>
            <s:element name="sendRequestXMLResult" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="receiveResponseXML">
        <s:complexType>
          <s:sequence>
            <s:element name="ticket" type="s:string" minOccurs="0"/>
            <s:element name="response" type="s:string" minOccurs="0"/>
            <s:element name="hresult" type="s:string" minOccurs="0"/>
            <s:element name="message" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="receiveResponseXMLResponse">
        <s:complexType>
          <s:sequence>
            <s:element name="receiveResponseXMLResult" type="s:int"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="getLastError">
        <s:complexType>
          <s:sequence>
            <s:element name="ticket" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="getLastErrorResponse">
        <s:complexType>
          <s:sequence>
            <s:element name="getLastErrorResult" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="closeConnection">
        <s:complexType>
          <s:sequence>
            <s:element name="ticket" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="closeConnectionResponse">
        <s:complexType>
          <s:sequence>
            <s:element name="closeConnectionResult" type="s:string" minOccurs="0"/>
          </s:sequence>
        </s:complexType>
      </s:element>
    </s:schema>
  </types>

  <message name="authenticateSoapIn">
    <part name="parameters" element="tns:authenticate"/>
  </message>
  <message name="authenticateSoapOut">
    <part name="parameters" element="tns:authenticateResponse"/>
  </message>
  <message name="sendRequestXMLSoapIn">
    <part name="parameters" element="tns:sendRequestXML"/>
  </message>
  <message name="sendRequestXMLSoapOut">
    <part name="parameters" element="tns:sendRequestXMLResponse"/>
  </message>
  <message name="receiveResponseXMLSoapIn">
    <part name="parameters" element="tns:receiveResponseXML"/>
  </message>
  <message name="receiveResponseXMLSoapOut">
    <part name="parameters" element="tns:receiveResponseXMLResponse"/>
  </message>
  <message name="getLastErrorSoapIn">
    <part name="parameters" element="tns:getLastError"/>
  </message>
  <message name="getLastErrorSoapOut">
    <part name="parameters" element="tns:getLastErrorResponse"/>
  </message>
  <message name="closeConnectionSoapIn">
    <part name="parameters" element="tns:closeConnection"/>
  </message>
  <message name="closeConnectionSoapOut">
    <part name="parameters" element="tns:closeConnectionResponse"/>
  </message>

  <portType name="QBWebConnectorSvcSoap">
    <operation name="authenticate">
      <input message="tns:authenticateSoapIn"/>
      <output message="tns:authenticateSoapOut"/>
    </operation>
    <operation name="sendRequestXML">
      <input message="tns:sendRequestXMLSoapIn"/>
      <output message="tns:sendRequestXMLSoapOut"/>
    </operation>
    <operation name="receiveResponseXML">
      <input message="tns:receiveResponseXMLSoapIn"/>
      <output message="tns:receiveResponseXMLSoapOut"/>
    </operation>
    <operation name="getLastError">
      <input message="tns:getLastErrorSoapIn"/>
      <output message="tns:getLastErrorSoapOut"/>
    </operation>
    <operation name="closeConnection">
      <input message="tns:closeConnectionSoapIn"/>
      <output message="tns:closeConnectionSoapOut"/>
    </operation>
  </portType>

  <binding name="QBWebConnectorSvcSoap" type="tns:QBWebConnectorSvcSoap">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="authenticate">
      <soap:operation soapAction="http://developer.intuit.com/authenticate" style="document"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
    <operation name="sendRequestXML">
      <soap:operation soapAction="http://developer.intuit.com/sendRequestXML" style="document"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
    <operation name="receiveResponseXML">
      <soap:operation soapAction="http://developer.intuit.com/receiveResponseXML" style="document"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
    <operation name="getLastError">
      <soap:operation soapAction="http://developer.intuit.com/getLastError" style="document"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
    <operation name="closeConnection">
      <soap:operation soapAction="http://developer.intuit.com/closeConnection" style="document"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>

  <service name="QBWebConnectorSvc">
    <port name="QBWebConnectorSvcSoap" binding="tns:QBWebConnectorSvcSoap">
      <soap:address location="https://db-api.enersystems.com:5400/api/qbwc"/>
    </port>
  </service>
</definitions>'''

    return wsdl.encode('utf-8')


# Export
__all__ = ['process_qbwc_request', 'get_wsdl', 'log_audit']
