#!/usr/bin/env python3
"""
Self-Healing Link Checker
Scans the website for broken links and attempts to fix them or report them.
"""
import os
from pathlib import Path
from typing import List, Dict
import re

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WEBSITE_ROOT = WORKSPACE_ROOT / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend"

def scan_links(directory: Path) -> List[Dict]:
    broken_links = []
    print(f"🔍 Scanning {directory} for broken links...")
    
    for file_path in directory.rglob("*.html"):
        content = file_path.read_text(errors='ignore')
        # Find all hrefs
        links = re.findall(r'href=["\'](.*?)["\']', content)
        
        for link in links:
            if link.startswith("http") or link.startswith("#") or link.startswith("mailto:"):
                continue
                
            # Resolve local link
            if link.startswith("/"):
                target = WORKSPACE_ROOT / link.lstrip("/")
            else:
                target = file_path.parent / link
                
            # Check existence
            if not target.exists():
                # Check if it maps to a known service/route (e.g. /research)
                if link == "research.html":
                    # Verify if research.html actually exists nearby
                    if not (file_path.parent / "research.html").exists():
                         broken_links.append({
                            "source": file_path,
                            "link": link,
                            "target": target
                        })
                else:
                    broken_links.append({
                        "source": file_path,
                        "link": link,
                        "target": target
                    })
                    
    return broken_links

def heal_links(broken_links: List[Dict]):
    print(f"🩹 Attempting to heal {len(broken_links)} broken links...")
    
    for error in broken_links:
        link = error['link']
        source = error['source']
        
        # Heuristic 1: Is it the Papers Index?
        if "PAPERS_INDEX.md" in link:
            print(f"   Fixing Papers Index link in {source.name}")
            content = source.read_text()
            new_content = content.replace(link, "research.html")
            source.write_text(new_content)
            print("   ✅ Redirected to research.html")

if __name__ == "__main__":
    if not WEBSITE_ROOT.exists():
        print(f"❌ Website root not found at {WEBSITE_ROOT}")
        exit(1)
        
    broken = scan_links(WEBSITE_ROOT)
    if broken:
        heal_links(broken)
    else:
        print("✅ No broken links found.")

