import os, json, datetime, hashlib

class BrainGenerator:
    def __init__(self, brain_dir="/brain"):
        self.brain_dir = brain_dir
        os.makedirs(self.brain_dir, exist_ok=True)

    def generate_manifest(self, droplet_info):
        manifest = {
            "droplet": droplet_info.get("name","Unknown"),
            "id": droplet_info.get("id","N/A"),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "hash": hashlib.sha256(str(droplet_info).encode()).hexdigest(),
            "connections": droplet_info.get("connections",[])
        }
        path = os.path.join(self.brain_dir,"manifest.json")
        with open(path,"w") as f: json.dump(manifest,f,indent=2)
        return manifest
