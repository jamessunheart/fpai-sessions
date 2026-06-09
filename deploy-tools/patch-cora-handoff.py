#!/usr/bin/env python3
"""Patch CORA's build_context to read the System Handoff reference file."""

CORA_FILE = "/opt/fpai/cora-loop/agents/cora.py"

HANDOFF_BLOCK = '''
    # Read System Handoff — permanent identity and design principles
    try:
        import os as _os
        handoff_path = "/opt/fpai/system-handoff.json"
        if _os.path.exists(handoff_path):
            with open(handoff_path) as _hf:
                handoff = json.loads(_hf.read())
            hc = handoff.get("handoff", {})
            parts.append("SYSTEM IDENTITY (from System Handoff):")
            sid = hc.get("system_identity", {})
            parts.append("  What we are: " + sid.get("what_we_are", ""))
            parts.append("  Moat: " + sid.get("moat", ""))
            parts.append("  Sequence: " + hc.get("sequence", ""))
            parts.append("  Product ladder: " + " | ".join(p.get("name", "") for p in hc.get("product_ladder", [])))
            pitch = hc.get("core_pitch", {})
            parts.append("  Market pitch: " + pitch.get("market", ""))
            parts.append("")
            parts.append("DESIGN PRINCIPLES:")
            for dp in hc.get("design_principles", []):
                parts.append("  - " + dp)
            parts.append("")
            parts.append("STRATEGIC WARNING: " + hc.get("strategic_warning", ""))
            parts.append("SUNHEART RULE: " + hc.get("sunheart_rule", ""))
            parts.append("")
    except Exception:
        pass

'''

with open(CORA_FILE) as f:
    code = f.read()

MARKER = "    # Seed context (always included"
if MARKER in code:
    if "SYSTEM IDENTITY (from System Handoff)" not in code:
        code = code.replace(MARKER, HANDOFF_BLOCK + "    " + MARKER.lstrip())
        with open(CORA_FILE, "w") as f:
            f.write(code)
        print("SUCCESS: CORA patched with System Handoff reading")
    else:
        print("SKIP: System Handoff reading already present")
else:
    print("ERROR: Could not find insertion marker")
