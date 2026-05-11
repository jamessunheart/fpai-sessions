# 📊 Droplet #2 - Dashboard API Documentation

**Steward:** Haythem Timoumi  
**Base URL:** `https://drop2.fullpotential.ai`  
**Purpose:** System monitoring, metrics collection, and sprint management

---

## 🎯 Overview

Droplet 2 provides REST APIs for:
- Sprint management (CRUD operations)
- System health monitoring (heartbeats)
- Droplet status tracking
- Proof submission tracking
- Daily analytics and metrics

---

## 🚀 Quick Test - Copy & Paste into Postman

**Import cURL → Open Postman → Click "Import" → Select "Raw text" → Paste any cURL below**

### 1. Submit Heartbeat (Most Important)
```bash
curl -X POST https://drop2.fullpotential.ai/heartbeats \
  -H "Content-Type: application/json" \
  -d '{"Cell_ID":"droplet_13","CPU_Usage":45.2,"RAM_Usage":512,"Status":"active"}'
```

### 2. Get All Heartbeats
```bash
curl -X GET https://drop2.fullpotential.ai/heartbeats \
  -H "Content-Type: application/json"
```

### 3. Get All Sprints
```bash
curl -X GET https://drop2.fullpotential.ai/sprints \
  -H "Content-Type: application/json"
```

### 4. Create Sprint
```bash
curl -X POST https://drop2.fullpotential.ai/sprints \
  -H "Content-Type: application/json" \
  -d '{"Sprint_ID":"sprint_test_001","Name":"Test Sprint","Dev_Name":"Haythem","Status":"Active","Time_Spent_hr":2.0,"Notes":"Testing API"}'
```

### 5. Get All Cells
```bash
curl -X GET https://drop2.fullpotential.ai/cells \
  -H "Content-Type: application/json"
```

### 6. Get All Proofs
```bash
curl -X GET https://drop2.fullpotential.ai/proof \
  -H "Content-Type: application/json"
```

### 7. Generate Daily Digest
```bash
curl -X POST https://drop2.fullpotential.ai/daily-digest \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 📡 Available Endpoints

### 1. GET /heartbeats
**Purpose:** Retrieve system health metrics from all droplets

**Request:**
```http
GET https://drop2.fullpotential.ai/heartbeats
Content-Type: application/json
```

**Response Schema:**
```json
{
  "records": [
    {
      "id": "rec123abc",
      "createdTime": "2025-01-15T10:30:00.000Z",
      "fields": {
        "Cell_ID": "droplet_13",
        "CPU_Usage": 45.2,
        "RAM_Usage": 68.5,
        "Status": "active",
        "Timestamp": "2025-01-15T10:30:00Z"
      }
    }
  ]
}
```

**Postman Setup:**
- Method: `GET`
- URL: `https://drop2.fullpotential.ai/heartbeats`
- Headers: `Content-Type: application/json`

---

### 2. POST /heartbeats
**Purpose:** Submit heartbeat/metrics from a droplet

**Request:**
```http
POST https://drop2.fullpotential.ai/heartbeats
Content-Type: application/json

{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active"
}
```

**Response:**
```json
{
  "id": "rec123abc",
  "createdTime": "2025-01-15T10:30:00.000Z",
  "fields": {
    "Cell_ID": "droplet_13",
    "CPU_Usage": 45.2,
    "RAM_Usage": 512,
    "Status": "active"
  }
}
```

**Postman Setup:**
- Method: `POST`
- URL: `https://drop2.fullpotential.ai/heartbeats`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active"
}
```

---

### 3. GET /sprints
**Purpose:** Retrieve all sprints

**Request:**
```http
GET https://drop2.fullpotential.ai/sprints
Content-Type: application/json
```

**Response Schema:**
```json
{
  "records": [
    {
      "id": "recXYZ789",
      "createdTime": "2025-01-15T09:00:00.000Z",
      "fields": {
        "Sprint_ID": "sprint_001",
        "Name": "Build Nexus Integration",
        "Dev_Name": "Suresh",
        "Status": "Active",
        "Proof_URL": "https://github.com/...",
        "Time_Spent_hr": 5.5,
        "Notes": "Integration in progress"
      }
    }
  ]
}
```

**Postman Setup:**
- Method: `GET`
- URL: `https://drop2.fullpotential.ai/sprints`
- Headers: `Content-Type: application/json`

---

### 4. POST /sprints
**Purpose:** Create a new sprint

**Request:**
```http
POST https://drop2.fullpotential.ai/sprints
Content-Type: application/json

{
  "Sprint_ID": "sprint_002",
  "Name": "Dashboard Metrics Endpoint",
  "Dev_Name": "Haythem",
  "Status": "Active",
  "Time_Spent_hr": 2.0,
  "Notes": "Creating metrics API"
}
```

**Response:**
```json
{
  "id": "recABC123",
  "createdTime": "2025-01-15T11:00:00.000Z",
  "fields": {
    "Sprint_ID": "sprint_002",
    "Name": "Dashboard Metrics Endpoint",
    "Dev_Name": "Haythem",
    "Status": "Active",
    "Time_Spent_hr": 2.0,
    "Notes": "Creating metrics API"
  }
}
```

**Postman Setup:**
- Method: `POST`
- URL: `https://drop2.fullpotential.ai/sprints`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "Sprint_ID": "sprint_002",
  "Name": "Dashboard Metrics Endpoint",
  "Dev_Name": "Haythem",
  "Status": "Active",
  "Time_Spent_hr": 2.0,
  "Notes": "Creating metrics API"
}
```

---

### 5. PUT /sprints/{id}
**Purpose:** Update an existing sprint

**Request:**
```http
PUT https://drop2.fullpotential.ai/sprints/recABC123
Content-Type: application/json

