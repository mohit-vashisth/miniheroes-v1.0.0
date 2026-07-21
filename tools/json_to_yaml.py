import json, yaml
from pathlib import Path

# Project root = parent of the tools folder
ROOT = Path(__file__).resolve().parent.parent          # <-- bas ye line change karo

JSON_FILE = ROOT / "templates" / "templates.json"
YAML_FILE = ROOT / "templates" / "scripts" / "auto_steps.yaml"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

steps = []
for item in data:
    img = item["image"]
    x = item["position"]["x"]
    y = item["position"]["y"]
    sec = item.get("seconds", 1)

    steps.append({
        "wait": {
            "image": img,
            "retries": 3,
            "confidence": 0.8
        }
    })
    steps.append({
        "tap": {
            "image": img,
            "x": x,
            "y": y
        }
    })
    steps.append({
        "sleep": {
            "seconds": sec
        }
    })

yaml_data = {"steps": steps}

YAML_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(YAML_FILE, "w", encoding="utf-8") as f:
    yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

print(f"Converted {len(steps)} steps → {YAML_FILE}")