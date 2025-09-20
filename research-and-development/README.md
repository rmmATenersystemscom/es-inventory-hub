# Research & Development Directory

This directory contains development, debugging, and experimental scripts for the ES Inventory Hub project.

## 📁 Contents

### **Debug Scripts**
- `debug_sqlalchemy.py` - SQLAlchemy database connection and query debugging
- `debug_threatlocker.py` - ThreatLocker API testing and debugging
- `run_migration.py` - Manual migration execution script

### **Development Directories**
- `dashboard_diffs/` - Dashboard comparison and diff analysis tools

## 🚨 Important Notes

### **Development Use Only**
- These scripts are for development, testing, and debugging purposes
- **DO NOT** run these scripts in production environments
- Always review scripts before execution
- Some scripts may modify database state or make API calls

### **Script Purposes**

#### **debug_sqlalchemy.py**
- Tests database connectivity and SQLAlchemy configuration
- Useful for troubleshooting database connection issues
- Can be used to verify schema changes

#### **debug_threatlocker.py**
- Tests ThreatLocker API connectivity and authentication
- Useful for debugging API integration issues
- Can be used to test API endpoints and data retrieval

#### **run_migration.py**
- Manual migration execution script
- Use with caution - migrations should typically be run via Alembic
- Useful for testing migrations in development environments

#### **dashboard_diffs/**
- Contains tools for comparing dashboard implementations
- Used for analyzing differences between dashboard versions
- Development and testing utilities

## 🔧 Usage Guidelines

1. **Always test in development first**
2. **Review script contents before execution**
3. **Backup data before running migration scripts**
4. **Use appropriate environment variables**
5. **Clean up after testing**

## 📝 Adding New Scripts

When adding new development scripts:

1. Place them in this directory
2. Update this README with description and usage notes
3. Include appropriate warnings and safety notes
4. Test thoroughly before committing

---

*This directory is for development purposes only. Production code should be in the main project structure.*
