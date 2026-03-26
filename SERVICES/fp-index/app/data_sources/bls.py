"""
BLS (Bureau of Labor Statistics) Data Connector
================================================

Fetches real employment and wage data from the BLS Public Data API v2.
Uses the Occupational Employment and Wage Statistics (OEWS) survey.

Series ID format (25 chars):
  OE + U + areatype(1) + area(7) + industry(6) + occupation(6) + datatype(2)

National employment: OEUN0000000000000{SOC}01
National median wage: OEUN0000000000000{SOC}13

API limits (no key): 10 series/request, 25 requests/day
API limits (with key): 50 series/request, 500 requests/day
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("fp_index.bls")

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_KEY = os.getenv("BLS_API_KEY", "")

SOC_CODES = {
    "legal_doc_review": "232011",
    "legal_research": "232011",
    "code_generation": "151252",
    "qa_testing": "151253",
    "it_support": "151232",
    "customer_service_basic": "434051",
    "call_center": "434051",
    "financial_analysis": "132051",
    "bookkeeping": "433031",
    "tax_preparation": "132082",
    "radiology": "291224",
    "medical_coding": "292072",
    "medical_transcription": "319094",
    "copywriting": "273043",
    "graphic_design_basic": "271024",
    "translation": "273091",
    "data_entry": "439021",
    "scheduling": "436014",
    "executive_assistant": "436011",
    "tutoring": "253041",
    "grading": "251000",
    "warehouse_picking": "537065",
    "truck_driving": "533032",
    "literature_review": "190000",
    "market_research": "131161",
}


def _build_series_id(soc_code: str, datatype: str = "01") -> str:
    """Build a 25-char OEWS series ID for national data.
    
    datatype: 01=employment, 13=annual median wage
    """
    return f"OEUN0000000000000{soc_code}{datatype}"


async def fetch_bls_data() -> dict[str, dict]:
    """Fetch employment and median wage for all 25 categories from BLS.
    
    Returns: {category_id: {"employment": int, "median_salary": float, "year": str}}
    """
    unique_socs = {}
    for cat_id, soc in SOC_CODES.items():
        if soc not in unique_socs:
            unique_socs[soc] = []
        unique_socs[soc].append(cat_id)

    employment_series = {soc: _build_series_id(soc, "01") for soc in unique_socs}
    wage_series = {soc: _build_series_id(soc, "13") for soc in unique_socs}

    all_series_ids = list(employment_series.values()) + list(wage_series.values())

    soc_by_series = {}
    for soc, sid in employment_series.items():
        soc_by_series[sid] = (soc, "employment")
    for soc, sid in wage_series.items():
        soc_by_series[sid] = (soc, "median_salary")

    batch_size = 50 if BLS_API_KEY else 10
    batches = [all_series_ids[i:i+batch_size] for i in range(0, len(all_series_ids), batch_size)]

    raw_data: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for batch_idx, batch in enumerate(batches):
            payload = {"seriesid": batch}
            if BLS_API_KEY:
                payload["registrationkey"] = BLS_API_KEY

            try:
                resp = await client.post(BLS_API_URL, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"BLS API batch {batch_idx}: HTTP {resp.status_code}")
                    continue

                data = resp.json()
                if data.get("status") != "REQUEST_SUCCEEDED":
                    msgs = data.get("message", [])
                    logger.warning(f"BLS API batch {batch_idx}: {msgs}")
                    continue

                for series in data.get("Results", {}).get("series", []):
                    sid = series.get("seriesID", "")
                    if sid not in soc_by_series:
                        continue
                    soc, field = soc_by_series[sid]

                    series_data = series.get("data", [])
                    if not series_data:
                        continue

                    latest = series_data[0]
                    value_str = latest.get("value", "0")
                    year = latest.get("year", "")

                    try:
                        value = float(value_str.replace(",", ""))
                    except ValueError:
                        continue

                    if soc not in raw_data:
                        raw_data[soc] = {"year": year}
                    raw_data[soc][field] = value
                    raw_data[soc]["year"] = year

                logger.info(f"BLS API batch {batch_idx}: got {len(data.get('Results', {}).get('series', []))} series")

            except Exception as e:
                logger.warning(f"BLS API batch {batch_idx} failed: {e}")

            if batch_idx < len(batches) - 1:
                await asyncio.sleep(1.0)

    results = {}
    for cat_id, soc in SOC_CODES.items():
        if soc in raw_data:
            d = raw_data[soc]
            results[cat_id] = {
                "employment": int(d.get("employment", 0)),
                "median_salary": d.get("median_salary", 0.0),
                "year": d.get("year", ""),
                "soc_code": soc,
            }

    logger.info(f"BLS data fetched for {len(results)}/{len(SOC_CODES)} categories")
    return results


async def update_categories_from_bls():
    """Fetch BLS data and update JobCategoryRow records with real numbers."""
    from ..models.database import JobCategoryRow, async_session

    bls_data = await fetch_bls_data()
    if not bls_data:
        logger.warning("No BLS data returned — skipping update")
        return 0

    updated = 0
    async with async_session() as session:
        for cat_id, data in bls_data.items():
            row = await session.get(JobCategoryRow, cat_id)
            if not row:
                continue

            changed = False
            if data["employment"] > 0 and row.total_us_employment != data["employment"]:
                prev_emp = row.total_us_employment or 0
                row.total_us_employment = data["employment"]
                if prev_emp > 0:
                    pct_change = (data["employment"] - prev_emp) / prev_emp * 100
                    row.gap_velocity = round(pct_change, 2)
                changed = True
            if data["median_salary"] > 0 and row.median_salary != data["median_salary"]:
                row.median_salary = data["median_salary"]
                changed = True

            if changed:
                row.last_updated = datetime.now(timezone.utc)
                updated += 1

        await session.commit()

    logger.info(f"Updated {updated} categories with BLS data (year: {next(iter(bls_data.values()), {}).get('year', '?')})")
    return updated
