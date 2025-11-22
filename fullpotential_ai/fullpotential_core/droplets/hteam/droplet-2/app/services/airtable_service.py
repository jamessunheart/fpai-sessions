import requests
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..config import settings
from ..utils.logging import get_logger

log = get_logger(__name__)


class AirtableService:
    def __init__(self):
        self.api_key = settings.airtable_api_key
        self.base_id = settings.airtable_base_id
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Airtable API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.error(f"Airtable API error: {str(e)}")
            raise Exception(f"Airtable API error: {str(e)}")

    # Generic CRUD operations
    def get_records(self, table_name: str) -> Dict[str, Any]:
        """Get all records from a table"""
        return self._make_request("GET", table_name)

    def create_record(self, table_name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in a table"""
        data = {"records": [{"fields": fields}]}
        return self._make_request("POST", table_name, data)

    def update_record(self, table_name: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record in a table"""
        data = {"records": [{"id": record_id, "fields": fields}]}
        return self._make_request("PATCH", table_name, data)

    def delete_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Delete a record from a table"""
        return self._make_request("DELETE", f"{table_name}/{record_id}")

    # Bulk operations
    def write_sample_data(self) -> Dict[str, Any]:
        """Push sample data to all Airtable tables"""
        results = {}
        unique_id = random.randint(1000, 9999)
        
        # Sample data for each table
        tables_data = {
            "Sprints": {
                "Sprint_ID": f"SP-API-{unique_id}",
                "Name": "API Test Sprint",
                "Dev_Name": "API Bot",
                "Status": "Pending",
                "Time_Spent_hr": 2,
                "Notes": "API test successful"
            },
            "Cells": {
                "Cell_ID": f"CL-API-{unique_id}",
                "Role": "Builder",
                "IP_Address": f"192.168.1.{unique_id % 255}",
                "Health_Status": "OK",
                "Cost_per_hr": 0.007
            },
            "Proof": {
                "Proof_ID": f"PR-API-{unique_id}",
                "Sprint_ID": f"SP-API-{unique_id}",
                "Result": "All endpoints working",
                "Token": f"api_token_{unique_id}",
                "Timestamp": datetime.now().strftime("%Y-%m-%d")
            },
            "Heartbeats": {
                "Cell_ID": f"CL-API-{unique_id}",
                "CPU_Usage": random.randint(20, 80),
                "RAM_Usage": random.randint(30, 90),
                "Status": "Healthy"
            }
        }
        
        for table_name, fields in tables_data.items():
            try:
                result = self.create_record(table_name, fields)
                results[table_name] = {"status": "success", "data": result}
                log.info(f"✅ {table_name}: Created sample record")
            except Exception as e:
                results[table_name] = {"status": "error", "error": str(e)}
                log.error(f"❌ {table_name}: {str(e)}")
        
        return results

    def read_all_records(self) -> Dict[str, Any]:
        """Fetch records from all Airtable tables"""
        results = {}
        tables = ["Sprints", "Cells", "Proof", "Heartbeats"]
        
        for table in tables:
            try:
                data = self.get_records(table)
                results[table] = data
                record_count = len(data.get('records', []))
                log.info(f"📖 Read {table}: {record_count} records")
            except Exception as e:
                results[table] = {"error": str(e)}
                log.error(f"❌ Read {table}: {str(e)}")
        
        return results


# Global instance
airtable_service = AirtableService()