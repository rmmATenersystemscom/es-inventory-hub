# ES Inventory Hub Database Access Guide

**Purpose**: This guide provides complete instructions for accessing the ES Inventory Hub database from external projects, specifically for building a variance dashboard.

**Last Updated**: September 13, 2025  
**Database Version**: PostgreSQL  
**ES Inventory Hub Version**: v1.0.4

---

## 🔗 Database Connection Information

### **Connection Details**
```
Host: localhost (or server IP for remote access)
Port: 5432
Database: es_inventory_hub
Username: postgres
Password: Xat162gT2Qsg4WDlO5r
```

### **Connection String**
```
postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub
```

### **Environment Variables**
```bash
# Primary connection string
DB_DSN=postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub
DATABASE_URL=postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub

# Individual components (alternative)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=es_inventory_hub
DB_USER=postgres
DB_PASSWORD=Xat162gT2Qsg4WDlO5r
```

---

## 📊 Database Schema Overview

### **Primary Tables for Dashboard**

#### **`exceptions` Table**
Stores cross-vendor consistency check results and variance data.

```sql
CREATE TABLE exceptions (
    id BIGSERIAL PRIMARY KEY,
    date_found DATE NOT NULL DEFAULT CURRENT_DATE,
    type VARCHAR(64) NOT NULL,  -- MISSING_NINJA, DUPLICATE_TL, SITE_MISMATCH, SPARE_MISMATCH
    hostname VARCHAR(255) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_date DATE,
    resolved_by VARCHAR(255),
    assigned_to VARCHAR(255),
    notes TEXT[]
);
```

**Indexes:**
- `ix_exceptions_type_date` on (type, date_found)
- `ix_exceptions_hostname` on (hostname)
- `ix_exceptions_resolved` on (resolved)

#### **`device_snapshot` Table**
Main device inventory data from both Ninja and ThreatLocker.

```sql
CREATE TABLE device_snapshot (
    id BIGSERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    device_identity_id BIGINT NOT NULL REFERENCES device_identity(id),
    site_id BIGINT REFERENCES site(id),
    device_type_id INTEGER REFERENCES device_type(id),
    billing_status_id INTEGER REFERENCES billing_status(id),
    hostname VARCHAR(255),
    os_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core Device Information
    organization_name VARCHAR(255),
    display_name VARCHAR(255),
    device_status VARCHAR(100),
    
    -- Timestamps
    last_online TIMESTAMP WITH TIME ZONE,
    agent_install_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- ThreatLocker-specific fields
    organization_id VARCHAR(255),
    computer_group VARCHAR(255),
    security_mode VARCHAR(100),
    deny_count_1d INTEGER,
    deny_count_3d INTEGER,
    deny_count_7d INTEGER,
    install_date DATE,
    is_locked_out BOOLEAN,
    is_isolated BOOLEAN,
    agent_version VARCHAR(100),
    has_checked_in BOOLEAN,
    
    CONSTRAINT uq_device_snapshot_date_vendor_device 
        UNIQUE (snapshot_date, vendor_id, device_identity_id)
);
```

#### **`vendor` Table**
Vendor information for data sources.

```sql
CREATE TABLE vendor (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Current data:
-- ID 1: ninja (legacy)
-- ID 2: threatlocker (legacy)  
-- ID 3: Ninja (current)
-- ID 4: ThreatLocker (current)
```

#### **`site` Table**
Site/organization information.

```sql
CREATE TABLE site (
    id BIGSERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendor(id),
    vendor_site_key VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    UNIQUE(vendor_id, vendor_site_key)
);
```

#### **`billing_status` Table**
Billing status classifications.

```sql
CREATE TABLE billing_status (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL
);

-- Current data:
-- ID 1: billable
-- ID 2: spare  
-- ID 3: unknown
```

---

## 🚀 Quick Setup for External Project

### **1. Project Structure**
```
/opt/dashboard-project/es-dashboards/dashboards/variance-dashboard/
├── app.py                 # Flask application
├── config.py             # Configuration management
├── models/
│   ├── __init__.py
│   ├── database.py       # Database connection
│   └── schemas.py        # SQLAlchemy models
├── routes/
│   ├── __init__.py
│   ├── exceptions.py     # Exception management routes
│   └── dashboard.py      # Main dashboard routes
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── exceptions.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── .env                  # Environment variables
└── requirements.txt      # Python dependencies
```

