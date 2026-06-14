#!/usr/bin/env python3
"""
Service Discovery Scanner
Scans all services in agents/services/ and creates a comprehensive registry
"""
import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

SERVICES_DIR = Path("/Users/jamessunheart/Development/SERVICES")
OUTPUT_FILE = Path("/Users/jamessunheart/Development/agents/services/SERVICE_CATALOG.json")

def extract_port(content: str) -> Optional[int]:
    """Extract port number from text"""
    patterns = [
        r'[Pp]ort:?\s*(\d{4,5})',
        r'localhost:(\d{4,5})',
        r':(\d{4,5})/',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
    return None

def check_service_health(port: int) -> Dict:
    """Check if service is responding"""
    try:
        resp = requests.get(f"http://localhost:{port}/health", timeout=1)
        if resp.status_code == 200:
            return {
                "status": "online",
                "health_data": resp.json()
            }
    except:
        pass
    return {"status": "offline", "health_data": None}

def scan_service_directory(service_dir: Path) -> Dict:
    """Scan a single service directory"""
    service = {
        "name": service_dir.name,
        "path": str(service_dir),
        "port": None,
        "status": "unknown",
        "health": None,
        "files": {
            "spec": False,
            "readme": False,
            "main": False,
            "requirements": False
        },
        "capabilities": [],
        "tech_stack": [],
        "description": None,
        "scanned_at": datetime.utcnow().isoformat() + "Z"
    }

    # Check for key files
    spec_file = service_dir / "SPEC.md"
    readme_file = service_dir / "README.md"
    main_file = service_dir / "main.py"
    req_file = service_dir / "requirements.txt"

    if spec_file.exists():
        service["files"]["spec"] = True
        try:
            content = spec_file.read_text()

            # Extract port
            port = extract_port(content)
            if port:
                service["port"] = port

            # Extract description (first paragraph after Purpose/Description)
            desc_match = re.search(r'## (?:Purpose|Description)\s*\n\n(.+?)(?:\n\n|\n##)', content, re.DOTALL)
            if desc_match:
                service["description"] = desc_match.group(1).strip()[:200]

            # Extract capabilities
            cap_match = re.search(r'## (?:Core Capabilities|Capabilities|Features)\s*\n\n(.+?)(?:\n##)', content, re.DOTALL)
            if cap_match:
                caps = re.findall(r'[-*]\s*\*\*(.+?)\*\*', cap_match.group(1))
                service["capabilities"] = caps[:10]

            # Extract tech stack
            tech_match = re.search(r'## Tech Stack\s*\n\n(.+?)(?:\n##)', content, re.DOTALL)
            if tech_match:
                techs = re.findall(r'[-*]\s*\*\*(?:Framework|Language|Library):\*\*\s*(.+)', tech_match.group(1))
                service["tech_stack"] = techs[:5]

        except Exception as e:
            print(f"Error parsing SPEC for {service_dir.name}: {e}")

    if readme_file.exists():
        service["files"]["readme"] = True
        if not service["port"]:
            try:
                content = readme_file.read_text()
                port = extract_port(content)
                if port:
                    service["port"] = port
            except:
                pass

    if main_file.exists():
        service["files"]["main"] = True

    if req_file.exists():
        service["files"]["requirements"] = True

    # Check health if we have a port
    if service["port"]:
        health_result = check_service_health(service["port"])
        service["status"] = health_result["status"]
        service["health"] = health_result["health_data"]

    return service

def scan_all_services() -> List[Dict]:
    """Scan all service directories"""
    services = []

    for item in sorted(SERVICES_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith('.'):
            continue

        # Skip template and system directories
        if item.name in ['_TEMPLATE', 'node_modules', 'venv', '__pycache__']:
            continue

        print(f"Scanning {item.name}...")
        service_info = scan_service_directory(item)
        services.append(service_info)

    return services

def generate_report(services: List[Dict]):
    """Generate summary report"""
    total = len(services)
    online = sum(1 for s in services if s["status"] == "online")
    offline = sum(1 for s in services if s["status"] == "offline")
    unknown = sum(1 for s in services if s["status"] == "unknown")

    with_spec = sum(1 for s in services if s["files"]["spec"])
    with_readme = sum(1 for s in services if s["files"]["readme"])
    with_port = sum(1 for s in services if s["port"])

    report = {
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_services": total,
            "status": {
                "online": online,
                "offline": offline,
                "unknown": unknown
            },
            "documentation": {
                "with_spec": with_spec,
                "with_readme": with_readme,
                "with_port": with_port
            }
        },
        "services": services
    }

    return report

def main():
    print("🔍 Scanning all services in agents/services/...")
    print()

    services = scan_all_services()
    report = generate_report(services)

    # Save to file
    OUTPUT_FILE.write_text(json.dumps(report, indent=2))

    print()
    print("=" * 60)
    print("SERVICE DISCOVERY REPORT")
    print("=" * 60)
    print(f"Total Services: {report['summary']['total_services']}")
    print(f"\nStatus:")
    print(f"  Online:  {report['summary']['status']['online']}")
    print(f"  Offline: {report['summary']['status']['offline']}")
    print(f"  Unknown: {report['summary']['status']['unknown']}")
    print(f"\nDocumentation:")
    print(f"  With SPEC:   {report['summary']['documentation']['with_spec']}")
    print(f"  With README: {report['summary']['documentation']['with_readme']}")
    print(f"  With Port:   {report['summary']['documentation']['with_port']}")
    print()
    print(f"📄 Full catalog saved to: {OUTPUT_FILE}")

    # Print online services
    online_services = [s for s in services if s["status"] == "online"]
    if online_services:
        print()
        print("✅ Online Services:")
        for s in online_services:
            print(f"  • {s['name']} (port {s['port']})")

    # Print offline services with ports (can be restarted)
    offline_with_port = [s for s in services if s["status"] == "offline" and s["port"]]
    if offline_with_port:
        print()
        print("⚠️  Offline Services (can be restarted):")
        for s in offline_with_port:
            print(f"  • {s['name']} (port {s['port']})")

if __name__ == "__main__":
    main()