{
  "Status": "Done",
  "Time_Spent_hr": 8.5,
  "Proof_URL": "https://github.com/proof"
}
```

**Response:**
```json
{
  "id": "recABC123",
  "fields": {
    "Sprint_ID": "sprint_002",
    "Name": "Dashboard Metrics Endpoint",
    "Dev_Name": "Haythem",
    "Status": "Done",
    "Time_Spent_hr": 8.5,
    "Proof_URL": "https://github.com/proof",
    "Notes": "Creating metrics API"
  }
}
```

**Postman Setup:**
- Method: `PUT`
- URL: `https://drop2.fullpotential.ai/sprints/recABC123` (replace with actual record ID)
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "Status": "Done",
  "Time_Spent_hr": 8.5,
  "Proof_URL": "https://github.com/proof"
}
```

---

### 6. DELETE /sprints/{id}
**Purpose:** Delete a sprint

**Request:**
```http
DELETE https://drop2.fullpotential.ai/sprints/recABC123
Content-Type: application/json
```

**Response:**
```json
{
  "deleted": true,
  "id": "recABC123"
}
```

**Postman Setup:**
- Method: `DELETE`
- URL: `https://drop2.fullpotential.ai/sprints/recABC123` (replace with actual record ID)
- Headers: `Content-Type: application/json`

---

### 7. GET /cells
**Purpose:** Retrieve droplet/cell status information

**Request:**
```http
GET https://drop2.fullpotential.ai/cells
Content-Type: application/json
```

**Response Schema:**
```json
{
  "records": [
    {
      "id": "recCELL01",
      "createdTime": "2025-01-15T08:00:00.000Z",
      "fields": {
        "Cell_ID": "droplet_13",
        "Role": "Connector",
        "IP_Address": "64.227.107.127",
        "Health_Status": "OK",
        "Cost_per_hr": 0.018
      }
    }
  ]
}
```

**Postman Setup:**
- Method: `GET`
- URL: `https://drop2.fullpotential.ai/cells`
- Headers: `Content-Type: application/json`

---

### 8. GET /proof
**Purpose:** Retrieve proof submissions

**Request:**
```http
GET https://drop2.fullpotential.ai/proof
Content-Type: application/json
```

**Response Schema:**
```json
{
  "records": [
    {
      "id": "recPROOF01",
      "createdTime": "2025-01-15T12:00:00.000Z",
      "fields": {
        "Proof_ID": "proof_001",
        "Sprint_ID": "sprint_001",
        "Result": "success",
        "Token": "abc123xyz",
        "Timestamp": "2025-01-15T12:00:00Z"
      }
    }
  ]
}
```

**Postman Setup:**
- Method: `GET`
- URL: `https://drop2.fullpotential.ai/proof`
- Headers: `Content-Type: application/json`

---

### 9. POST /daily-digest
**Purpose:** Generate daily analytics report

**Request:**
```http
POST https://drop2.fullpotential.ai/daily-digest
Content-Type: application/json
```

**Response Schema:**
```json
{
  "Date": "2025-01-15",
  "Total_Droplets": 13,
  "Active_Droplets": 11,
  "Uptime_Percentage": 95.5,
  "New_Sprints_Today": 3,
  "Total_Sprints": 45,
  "Completed_Sprints": 38,
  "Active_Sprints": 5,
  "Pending_Sprints": 2,
  "Total_Proofs": 120,
  "Verified_Proofs": 115,
  "Average_CPU": 42.3,
  "Average_RAM": 65.8,
  "Daily_Summary": "System running smoothly"
}
```

**Postman Setup:**
- Method: `POST`
- URL: `https://drop2.fullpotential.ai/daily-digest`
- Headers: `Content-Type: application/json`
- Body: (empty or `{}`)

---

## 🔗 For Nexus Integration (Suresh)

### Recommended Endpoint for Cross-Droplet Metrics

**Use:** `POST /heartbeats`

**When to call:** Every 60 seconds from each droplet

**Payload Format:**
```json
{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active"
}
```

**Field Descriptions:**
- `Cell_ID` (string, required): Your droplet identifier (e.g., "droplet_13")
- `CPU_Usage` (number, required): CPU usage percentage (0-100)
- `RAM_Usage` (number, required): RAM usage in MB
- `Status` (string, required): "active", "inactive", or "error"
- Note: DO NOT include Timestamp - Airtable auto-generates it

---

## 🧪 Testing in Postman

### Quick Setup Steps:

1. **Create New Collection:** "Droplet 2 - Dashboard API"

2. **Add Environment Variables:**
   - Variable: `base_url`
   - Value: `https://drop2.fullpotential.ai`

3. **Test Heartbeat Submission:**
   - Create new request: "Submit Heartbeat"
   - Method: POST
   - URL: `{{base_url}}/heartbeats`
   - Body → raw → JSON:
   ```json
   {
     "Cell_ID": "droplet_13",
     "CPU_Usage": 45.2,
     "RAM_Usage": 512,
     "Status": "active"
   }
   ```
   - Click "Send"

4. **Test Get Heartbeats:**
   - Create new request: "Get Heartbeats"
   - Method: GET
   - URL: `{{base_url}}/heartbeats`
   - Click "Send"

---

## 📝 Notes for Integration

- **DO NOT send Timestamp field** - Airtable rejects it and auto-generates createdTime
- Status values: "active", "inactive", "error"
- CPU_Usage is a percentage (0-100)
- RAM_Usage is in megabytes (MB)
- All endpoints return Airtable record format with `id`, `createdTime`, and `fields`

---

## 🆘 Support

**Steward:** Haythem Timoumi  
**Droplet:** #2 (Dashboard)  
**Status:** Active and ready for integration

For questions or issues, contact via team chat.