### **2. Environment Setup**
```bash
# Create project directory
mkdir -p /opt/dashboard-project/es-dashboards/dashboards/variance-dashboard
cd /opt/dashboard-project/es-dashboards/dashboards/variance-dashboard

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install flask psycopg2-binary sqlalchemy python-dotenv alembic
```

### **3. Dependencies (requirements.txt)**
```txt
Flask>=2.3.0
psycopg2-binary>=2.9.0
SQLAlchemy>=1.4.0
Alembic>=1.8.0
python-dotenv>=0.19.0
Werkzeug>=2.3.0
```

### **4. Environment Configuration (.env)**
```bash
# Database connection
DB_DSN=postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub
DATABASE_URL=postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub

# Flask configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Dashboard configuration
DASHBOARD_REFRESH_INTERVAL=300
DASHBOARD_TIMEOUT=30
```

---

## 📋 Essential Database Models

### **Copy Required Files from ES Inventory Hub**
```bash
# Copy database models and utilities
cp /opt/es-inventory-hub/storage/schema.py ./models/schemas.py
cp /opt/es-inventory-hub/common/db.py ./models/database.py
cp /opt/es-inventory-hub/common/config.py ./config.py
```

### **Key SQLAlchemy Models**
```python
# models/schemas.py (copied from ES Inventory Hub)
from sqlalchemy import Column, Integer, String, Date, Boolean, BigInteger, JSONB, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Exceptions(Base):
    __tablename__ = 'exceptions'
    
    id = Column(BigInteger, primary_key=True)
    date_found = Column(Date, nullable=False, default=datetime.utcnow().date())
    type = Column(String(64), nullable=False)
    hostname = Column(String(255), nullable=False)
    details = Column(JSONB, nullable=False, default={})
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_date = Column(Date)
    resolved_by = Column(String(255))
    assigned_to = Column(String(255))
    notes = Column(JSONB, default=[])

class DeviceSnapshot(Base):
    __tablename__ = 'device_snapshot'
    
    id = Column(BigInteger, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    device_identity_id = Column(BigInteger, ForeignKey('device_identity.id'), nullable=False)
    hostname = Column(String(255))
    organization_name = Column(String(255))
    display_name = Column(String(255))
    device_status = Column(String(100))
    # ... (additional fields as needed)

class Vendor(Base):
    __tablename__ = 'vendor'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
```

---

## 🔍 Essential Database Queries

### **Exception Queries**
```sql
-- Get all exceptions for today
SELECT * FROM exceptions 
WHERE date_found = CURRENT_DATE 
ORDER BY type, hostname;

-- Get exception statistics by type
SELECT type, COUNT(*) as count 
FROM exceptions 
WHERE date_found = CURRENT_DATE 
GROUP BY type;

-- Get unresolved exceptions
SELECT * FROM exceptions 
WHERE resolved = FALSE 
ORDER BY date_found DESC, type;

-- Get exceptions by hostname pattern
SELECT * FROM exceptions 
WHERE hostname ILIKE '%CHI-%' 
AND date_found = CURRENT_DATE;
```

### **Device Count Queries**
```sql
-- Get device counts by vendor for today
SELECT v.name as vendor, COUNT(*) as device_count
FROM device_snapshot ds
JOIN vendor v ON ds.vendor_id = v.id
WHERE ds.snapshot_date = CURRENT_DATE
GROUP BY v.name;

-- Get total devices by date
SELECT snapshot_date, COUNT(*) as total_devices
FROM device_snapshot
GROUP BY snapshot_date
ORDER BY snapshot_date DESC
LIMIT 30;

-- Get devices by organization
SELECT organization_name, COUNT(*) as device_count
FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE
GROUP BY organization_name
ORDER BY device_count DESC;
```

