#!/usr/bin/env python3
"""
Research Librarian CLI

A tool to review, curate, and publish research papers from a staging area
to the live website. Now with AI powers!

Usage:
    python3 research_librarian.py --review
    python3 research_librarian.py --scan-system
    python3 research_librarian.py --synthesize "Topic Name"
"""
import argparse
import os
import shutil
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
SCRIPT_DIR = Path(__file__).parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[1]
INCOMING_DIR = SCRIPT_DIR / "_incoming"

# Define PUBLISH_DIR globally
PUBLISH_DIR = WORKSPACE_ROOT / "docs" / "resources" / "docs" / "autonomous-research-agent" / "papers"
if not PUBLISH_DIR.exists():
    PUBLISH_DIR = WORKSPACE_ROOT / "docs" / "papers"

PAPERS_INDEX_PATH = WORKSPACE_ROOT / "fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/papers.json"

# Config
MAX_TEXT_LENGTH = 100000
ALLOWED_EXTENSIONS = {'.pdf', '.md', '.txt', '.docx'}
IGNORE_DIRS = {
    '.git', 'node_modules', 'venv', '__pycache__', '.cursor', 
    'fullpotential_ai', 'site-packages', 'build', 'dist', 
    'terminals', 'tmp', 'temp'
}

class LLMClient:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        # Fallback: check for .env in workspace root
        if not api_key:
            env_path = WORKSPACE_ROOT / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                
        self.client = Anthropic(api_key=api_key) if api_key else None
        if not self.client:
            # Silent failure for scan mode to avoid spamming console, will return unknown classification
            pass

    def analyze_paper(self, text: str) -> Dict[str, str]:
        """
        Analyzes paper text to suggest a title and summary.
        """
        if not self.client:
            return {"title": "", "summary": "", "tags": []}

        prompt = f"""
        Analyze the following research paper excerpt and provide:
        1. A clean, academic filename (ending in .pdf or .md). Use underscores for spaces.
        2. A 1-sentence summary for a public library index.
        3. A list of 3-5 comma-separated tags (e.g. #Economics, #Consciousness).
        4. A safety check: Does this look like a valid research paper? If it looks like code, secrets, or a system file, verify: false.

        Format the output as JSON:
        {{
            "filename": "suggested_name.pdf",
            "summary": "The summary text.",
            "tags": ["#Tag1", "#Tag2"],
            "is_valid_paper": true/false,
            "warning": "Warning message if invalid"
        }}

        Paper Excerpt:
        {text[:15000]}
        """
        
        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            content = message.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            
            return json.loads(content)
        except Exception as e:
            print(f"Error analyzing paper: {e}")
            return {"title": "", "summary": "", "tags": []}

    def classify_confidentiality(self, text: str, filename: str) -> Dict:
        """
        Determines if a file is SAFE (Public) or CONFIDENTIAL (Internal).
        """
        # Fallback for when API is missing or fails:
        if not self.client:
            # Heuristic Fallback:
            # If it contains "Manifesto", "Paper", "Report" in title -> Lean Public
            # If it contains "Key", "Secret", "Password" -> Lean Private
            lower_name = filename.lower()
            if any(x in lower_name for x in ["manifesto", "paper", "whitepaper", "report", "framework", "guide"]):
                return {"classification": "PUBLIC", "confidence": 50, "reason": "Heuristic match (No AI)"}
            return {"classification": "UNKNOWN", "reason": "AI unavailable"}

        prompt = f"""
        You are the Guardian of Trust and Public Safety for the Full Potential OS.
        Task: Evaluate this document for public release.
        
        CRITICAL MISSION:
        - Build trust with the public.
        - Share knowledge that aids the greater good (Regenerative/Conscious).
        - PROTECT the mission from self-sabotage (leaking secrets, internal strategies, or unpolished chaos).

        STRICT RULES for "CONFIDENTIAL" (Do NOT Publish):
        - Contains API keys, passwords, tokens, or credentials.
        - Contains personal PII (phone numbers, home addresses, bank accounts).
        - Explicitly marked "Internal Use Only", "Confidential", "Top Secret", "Draft".
        - Raw code files, system logs, or config files (unless it's a specific code paper).
        - Content that sounds like "evil plan", "manipulation", or "extraction" (we want regenerative).
        - Unfinished drafts or rough notes that would look unprofessional.

        RULES for "PUBLIC" (Safe to Publish):
        - Research papers, finished manifestos, educational guides.
        - Positive, constructive content aligned with human potential.
        - General business philosophy (if verified safe).

        Filename: {filename}
        
        Document Excerpt:
        {text[:10000]}

        Format Output JSON:
        {{
            "classification": "PUBLIC" | "CONFIDENTIAL",
            "confidence": 0-100,
            "reason": "Detailed explanation of why it is safe or unsafe based on the mission."
        }}
        """
        
        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            content = message.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            return json.loads(content)
        except Exception:
            # If AI fails, fall back to heuristic
            lower_name = filename.lower()
            if any(x in lower_name for x in ["manifesto", "paper", "whitepaper", "report", "framework", "guide"]):
                return {"classification": "PUBLIC", "confidence": 50, "reason": "Heuristic match (AI Failed)"}
            return {"classification": "UNKNOWN", "reason": "AI Error"}

    def synthesize(self, topic: str, papers: List[Dict]) -> str:
        if not self.client:
            return f"# Synthesis: {topic}\n\n*Error: AI client not available.*"

        context = ""
        for p in papers:
            context += f"\n--- Paper: {p['title']} ---\n{p['text'][:5000]}\n"

        prompt = f"""
        You are a Senior Research Librarian for the Full Potential OS.
        Task: Write a comprehensive Synthesis Paper on the topic: "{topic}".
        Source Material: {context}
        Instructions: Write in valid Markdown. Structure: Title, Executive Summary, Key Themes, Unified Insights, Conclusion, References.
        """

        try:
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"# Error generating synthesis\n\n{e}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def extract_text(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    if file_path.suffix.lower() in ['.md', '.txt', '.py', '.sh', '.json', '.yaml']:
        try:
            return file_path.read_text(errors='ignore')
        except:
            return ""
    elif file_path.suffix.lower() == '.pdf':
        try:
            import logging
            # Suppress PDF reader warnings
            logging.getLogger("pypdf").setLevel(logging.ERROR)
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages[:5]:
                text += page.extract_text() + "\n"
            return text
        except:
            # Try reading as text if not a real PDF
            try:
                return file_path.read_text(errors='ignore')
            except:
                return ""
    return ""

