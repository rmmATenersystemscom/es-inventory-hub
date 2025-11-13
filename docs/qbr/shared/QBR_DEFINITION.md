# QBR Definition and Data Domain Clarification

## About This Document
This document defines what **QBR (Quarterly Business Review)** means in the context of Enersystems’ MSP operations and the QBR Web Dashboard system.  
It is intended for **both the Database AI and Dashboard AI** to ensure a shared understanding of how different data sources relate and how QBR metrics differ from raw operational or vendor data.

---

## 🧭 What QBR Means

A **QBR (Quarterly Business Review)** is a **data-driven client performance review** that consolidates operational, service, and financial metrics into a unified view.  
It is used internally by Enersystems to evaluate performance across clients, and externally to demonstrate value during client reviews.

The **QBR Dashboard System** automates what was once a manual spreadsheet-driven process by integrating data from:
- **NinjaOne (RMM)** — technical and asset management data  
- **ConnectWise Manage (PSA)** — service and workload data  
- **QuickBooks (Accounting)** — financial data  
- **Optional Vendor Integrations (e.g., ThreatLocker)** — specialized compliance or security data

---

## ⚙️ QBR Data Domains and Roles

| Domain | Source System | Primary Focus | Nature of Data |
|:-------|:---------------|:---------------|:----------------|
| **Operational** | NinjaOne (RMM) | Devices, endpoints, managed assets | Quantitative, technical, static per device |
| **Service Delivery** | ConnectWise Manage (PSA) | Tickets, hours, service activity | Temporal, workflow-based, human-driven |
| **Financial** | QuickBooks | Revenue, expenses, margins | Monetary, transactional, accounting-grade |
| **Security/Vendor** | ThreatLocker, Veeam, etc. | Security or compliance status | Contextual, limited-scope vendor data |

Each system serves a distinct purpose. **QBR metrics unify them** into a single narrative about how well Enersystems delivers, manages, and profits from its services.

---

## 🔍 How These Data Sources Differ

### 1️⃣ NinjaOne Data (Operational Layer)
- Defines **which endpoints and clients exist** (inventory baseline).  
- Provides **counts, status, and asset configuration** data.  
- Represents **the scope of managed work**, not time or cost.  
- Key metrics: *# of Endpoints Managed, Device Status, Patch Compliance.*

**For Database AI:** Serves as the *foundation* for organizations and assets.  
**For Dashboard AI:** Displayed as operational scope and health indicators.

---

### 2️⃣ ConnectWise Manage Data (Service Layer)
- Represents **the work performed** — tickets created, resolved, and time logged.  
- Each record connects to an organization or contact.  
- Contains **temporal and workload-based** data.  
- Key metrics: *Tickets Created, Tickets Closed, Hours on Reactive Work.*

**For Database AI:** Serves as the *activity layer* describing labor and responsiveness.  
**For Dashboard AI:** Used for charts showing workload, efficiency, and SLA trends.

---

### 3️⃣ QuickBooks Data (Financial Layer)
- Captures **the financial outcomes** of service operations.  
- Used to derive **revenue, cost, margin, and profitability** metrics.  
- Links to Ninja or ConnectWise orgs via customer/invoice mapping.  
- Key metrics: *Monthly Recurring Revenue, Gross Margin, Expense Ratios.*

**For Database AI:** Feeds financial KPIs for smartnumbers.  
**For Dashboard AI:** Displayed in financial summary widgets and charts.

---

### 4️⃣ ThreatLocker and Other Vendor Data (Supplementary Layer)
- Specialized integrations (e.g., security or compliance metrics).  
- Complements NinjaOne data but does not drive QBR financial or service metrics.  
- Used for *exceptions* or *variance tracking*.  

**For Database AI:** Optional enrichment source.  
**For Dashboard AI:** Secondary indicators, typically shown in sub-panels or reports.

---

## 📊 How QBR Metrics Differ from Raw Data

| Type | Description | Example |
|------|--------------|----------|
| **Source Data** | Raw values pulled directly from APIs | “Tickets closed = 152”, “Endpoints = 720” |
| **Derived Metrics** | Calculated KPIs combining sources | “Tickets per endpoint = 0.21”, “Gross Margin = 68%” |
| **SmartNumbers** | Executive-level rollups for QBR | “Operational Efficiency = 93%”, “Revenue Retention = 98%” |

QBR metrics are therefore **aggregated and derived** — they tell *how the business performed*, not just *what happened*.

---

## 🧩 Summary for AIs

- **NinjaOne defines what you manage.**  
- **ConnectWise defines what you did.**  
- **QuickBooks defines what you earned.**  
- **ThreatLocker defines how secure you are.**  
- **QBR metrics unify all of these** to answer: *“How effectively did we deliver and profit from managed services this quarter?”*

---

## ✅ Integration Guidance

**Database AI:**
- Build collectors for ConnectWise and QuickBooks following NinjaOne pattern.  
- Normalize org-level joins based on consistent identifiers.  
- Store QBR-ready data in `metrics_monthly`, `metrics_quarterly`, and `smartnumbers` tables.

**Dashboard AI:**
- Use only the REST API endpoints exposed by the backend.  
- Do not directly query or replicate backend logic.  
- Display unified, time-based KPIs under logical sections (Operations, Service, Financial).

---

**Version:** 1.0  
**Author:** GPT-5 (Architectural Alignment Document)  
**Date:** 2025-11-06
