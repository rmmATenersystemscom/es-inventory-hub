#!/usr/bin/env python3
"""
ES Inventory Hub Custom Security Scanner
Performs custom security checks specific to the project
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class SecurityScanner:
    """Custom security scanner for ES Inventory Hub"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.findings: List[Dict[str, Any]] = []
        
    def scan_subprocess_usage(self) -> List[Dict[str, Any]]:
        """Scan for insecure subprocess usage"""
        findings = []
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            # Skip test files, virtual environments, and this scanner itself
            if any(skip in str(py_file) for skip in ['test_', '__pycache__', 'venv', '.venv', 'migrations', 'security_scan.py']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Check for shell=True
                        if 'subprocess' in line and 'shell=True' in line:
                            findings.append({
                                'severity': 'HIGH',
                                'type': 'insecure_subprocess',
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'issue': 'subprocess.run with shell=True detected',
                                'recommendation': 'Use list arguments instead of shell=True'
                            })
                        
                        # Check for os.system
                        if 'os.system' in line:
                            findings.append({
                                'severity': 'HIGH',
                                'type': 'insecure_subprocess',
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'issue': 'os.system() usage detected',
                                'recommendation': 'Use subprocess.run() with list arguments'
                            })
                        
                        # Check for eval/exec
                        if re.search(r'\beval\s*\(', line) or re.search(r'\bexec\s*\(', line):
                            findings.append({
                                'severity': 'CRITICAL',
                                'type': 'code_injection',
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': i,
                                'issue': 'eval() or exec() usage detected',
                                'recommendation': 'Avoid eval/exec - use safer alternatives'
                            })
            except Exception as e:
                print(f"Error scanning {py_file}: {e}", file=sys.stderr)
        
        return findings
    
    def scan_sql_injection(self) -> List[Dict[str, Any]]:
        """Scan for potential SQL injection vulnerabilities"""
        findings = []
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            if any(skip in str(py_file) for skip in ['test_', '__pycache__', 'venv', '.venv', 'security_scan.py']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        # Check for string concatenation in SQL
                        if 'text(' in line or 'execute(' in line:
                            # Look for f-strings or + operators in SQL context
                            if 'f"' in line or "f'" in line:
                                if 'SELECT' in line.upper() or 'INSERT' in line.upper() or 'UPDATE' in line.upper():
                                    findings.append({
                                        'severity': 'HIGH',
                                        'type': 'sql_injection',
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'issue': 'Potential SQL injection - f-string in SQL query',
                                        'recommendation': 'Use parameterized queries with :param syntax'
                                    })
            except Exception as e:
                print(f"Error scanning {py_file}: {e}", file=sys.stderr)
        
        return findings
    
    def scan_hardcoded_credentials(self) -> List[Dict[str, Any]]:
        """Scan for hardcoded credentials"""
        findings = []
        python_files = list(self.project_root.rglob("*.py"))
        
        credential_patterns = [
            (r'password\s*=\s*["\']([^"\']+)["\']', 'password'),
            (r'api_key\s*=\s*["\']([^"\']+)["\']', 'api_key'),
            (r'secret\s*=\s*["\']([^"\']+)["\']', 'secret'),
            (r'token\s*=\s*["\']([^"\']+)["\']', 'token'),
        ]
        
        for py_file in python_files:
            if any(skip in str(py_file) for skip in ['test_', '__pycache__', 'venv', '.venv', 'security_scan.py']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern, cred_type in credential_patterns:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                value = match.group(1)
                                # Skip if it's clearly a placeholder
                                if any(placeholder in value.lower() for placeholder in ['your_', 'placeholder', 'example', 'xxx', 'changeme']):
                                    continue
                                # Skip if it's an environment variable reference
                                if 'os.environ' in line or 'os.getenv' in line or 'getenv' in line:
                                    continue
                                    
                                findings.append({
                                    'severity': 'CRITICAL',
                                    'type': 'hardcoded_credential',
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': i,
                                    'issue': f'Potential hardcoded {cred_type}',
                                    'recommendation': 'Use environment variables or secure credential storage'
                                })
            except Exception as e:
                print(f"Error scanning {py_file}: {e}", file=sys.stderr)
        
        return findings
    
    def scan_cors_configuration(self) -> List[Dict[str, Any]]:
        """Check CORS configuration"""
        findings = []
        api_file = self.project_root / 'api' / 'api_server.py'
        
        if not api_file.exists():
            return findings
        
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for wildcard CORS
                if "origins=['*']" in content or 'origins=["*"]' in content:
                    findings.append({
                        'severity': 'HIGH',
                        'type': 'cors_misconfiguration',
                        'file': 'api/api_server.py',
                        'line': 0,
                        'issue': 'CORS configured with wildcard origin',
                        'recommendation': 'Restrict CORS to specific trusted origins'
                    })
                
                # Check if localhost is allowed (may be OK for development)
                if 'localhost' in content and 'CORS' in content:
                    # This is informational, not necessarily a problem
                    pass
        except Exception as e:
            print(f"Error scanning CORS: {e}", file=sys.stderr)
        
        return findings
    
    def scan_authentication(self) -> List[Dict[str, Any]]:
        """Check for authentication implementation"""
        findings = []
        api_file = self.project_root / 'api' / 'api_server.py'
        
        if not api_file.exists():
            return findings
        
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check for authentication decorators or middleware
                auth_keywords = ['@login_required', '@auth_required', 'authenticate', 'authorization', 'jwt', 'token']
                has_auth = any(keyword in content for keyword in auth_keywords)
                
                if not has_auth:
                    findings.append({
                        'severity': 'HIGH',
                        'type': 'missing_authentication',
                        'file': 'api/api_server.py',
                        'line': 0,
                        'issue': 'No authentication mechanism detected',
                        'recommendation': 'Implement API authentication (API keys, JWT, or similar)'
                    })
        except Exception as e:
            print(f"Error scanning authentication: {e}", file=sys.stderr)
        
        return findings
    
    def run_all_scans(self) -> Dict[str, Any]:
        """Run all security scans"""
        print("Running custom security scans...", file=sys.stderr)
        
        all_findings = []
        all_findings.extend(self.scan_subprocess_usage())
        all_findings.extend(self.scan_sql_injection())
        all_findings.extend(self.scan_hardcoded_credentials())
        all_findings.extend(self.scan_cors_configuration())
        all_findings.extend(self.scan_authentication())
        
        # Count by severity
        severity_counts = {
            'CRITICAL': len([f for f in all_findings if f['severity'] == 'CRITICAL']),
            'HIGH': len([f for f in all_findings if f['severity'] == 'HIGH']),
            'MEDIUM': len([f for f in all_findings if f['severity'] == 'MEDIUM']),
            'LOW': len([f for f in all_findings if f['severity'] == 'LOW']),
        }
        
        return {
            'timestamp': str(Path(__file__).stat().st_mtime),
            'total_findings': len(all_findings),
            'severity_counts': severity_counts,
            'findings': all_findings
        }


def main():
    parser = argparse.ArgumentParser(description='ES Inventory Hub Custom Security Scanner')
    parser.add_argument('--output', '-o', help='Output JSON file', default=None)
    parser.add_argument('--project-root', help='Project root directory', default=None)
    
    args = parser.parse_args()
    
    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = PROJECT_ROOT
    
    scanner = SecurityScanner(project_root)
    results = scanner.run_all_scans()
    
    output_json = json.dumps(results, indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output_json)
    
    # Exit with error code if critical findings
    if results['severity_counts']['CRITICAL'] > 0:
        sys.exit(1)
    elif results['severity_counts']['HIGH'] > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