def get_file_info(file_path: Path) -> str:
    stat = file_path.stat()
    size_kb = round(stat.st_size / 1024, 1)
    return f"Size: {size_kb} KB | Type: {file_path.suffix}"

def update_index():
    print("\n🔄 Updating Research Index (papers.json)...")
    indexer_script = SCRIPT_DIR / "build_papers_index.py"
    try:
        subprocess.run([sys.executable, str(indexer_script), "--json"], check=True)
        print("✅ Index updated successfully.")
    except subprocess.CalledProcessError:
        print("❌ Failed to update index.")

def scan_system_mode(llm: LLMClient):
    print("\n🕵️  Scanning system for potential research papers...")
    print(f"    Root: {WORKSPACE_ROOT}")
    print("    Excluding: " + ", ".join(list(IGNORE_DIRS)[:5]) + "...")
    
    candidates = []
    
    # Walk the filesystem
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            file_path = Path(root) / file
            
            # Quick Filter 1: Extension
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
                
            # Quick Filter 2: Not already in papers or incoming
            if "papers" in str(file_path) or "_incoming" in str(file_path):
                continue
                
            # Quick Filter 3: Size (skip tiny files or huge blobs)
            if file_path.stat().st_size < 1000 or file_path.stat().st_size > 10 * 1024 * 1024:
                continue
                
            candidates.append(file_path)
            
    print(f"\n🔍 Found {len(candidates)} potential candidates.")
    print("🧠 Analyzing for classification (Public vs Confidential)...")
    
    safe_count = 0
    
    if not INCOMING_DIR.exists():
        INCOMING_DIR.mkdir(parents=True)

    for idx, fp in enumerate(candidates):
        # Progress bar effect with overwrite
        print(f"[{idx+1}/{len(candidates)}] Checking: {fp.name[:40].ljust(40)}", end="\r")
        
        text = extract_text(fp)
        if not text:
            continue
            
        # Heuristic check before expensive LLM call
        # If it looks like code or config, skip
        if "import " in text[:100] or "def " in text[:100] or "{" in text[:50]:
            continue
            
        result = llm.classify_confidentiality(text, fp.name)
        
        if result.get("classification") == "PUBLIC":
            # It's safe! Copy to inbox.
            safe_count += 1
            dest = INCOMING_DIR / fp.name
            # Avoid overwriting if name exists
            if dest.exists():
                dest = INCOMING_DIR / f"{fp.stem}_{safe_count}{fp.suffix}"
            
            shutil.copy2(fp, dest)
            # Clear line to show success
            print(f"\033[K✅ SAFE: {fp.name} -> Inbox ({result.get('confidence')}% confidence)")

    print(f"\n\n🏁 Scan Complete.")
    print(f"🎉 Identified {safe_count} SAFE papers and moved them to {INCOMING_DIR.relative_to(WORKSPACE_ROOT)}")
    print("Run 'python3 research_librarian.py --review' to verify and publish them.")


