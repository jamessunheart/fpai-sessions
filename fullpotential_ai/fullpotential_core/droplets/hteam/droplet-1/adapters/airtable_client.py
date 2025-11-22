
import os, requests

BASE = "https://api.airtable.com/v0"

class Airtable:
    def __init__(self):
        self.token = os.getenv("AIRTABLE_TOKEN")
        self.base = os.getenv("AIRTABLE_BASE_ID")
        self.table = os.getenv("AIRTABLE_TABLE", "Droplets")
        if not (self.base and self.token):
            raise RuntimeError("Airtable not configured")
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {self.token}"
        self.s.headers["Content-Type"] = "application/json"

    def _url(self, path=""):
        return f"{BASE}/{self.base}/{self.table}{path}"

    def find_by_fqdn(self, fqdn: str):
        # escape single quotes for filterByFormula
        fq = fqdn.replace("'", "\\'")
        params = {"filterByFormula": f"{{fqdn}} = '{fq}'", "pageSize": 1}
        r = self.s.get(self._url(), params=params, timeout=15)
        r.raise_for_status()
        items = r.json().get("records", [])
        return items[0] if items else None

    def create_one(self, fields: dict):
        r = self.s.post(self._url(), json={"records": [{"fields": fields}]}, timeout=15)
        r.raise_for_status()
        return r.json()["records"][0]

    def update_one(self, rec_id: str, fields: dict):
        payload = {"records": [{"id": rec_id, "fields": fields}]}
        r = self.s.patch(self._url(), json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["records"][0]

    def upsert_one(self, fields: dict):
        # Requires "Droplets" to have a field named exactly "fqdn"
        payload = {
            "performUpsert": { "fieldsToMergeOn": ["fqdn"] },
            "records": [ { "fields": fields } ]
        }
        # PATCH supports performUpsert
        r = self.s.patch(self._url(), json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["records"][0]

