# AI Prompt: ES Inventory Hub Variance Dashboard

## **Your Task**
Build a comprehensive web dashboard to visualize and manage variance data from the ES Inventory Hub database. The dashboard should display cross-vendor consistency check results and provide tools for managing device inventory discrepancies.

## **Essential Information**

### **Database Access Guide Location**
**CRITICAL**: Read the complete database access guide at:
```
/opt/es-inventory-hub/DATABASE_ACCESS_GUIDE.md
```

This file contains **ALL** the information you need including:
- Database connection credentials and connection strings
- Complete database schema with table structures
- Step-by-step setup instructions
- Ready-to-use code templates
- Essential database queries
- Security and deployment considerations

### **Current System Status**
- **Database**: PostgreSQL with 1,140+ devices (758 Ninja + 382 ThreatLocker)
- **Active Exceptions**: 41 variance issues requiring attention
- **Exception Types**: MISSING_NINJA (17), SPARE_MISMATCH (23), DUPLICATE_TL (1), SITE_MISMATCH (0)
- **Collection Schedule**: Daily automated collection at 2:10 AM (Ninja) and 2:31 AM (ThreatLocker)

### **Key Requirements**
1. **Read the DATABASE_ACCESS_GUIDE.md file first** - it contains everything you need
2. **Build a Flask-based web dashboard** that connects to the ES Inventory Hub database
3. **Display variance data** from the `exceptions` table with filtering and management capabilities
4. **Provide real-time insights** into device inventory discrepancies
5. **Enable exception management** (resolve, assign, track status)

### **Project Location**
Create your dashboard project at:
```
/opt/dashboard-project/es-dashboards/dashboards/variance-dashboard/
```

### **What You'll Find in the Database Access Guide**
- **Connection Details**: Exact database credentials and connection strings
- **Schema Documentation**: Complete table structures for `exceptions`, `device_snapshot`, `vendor`, etc.
- **Setup Instructions**: Step-by-step project setup with dependencies
- **Code Templates**: Flask app templates, SQLAlchemy models, API endpoints
- **Database Queries**: Pre-written queries for exceptions, device counts, variance analysis
- **Testing Scripts**: Connection testing and validation tools
- **Security Guidelines**: Authentication, authorization, and deployment considerations

### **Your Approach**
1. **Start by reading** `/opt/es-inventory-hub/DATABASE_ACCESS_GUIDE.md` completely
2. **Follow the setup instructions** in the guide to create your project
3. **Use the provided code templates** as your foundation
4. **Test the database connection** using the provided test script
5. **Build the dashboard** using the schema and query examples
6. **Implement the UI/UX** based on the separate layout instructions you'll receive

### **Success Criteria**
- ✅ Dashboard successfully connects to ES Inventory Hub database
- ✅ Displays all 41 current exceptions with full details
- ✅ Provides filtering, sorting, and management capabilities
- ✅ Shows real-time device counts and variance statistics
- ✅ Enables exception resolution and tracking
- ✅ Responsive, professional user interface

### **Important Notes**
- The database access guide contains **everything** you need - no additional database information is required
- Focus on the variance data in the `exceptions` table as your primary data source
- Use the existing ES Inventory Hub database - do not create a new database
- Follow the project structure and naming conventions outlined in the guide
- The guide includes complete code examples and templates to get you started

### **Next Steps**
1. Read the complete DATABASE_ACCESS_GUIDE.md file
2. Set up your project following the guide's instructions
3. Test the database connection
4. Build the dashboard using the provided templates and examples
5. Implement the UI based on the separate layout instructions you'll receive

**Remember**: The DATABASE_ACCESS_GUIDE.md file is your complete reference - it contains all the technical details, code examples, and setup instructions you need to successfully build this dashboard.


