# ES Inventory Hub API

**Purpose**: This directory contains the REST API server and testing utilities for the ES Inventory Hub system.

**Last Updated**: September 22, 2025  
**Status**: ✅ **ACTIVE** - API server and testing utilities

---

## 📁 **API Directory Contents**

### **Core Files**

#### **api_server.py**
- **Purpose**: REST API server for variance data and collector management
- **Size**: 429 lines
- **Dependencies**: Flask, SQLAlchemy, project modules
- **Usage**: `python3 api_server.py`
- **Port**: Runs on https://db-api.enersystems.com:5400

### **Port Configuration**
- **ES Inventory Hub Port Range**: 5400-5499
- **Dashboard Project Port Range**: 5000-5499 (reserved)
- **Current API Server Port**: 5400

#### **test_api.py**
- **Purpose**: Testing script for the API server
- **Size**: 73 lines
- **Dependencies**: requests library
- **Usage**: `python3 test_api.py`
- **Functionality**: Tests all API endpoints and validates responses

#### **requirements-api.txt**
- **Purpose**: Python dependencies for the API server
- **Dependencies**: Flask, Flask-CORS, SQLAlchemy, psycopg2-binary, python-dotenv

---

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
cd /opt/es-inventory-hub
pip install -r api/requirements-api.txt
```

### **2. Start API Server**
```bash
python3 api/api_server.py
```

### **3. Test API**
```bash
python3 api/test_api.py
```

---

## 📊 **API Endpoints**

### **System Status**
- `GET /api/health` - Health check
- `GET /api/status` - Overall system status
- `GET /api/collectors/status` - Collector service status

### **Variance Reports**
- `GET /api/variance-report/latest` - Latest variance report
- `GET /api/variance-report/{date}` - Specific date variance report
- `GET /api/exceptions` - Exception data with filtering

### **Collector Management**
- `POST /api/collectors/run` - Trigger collector runs
- `POST /api/exceptions/{id}/resolve` - Mark exceptions as resolved

---

## 🔌 **Port Configuration**

### **Port Range Allocation**
- **Dashboard Project**: Ports 5000-5499 (reserved)
- **ES Inventory Hub**: Ports 5400-5499 (available for use)
- **Current API Server**: Port 5400

### **Port Selection Rationale**
- **Port 5400**: Primary API server port
- **Future Expansion**: Additional services can use ports 5401-5499
- **Conflict Avoidance**: Clear separation from dashboard project ports
- **Firewall Considerations**: Ensure ports 5400-5499 are accessible if needed

### **Changing Ports**
To change the API server port, update the following:
1. **API Server**: Modify `port=5400` in `api_server.py`
2. **Test Script**: Update `API_BASE` in `test_api.py`
3. **Documentation**: Update all references to the new port
4. **Firewall**: Update firewall rules if applicable

---

## 🔧 **API Server Features**

### **Core Functionality**
1. **Variance Data Access** - RESTful endpoints for accessing variance reports
2. **Collector Management** - Trigger manual collector runs
3. **System Status** - Health checks and system monitoring
4. **Exception Management** - Resolve and track exceptions

### **Technical Details**
- **Framework**: Flask with CORS support
- **Database**: SQLAlchemy with PostgreSQL
- **Authentication**: None (internal API)
- **Error Handling**: Comprehensive error responses
- **Logging**: Console output with timestamps

---

## 🧪 **Testing**

### **Test Script Features**
- **Comprehensive Testing** - Tests all API endpoints
- **Response Validation** - Validates JSON responses
- **Error Handling** - Tests error scenarios
- **Status Reporting** - Clear pass/fail reporting

### **Running Tests**
```bash
# Test all endpoints
python3 api/test_api.py

# Test specific endpoint (manual)
curl https://db-api.enersystems.com:5400/api/health
curl https://db-api.enersystems.com:5400/api/status
curl https://db-api.enersystems.com:5400/api/variance-report/latest
```

---

## 📚 **Integration**

### **For Dashboard Developers**
- **API Base URL**: `https://db-api.enersystems.com:5400`
- **Documentation**: See `docs/API_QUICK_REFERENCE.md`
- **Integration Guide**: See `docs/DASHBOARD_INTEGRATION_GUIDE.md`

### **For System Administrators**
- **Service Management**: API server runs as standalone process
- **Monitoring**: Check console output for logs
- **Dependencies**: Ensure PostgreSQL is running

---

## 🔒 **Security Considerations**

### **Current Implementation**
- **No Authentication** - Internal API only
- **CORS Enabled** - Cross-origin requests allowed
- **Local Access** - Binds to localhost only

### **Production Recommendations**
- **Add Authentication** - Implement API keys or JWT
- **HTTPS Only** - Use SSL/TLS in production
- **Rate Limiting** - Implement request rate limiting
- **Input Validation** - Validate all input parameters

---

## 📈 **Performance**

### **Optimization Features**
- **Database Connection Pooling** - SQLAlchemy connection management
- **Efficient Queries** - Optimized database queries
- **Response Caching** - Consider implementing for static data

### **Monitoring**
- **Response Times** - Monitor API response times
- **Error Rates** - Track 4xx/5xx error rates
- **Resource Usage** - Monitor CPU and memory usage

---

## 🚨 **Troubleshooting**

### **Common Issues**

1. **API Server Won't Start**
   ```bash
   # Check dependencies
   pip install -r api/requirements-api.txt
   
   # Check database connection
   python3 -c "from common.db import get_engine; print('DB OK')"
   ```

2. **404 Errors**
   ```bash
   # Ensure API server is running
   python3 api/api_server.py
   
   # Check endpoint URLs
   curl https://db-api.enersystems.com:5400/api/health
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Test database connection
   psql -h localhost -U postgres -d es_inventory_hub
   ```

### **Debug Mode**
```bash
# Run API server in debug mode
FLASK_DEBUG=1 python3 api/api_server.py
```

---

## 📝 **Development**

### **Adding New Endpoints**
1. **Add Route** - Define new Flask route in `api_server.py`
2. **Add Logic** - Implement endpoint logic
3. **Add Tests** - Update `test_api.py` with new tests
4. **Update Documentation** - Update this README and API guides

### **Code Structure**
```python
@app.route('/api/new-endpoint', methods=['GET'])
def new_endpoint():
    """New endpoint description."""
    try:
        # Implementation here
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## 📚 **Related Documentation**

- **[API_QUICK_REFERENCE.md](../docs/API_QUICK_REFERENCE.md)** - Quick reference for API endpoints
- **[DASHBOARD_INTEGRATION_GUIDE.md](../docs/DASHBOARD_INTEGRATION_GUIDE.md)** - Complete integration guide
- **[DATABASE_ACCESS_GUIDE.md](../docs/DATABASE_ACCESS_GUIDE.md)** - Database connection details

---

**Note**: This API provides programmatic access to the ES Inventory Hub system for external applications and dashboards.