### **Variance Analysis Queries**
```sql
-- Get missing Ninja devices (ThreatLocker devices not in Ninja)
SELECT tl.hostname, tl.organization_name, tl.snapshot_date
FROM device_snapshot tl
LEFT JOIN device_snapshot ninja ON (
    LOWER(SPLIT_PART(tl.hostname, '.', 1)) = LOWER(SPLIT_PART(ninja.hostname, '.', 1))
    AND ninja.vendor_id = 3
    AND ninja.snapshot_date = tl.snapshot_date
)
WHERE tl.vendor_id = 4
AND tl.snapshot_date = CURRENT_DATE
AND ninja.id IS NULL;

-- Get spare devices still in ThreatLocker
SELECT tl.hostname, ninja.display_name, ninja.billing_status_id
FROM device_snapshot tl
JOIN device_snapshot ninja ON (
    LOWER(SPLIT_PART(tl.hostname, '.', 1)) = LOWER(SPLIT_PART(ninja.hostname, '.', 1))
    AND ninja.vendor_id = 3
    AND ninja.snapshot_date = tl.snapshot_date
)
WHERE tl.vendor_id = 4
AND tl.snapshot_date = CURRENT_DATE
AND ninja.billing_status_id = 2; -- 2 = spare
```

---

## 🧪 Connection Testing

### **Test Script (test_connection.py)**
```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def test_database_connection():
    """Test connection to ES Inventory Hub database"""
    dsn = os.getenv('DB_DSN')
    if not dsn:
        print("❌ DB_DSN not found in environment variables")
        return False
    
    try:
        engine = create_engine(dsn)
        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            
            # Test exceptions table
            result = conn.execute(text("SELECT COUNT(*) FROM exceptions"))
            exceptions = result.scalar()
            print(f"✅ Found {exceptions} exceptions")
            
            # Test device_snapshot table
            result = conn.execute(text("SELECT COUNT(*) FROM device_snapshot"))
            devices = result.scalar()
            print(f"✅ Found {devices} device snapshots")
            
            # Test vendor table
            result = conn.execute(text("SELECT name FROM vendor ORDER BY id"))
            vendors = [row[0] for row in result.fetchall()]
            print(f"✅ Vendors: {', '.join(vendors)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_database_connection()
```

### **Run Connection Test**
```bash
python test_connection.py
```

---

## 📊 Current Data Status

### **Latest Collection Results**
- **Ninja Devices**: 758 devices (vendor_id = 3)
- **ThreatLocker Devices**: 382 devices (vendor_id = 4)
- **Total Devices**: 1,140+ devices
- **Active Exceptions**: 41 exceptions

### **Exception Breakdown**
- **MISSING_NINJA**: 17 devices (ThreatLocker devices not in Ninja)
- **SPARE_MISMATCH**: 23 devices (spare devices still in ThreatLocker)
- **DUPLICATE_TL**: 1 device (duplicate ThreatLocker entries)
- **SITE_MISMATCH**: 0 devices (no site mismatches)

---

## 🔧 Flask Application Template

### **Basic Flask App (app.py)**
```python
from flask import Flask, render_template, jsonify
from models.database import session_scope
from models.schemas import Exceptions, DeviceSnapshot, Vendor
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/exceptions')
def get_exceptions():
    """Get all exceptions for today"""
    with session_scope() as session:
        exceptions = session.query(Exceptions).filter(
            Exceptions.date_found == date.today()
        ).order_by(Exceptions.type, Exceptions.hostname).all()
        
        return jsonify([{
            'id': exc.id,
            'type': exc.type,
            'hostname': exc.hostname,
            'details': exc.details,
            'resolved': exc.resolved,
            'date_found': exc.date_found.isoformat()
        } for exc in exceptions])

@app.route('/api/exceptions/stats')
def get_exception_stats():
    """Get exception statistics"""
    with session_scope() as session:
        from sqlalchemy import func
        
        stats = session.query(
            Exceptions.type,
            func.count(Exceptions.id).label('count')
        ).filter(
            Exceptions.date_found == date.today()
        ).group_by(Exceptions.type).all()
        
        return jsonify({stat.type: stat.count for stat in stats})

@app.route('/api/devices/summary')
def get_device_summary():
    """Get device count summary"""
    with session_scope() as session:
        from sqlalchemy import func
        
        summary = session.query(
            Vendor.name,
            func.count(DeviceSnapshot.id).label('count')
        ).join(DeviceSnapshot).filter(
            DeviceSnapshot.snapshot_date == date.today()
        ).group_by(Vendor.name).all()
        
        return jsonify({item.name: item.count for item in summary})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## 🔒 Security Considerations

### **Database Access**
- **Local Access**: Use `localhost` if both projects are on the same server
- **Remote Access**: Update PostgreSQL configuration for remote connections
- **Firewall**: Ensure port 5432 is accessible if needed

### **PostgreSQL Configuration for Remote Access**
```bash
# Edit /etc/postgresql/*/main/postgresql.conf
listen_addresses = '*'

