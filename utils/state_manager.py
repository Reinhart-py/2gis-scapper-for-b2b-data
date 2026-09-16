import json
import os
from typing import Any, Dict, List, Optional

HISTORY_FILE = ".scraper_history.json"
MAX_HISTORY = 10


def load_all_history() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def push_history_checkpoint(entry: Dict[str, Any]) -> None:
    history = load_all_history()
    # Deduplicate existing entry if present
    history = [h for h in history if not (h.get("engine") == entry.get("engine") and h.get("target") == entry.get("target"))]
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def update_latest_progress(engine: str, target: str, last_page_or_idx: int, total_saved: int) -> None:
    history = load_all_history()
    for h in history:
        if h.get("engine") == engine and h.get("target") == target:
            h["last_step"] = last_page_or_idx
            h["total_saved"] = total_saved
            break
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
