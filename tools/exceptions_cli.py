#!/usr/bin/env python3
"""
CLI tool for managing exceptions in the es-inventory-hub database.

This tool provides commands to list, resolve, and unresolve exceptions
with various filtering options.
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_, desc
from tabulate import tabulate

# Add the project root to the Python path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.db import session_scope
from storage.schema import Exceptions


def list_exceptions(
    exception_type: Optional[str] = None,
    filter_date: Optional[date] = None,
    unresolved_only: bool = False
) -> List[Exceptions]:
    """
    List exceptions with optional filtering.
    
    Args:
        exception_type: Filter by exception type (e.g., 'MISSING_NINJA')
        filter_date: Filter by date found (YYYY-MM-DD format)
        unresolved_only: Only show unresolved exceptions
        
    Returns:
        List of Exception objects matching the criteria
    """
    with session_scope() as session:
        query = session.query(Exceptions)
        
        # Apply filters
        if exception_type:
            query = query.filter(Exceptions.type == exception_type)
        
        if filter_date:
            query = query.filter(Exceptions.date_found == filter_date)
        
        if unresolved_only:
            query = query.filter(Exceptions.resolved == False)
        
        # Order by date_found descending, then by id descending
        query = query.order_by(desc(Exceptions.date_found), desc(Exceptions.id))
        
        return query.all()


def resolve_exception(exception_type: str, hostname: str) -> bool:
    """
    Resolve the most recent exception for the given type and hostname.
    
    Args:
        exception_type: Type of exception to resolve
        hostname: Hostname of the exception to resolve
        
    Returns:
        True if an exception was resolved, False if none found
    """
    with session_scope() as session:
        # Find the most recent exception for this type and hostname
        exception = session.query(Exceptions).filter(
            and_(
                Exceptions.type == exception_type,
                Exceptions.hostname == hostname
            )
        ).order_by(desc(Exceptions.date_found), desc(Exceptions.id)).first()
        
        if not exception:
            return False
        
        exception.resolved = True
        return True


def unresolve_exception(exception_type: str, hostname: str) -> bool:
    """
    Unresolve the most recent exception for the given type and hostname.
    
    Args:
        exception_type: Type of exception to unresolve
        hostname: Hostname of the exception to unresolve
        
    Returns:
        True if an exception was unresolved, False if none found
    """
    with session_scope() as session:
        # Find the most recent exception for this type and hostname
        exception = session.query(Exceptions).filter(
            and_(
                Exceptions.type == exception_type,
                Exceptions.hostname == hostname
            )
        ).order_by(desc(Exceptions.date_found), desc(Exceptions.id)).first()
        
        if not exception:
            return False
        
        exception.resolved = False
        return True


def format_exceptions_table(exceptions: List[Exceptions]) -> str:
    """
    Format exceptions as a table for display.
    
    Args:
        exceptions: List of Exception objects
        
    Returns:
        Formatted table string
    """
    if not exceptions:
        return "No exceptions found."
    
    # Prepare data for tabulation
    table_data = []
    for exc in exceptions:
        table_data.append([
            exc.date_found.strftime('%Y-%m-%d'),
            exc.type,
            exc.hostname,
            'Yes' if exc.resolved else 'No'
        ])
    
    headers = ['date_found', 'type', 'hostname', 'resolved']
    return tabulate(table_data, headers=headers, tablefmt='grid')


def parse_date(date_str: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        date object
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Manage exceptions in the es-inventory-hub database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                                    # List all exceptions
  %(prog)s list --type MISSING_NINJA              # List MISSING_NINJA exceptions
  %(prog)s list --unresolved-only                 # List only unresolved exceptions
  %(prog)s list --date 2024-01-15                 # List exceptions from specific date
  %(prog)s resolve --type MISSING_NINJA --hostname EXCHANGE
  %(prog)s unresolve --type MISSING_NINJA --hostname EXCHANGE
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command (default)
    list_parser = subparsers.add_parser('list', help='List exceptions')
    list_parser.add_argument(
        '--type', 
        help='Filter by exception type (e.g., MISSING_NINJA, DUPLICATE_TL)'
    )
    list_parser.add_argument(
        '--date', 
        type=parse_date,
        help='Filter by date found (YYYY-MM-DD format)'
    )
    list_parser.add_argument(
        '--unresolved-only', 
        action='store_true',
        help='Only show unresolved exceptions'
    )
    
    # Resolve command
    resolve_parser = subparsers.add_parser('resolve', help='Resolve an exception')
    resolve_parser.add_argument(
        '--type', 
        required=True,
        help='Exception type to resolve'
    )
    resolve_parser.add_argument(
        '--hostname', 
        required=True,
        help='Hostname of the exception to resolve'
    )
    
    # Unresolve command
    unresolve_parser = subparsers.add_parser('unresolve', help='Unresolve an exception')
    unresolve_parser.add_argument(
        '--type', 
        required=True,
        help='Exception type to unresolve'
    )
    unresolve_parser.add_argument(
        '--hostname', 
        required=True,
        help='Hostname of the exception to unresolve'
    )
    
    args = parser.parse_args()
    
    # If no command specified, default to list
    if args.command is None:
        args.command = 'list'
        # Create a namespace with default list arguments
        args = argparse.Namespace(
            command='list',
            type=None,
            date=None,
            unresolved_only=False
        )
    
    try:
        if args.command == 'list':
            exceptions = list_exceptions(
                exception_type=args.type,
                filter_date=args.date,
                unresolved_only=args.unresolved_only
            )
            print(format_exceptions_table(exceptions))
            
        elif args.command == 'resolve':
            if resolve_exception(args.type, args.hostname):
                print(f"Resolved exception: {args.type} for hostname {args.hostname}")
                sys.exit(0)
            else:
                print(f"No exception found: {args.type} for hostname {args.hostname}")
                sys.exit(1)
                
        elif args.command == 'unresolve':
            if unresolve_exception(args.type, args.hostname):
                print(f"Unresolved exception: {args.type} for hostname {args.hostname}")
                sys.exit(0)
            else:
                print(f"No exception found: {args.type} for hostname {args.hostname}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
