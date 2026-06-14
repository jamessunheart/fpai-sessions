import json
import logging
import time
from pathlib import Path
from typing import List, Dict
from .config import settings

logger = logging.getLogger("MissionDispatcher")

class MissionDispatcher:
    """
    Translates High Priorities into Actionable Intents.
    """
    
    def __init__(self):
        self.intents_dir = settings.intents_path
        self.intents_dir.mkdir(parents=True, exist_ok=True)

    async def dispatch(self, priorities: List[Dict]):
        """Dispatch top priorities as intents."""
        if not priorities:
            return

        # Only dispatch the TOP priority to avoid flooding
        top_priority = priorities[0]
        
        # Check if already active (simple duplication check)
        # In real impl, check 'claims' dir
        
        intent_name = f"{top_priority['type']}-{top_priority['target']}"
        intent_file = self.intents_dir / f"{intent_name}.json"
        
        if not intent_file.exists():
            intent = {
                "architect_intent": f"Priority Mission: {top_priority['name']}\nReason: {top_priority['reason']}",
                "droplet_name": top_priority['target'],
                "approval_mode": "auto",
                "auto_deploy": True,
                "generated_by": "Strategic Intelligence Service",
                "score": top_priority['score']
            }
            
            with open(intent_file, 'w') as f:
                json.dump(intent, f, indent=2)
                
            logger.info(f"🚀 Dispatched Mission: {intent_name} (Score: {top_priority['score']})")