# Edit /etc/postgresql/*/main/pg_hba.conf
host    es_inventory_hub    postgres    0.0.0.0/0    md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### **Application Security**
- Use environment variables for sensitive data
- Implement proper authentication and authorization
- Validate all user inputs
- Use HTTPS in production
- Implement rate limiting for API endpoints

---

## 📈 Performance Optimization

### **Database Indexes**
The database already has optimized indexes for common queries:
- `ix_exceptions_type_date` on (type, date_found)
- `ix_exceptions_hostname` on (hostname)
- `ix_exceptions_resolved` on (resolved)

### **Query Optimization Tips**
- Use `LIMIT` for large result sets
- Filter by date ranges to reduce data volume
- Use `EXPLAIN ANALYZE` to optimize slow queries
- Consider caching for frequently accessed data

### **Caching Strategy**
```python
# Example caching with Flask-Caching
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/exceptions/stats')
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_exception_stats():
    # ... query logic
```

---

## 🚀 Deployment Checklist

### **Development Environment**
- [ ] Virtual environment created and activated
- [ ] Dependencies installed from requirements.txt
- [ ] Environment variables configured in .env
- [ ] Database connection tested
- [ ] Basic Flask app running

### **Production Deployment**
- [ ] Gunicorn WSGI server configured
- [ ] Nginx reverse proxy setup
- [ ] SSL/TLS certificates installed
- [ ] Systemd service created
- [ ] Logging and monitoring configured
- [ ] Backup strategy implemented

---

## 📞 Support and Troubleshooting

### **Common Issues**
1. **Connection Refused**: Check if PostgreSQL is running and accessible
2. **Authentication Failed**: Verify username/password in connection string
3. **Database Not Found**: Ensure database name is correct
4. **Permission Denied**: Check PostgreSQL user permissions

### **Debug Commands**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection from command line
psql -h localhost -U postgres -d es_inventory_hub

# Check database size
psql -h localhost -U postgres -d es_inventory_hub -c "SELECT pg_size_pretty(pg_database_size('es_inventory_hub'));"

# Check table sizes
psql -h localhost -U postgres -d es_inventory_hub -c "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

---

## 📚 Additional Resources

### **ES Inventory Hub Files**
- **Database Models**: `/opt/es-inventory-hub/storage/schema.py`
- **Database Utils**: `/opt/es-inventory-hub/common/db.py`
- **Configuration**: `/opt/es-inventory-hub/common/config.py`
- **Cross-vendor Checks**: `/opt/es-inventory-hub/collectors/checks/cross_vendor.py`
- **Device Matching Logic**: [DEVICE_MATCHING_LOGIC.md](./DEVICE_MATCHING_LOGIC.md)

### **Documentation**
- **Main README**: `/opt/es-inventory-hub/README.md`
- **Device Matching Logic**: [DEVICE_MATCHING_LOGIC.md](./DEVICE_MATCHING_LOGIC.md) - **CRITICAL for variance reporting**
- **API Guide**: `/opt/dashboard-project/docs/THREATLOCKER_API_GUIDE.md`
- **Database Migrations**: `/opt/es-inventory-hub/storage/alembic/versions/`

### **Monitoring**
- **System Status**: Run `/opt/es-inventory-hub/scripts/monitor_collectors.py`
- **Collection Logs**: `/var/log/es-inventory-hub/`

---

**Note**: This guide provides complete access to the ES Inventory Hub database for building external dashboards. The database contains comprehensive device inventory data and variance information that can be used to create powerful analytics and management interfaces.
