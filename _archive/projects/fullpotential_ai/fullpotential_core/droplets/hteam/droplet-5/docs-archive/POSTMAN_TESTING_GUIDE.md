# 🧪 Postman Testing Guide - Droplet 2 API

## Quick Start (3 Steps)

### Step 1: Import Collection
1. Open Postman
2. Click **Import** button (top left)
3. Drag and drop `Droplet2_Postman_Collection.json` file
4. Collection "Droplet 2 - Dashboard API" will appear in your sidebar

### Step 2: Test Heartbeat Submission (Most Important for Nexus)
1. In the collection, expand **Heartbeats** folder
2. Click **"Submit Heartbeat (Metrics)"**
3. You'll see the request is already configured:
   - Method: `POST`
   - URL: `https://drop2.fullpotential.ai/heartbeats`
   - Body is pre-filled with example JSON
4. Click **Send** button
5. You should get a 200 OK response with the created record

### Step 3: Verify Data Was Saved
1. Click **"Get All Heartbeats"** in the same folder
2. Click **Send**
3. You should see your submitted heartbeat in the response

---

## 📝 Manual Testing (Without Import)

### Test 1: Submit Metrics (For Suresh/Nexus Integration)

**Setup:**
1. Create new request in Postman
2. Set method to: `POST`
3. Enter URL: `https://drop2.fullpotential.ai/heartbeats`
4. Go to **Headers** tab:
   - Key: `Content-Type`
   - Value: `application/json`
5. Go to **Body** tab:
   - Select **raw**
   - Select **JSON** from dropdown
6. Paste this JSON:

```json
{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active",
  "Timestamp": "2025-01-15T10:30:00Z"
}
```

7. Click **Send**

**Expected Response (200 OK):**
```json
{
  "id": "rec123abc",
  "createdTime": "2025-01-15T10:30:00.000Z",
  "fields": {
    "Cell_ID": "droplet_13",
    "CPU_Usage": 45.2,
    "RAM_Usage": 512,
    "Status": "active",
    "Timestamp": "2025-01-15T10:30:00Z"
  }
}
```

---

### Test 2: Get All Heartbeats

**Setup:**
1. Create new request
2. Set method to: `GET`
3. Enter URL: `https://drop2.fullpotential.ai/heartbeats`
4. Go to **Headers** tab:
   - Key: `Content-Type`
   - Value: `application/json`
5. Click **Send**

**Expected Response (200 OK):**
```json
{
  "records": [
    {
      "id": "rec123abc",
      "createdTime": "2025-01-15T10:30:00.000Z",
      "fields": {
        "Cell_ID": "droplet_13",
        "CPU_Usage": 45.2,
        "RAM_Usage": 512,
        "Status": "active",
        "Timestamp": "2025-01-15T10:30:00Z"
      }
    }
  ]
}
```

---

### Test 3: Create Sprint

**Setup:**
1. Create new request
2. Set method to: `POST`
3. Enter URL: `https://drop2.fullpotential.ai/sprints`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):

```json
{
  "Sprint_ID": "sprint_test_001",
  "Name": "Test Sprint from Postman",
  "Dev_Name": "Haythem",
  "Status": "Active",
  "Time_Spent_hr": 1.0,
  "Notes": "Testing API integration"
}
```

6. Click **Send**

**Expected Response (200 OK):**
```json
{
  "id": "recXYZ789",
  "createdTime": "2025-01-15T11:00:00.000Z",
  "fields": {
    "Sprint_ID": "sprint_test_001",
    "Name": "Test Sprint from Postman",
    "Dev_Name": "Haythem",
    "Status": "Active",
    "Time_Spent_hr": 1.0,
    "Notes": "Testing API integration"
  }
}
```

---

### Test 4: Get All Sprints

**Setup:**
1. Create new request
2. Set method to: `GET`
3. Enter URL: `https://drop2.fullpotential.ai/sprints`
4. Headers: `Content-Type: application/json`
5. Click **Send**

---

## 🔄 Testing Different Droplets

To test metrics from different droplets, just change the `Cell_ID`:

**Droplet 1 (Registry - Liban):**
```json
{
  "Cell_ID": "droplet_1",
  "CPU_Usage": 35.0,
  "RAM_Usage": 256,
  "Status": "active",
  "Timestamp": "2025-01-15T10:30:00Z"
}
```

**Droplet 10 (Orchestrator - Tnsae):**
```json
{
  "Cell_ID": "droplet_10",
  "CPU_Usage": 52.3,
  "RAM_Usage": 768,
  "Status": "active",
  "Timestamp": "2025-01-15T10:30:00Z"
}
```

**Droplet 13 (Nexus - Suresh):**
```json
{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active",
  "Timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 🎯 For Suresh (Nexus Integration)

### Python Example to Send Metrics

```python
import httpx
from datetime import datetime

async def send_metrics_to_dashboard():
    """Send Nexus metrics to Dashboard (Droplet 2)"""
    
    metrics = {
        "Cell_ID": "droplet_13",
        "CPU_Usage": 45.2,
        "RAM_Usage": 512,
        "Status": "active",
        "Timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://drop2.fullpotential.ai/heartbeats",
            json=metrics,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Metrics sent to Dashboard")
            return response.json()
        else:
            print(f"❌ Failed: {response.status_code}")
            return None
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

async function sendMetricsToDashboard() {
  const metrics = {
    Cell_ID: "droplet_13",
    CPU_Usage: 45.2,
    RAM_Usage: 512,
    Status: "active",
    Timestamp: new Date().toISOString()
  };
  
  try {
    const response = await axios.post(
      'https://drop2.fullpotential.ai/heartbeats',
      metrics,
      {
        headers: { 'Content-Type': 'application/json' }
      }
    );
    
    console.log('✅ Metrics sent to Dashboard');
    return response.data;
  } catch (error) {
    console.error('❌ Failed:', error.message);
    return null;
  }
}
```

### cURL Example

```bash
curl -X POST https://drop2.fullpotential.ai/heartbeats \
  -H "Content-Type: application/json" \
  -d '{
    "Cell_ID": "droplet_13",
    "CPU_Usage": 45.2,
    "RAM_Usage": 512,
    "Status": "active",
    "Timestamp": "2025-01-15T10:30:00Z"
  }'
```

---

## ✅ Success Indicators

**Request Successful When:**
- Status code: `200 OK`
- Response contains `id` field (Airtable record ID)
- Response contains `createdTime` field
- Response contains `fields` object with your submitted data

**Common Issues:**
- `400 Bad Request`: Check JSON format, ensure all required fields present
- `404 Not Found`: Check URL spelling
- `500 Server Error`: Backend issue, contact Haythem

---

## 📊 Monitoring Dashboard

After sending metrics via Postman, you can view them in the dashboard:
- Open: `https://dashboard.fullpotential.ai` (or your local dashboard)
- Navigate to **Infrastructure** section
- Your submitted metrics should appear in real-time

---

## 🆘 Troubleshooting

### Issue: "Could not get response"
- Check internet connection
- Verify URL is correct: `https://drop2.fullpotential.ai`
- Try in browser first to confirm API is up

### Issue: "Invalid JSON"
- Ensure Body type is set to **raw** and **JSON**
- Check for missing commas or quotes
- Use JSON validator: jsonlint.com

### Issue: "Timestamp format error"
- Use ISO 8601 format: `2025-01-15T10:30:00Z`
- Include the `Z` at the end for UTC
- Or use: `new Date().toISOString()` in code

---

## 📞 Contact

**Questions?** Contact Haythem (Droplet #2 Steward)

**Status:** ✅ All endpoints tested and working