def review_mode(llm: LLMClient):
    target_dir = PUBLISH_DIR 
    if not INCOMING_DIR.exists():
        INCOMING_DIR.mkdir(parents=True)
        print(f"Created staging directory: {INCOMING_DIR}")
        return

    files = [f for f in INCOMING_DIR.iterdir() if f.is_file() and f.name != ".gitkeep"]
    
    if not files:
        print(f"No files found in {INCOMING_DIR.relative_to(WORKSPACE_ROOT)}")
        return

    print(f"\n📚 Found {len(files)} papers in Inbox.\n")
    processed_count = 0

    for file_path in files:
        clear_screen()
        print(f"--- Reviewing {processed_count + 1}/{len(files)} ---")
        print(f"📄 File: {file_path.name}")
        print(f"ℹ️  {get_file_info(file_path)}")
        
        print("🧠 AI Analyzing...")
        text = extract_text(file_path)
        analysis = llm.analyze_paper(text)
        
        suggested_name = analysis.get('filename', file_path.name)
        summary = analysis.get('summary', 'No summary generated.')
        tags = analysis.get('tags', [])
        is_valid = analysis.get('is_valid_paper', True)
        warning = analysis.get('warning', '')

        print(f"\n💡 AI Suggestion: {suggested_name}")
        print(f"📝 Summary: {summary}")
        print(f"🏷️  Tags: {', '.join(tags)}")
        
        if not is_valid:
            print(f"\n⚠️  SECURITY WARNING: {warning}")
        
        print("\nActions:")
        print("[A]pprove & Publish")
        print("[R]ename & Publish")
        print("[D]elete")
        print("[S]kip")
        print("[Q]uit")
        
        choice = input("\n> ").lower().strip()
        
        if choice == 'q':
            break
        elif choice == 's':
            continue
        elif choice == 'd':
            if input("Confirm delete? (y/n): ").lower() == 'y':
                os.remove(file_path)
                print("Deleted.")
                processed_count += 1
        elif choice in ['a', 'r']:
            if not is_valid:
                 if input("⚠️  CONFIRM PUBLISH OF FLAGGED FILE? (yes/no): ").lower() != 'yes':
                     continue

            final_name = suggested_name
            if choice == 'r':
                final_name = input(f"Enter filename ({suggested_name}): ").strip() or suggested_name
            
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                
            dest = target_dir / final_name
            shutil.move(str(file_path), str(dest))
            print(f"✅ Published to {dest.name}")
            processed_count += 1
            
        import time
        time.sleep(1)

    if processed_count > 0:
        update_index()

def synthesize_mode(llm: LLMClient, topic: str):
    target_dir = PUBLISH_DIR
    if not PAPERS_INDEX_PATH.exists():
        print(f"❌ Index not found at {PAPERS_INDEX_PATH}")
        return
        
    with open(PAPERS_INDEX_PATH, 'r') as f:
        index = json.load(f)
    papers = index.get('papers', [])
    
    topic_terms = topic.lower().split()
    relevant_papers = []
    
    for p in papers:
        score = 0
        text_to_search = (p.get('title', '') + " " + " ".join(p.get('tags', []))).lower()
        for term in topic_terms:
            if term in text_to_search:
                score += 1
        if score > 0:
            rel_path = p.get('path')
            if not rel_path: continue
            full_path = WORKSPACE_ROOT / rel_path
            text = extract_text(full_path)
            if text and len(text) > 100:
                relevant_papers.append({"title": p['title'], "text": text})
        if len(relevant_papers) >= 10: break
    
    if not relevant_papers:
        print("❌ No relevant papers found.")
        return

    print(f"\n🧠 Reading {len(relevant_papers)} papers...")
    result = llm.synthesize(topic, relevant_papers)
    
    if not target_dir.exists():
        try: target_dir.mkdir(parents=True, exist_ok=True)
        except: target_dir = Path.cwd()

    filename = f"Synthesis_{topic.replace(' ', '_')}.md"
    output_path = target_dir / filename
    output_path.write_text(result)
    print(f"✅ Synthesis Saved: {output_path}")
    update_index()

def main():
    parser = argparse.ArgumentParser(description="Research Librarian Tool")
    parser.add_argument("--review", action="store_true", help="Interactive review mode")
    parser.add_argument("--scan-system", action="store_true", help="Scan system for safe papers to ingest")
    parser.add_argument("--synthesize", type=str, help="Topic to synthesize into a new paper")
    args = parser.parse_args()

    llm = LLMClient()

    if args.review:
        review_mode(llm)
    elif args.scan_system:
        scan_system_mode(llm)
    elif args.synthesize:
        synthesize_mode(llm, args.synthesize)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
