import logging
import orjson
from pathlib import Path
from typing import List, Optional, Any, Dict
from datetime import datetime

logger = logging.getLogger("htmx-table")

def format_date_string(date_str: str, pattern: str) -> str:
    """
    Formats a date string (expected in YYYY-MM-DD) according to the given pattern.
    Supports YYYY, MM, DD placeholders.
    """
    if not date_str or not pattern:
        return date_str
        
    try:
        # Parse the input date (assuming YYYY-MM-DD from the JSON)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Convert user friendly pattern to strftime format
        fmt = pattern.replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d")
        
        return dt.strftime(fmt)
    except ValueError:
        # Return original if parsing fails
        return date_str
    except Exception as e:
        logger.error(f"Error formatting date {date_str} with {pattern}: {e}")
        return date_str

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, 'rb') as f:
            return orjson.loads(f.read())
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return default

def save_json(path: Path, data: Any):
    try:
        with open(path, 'wb') as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    except Exception as e:
        logger.error(f"Error saving {path}: {e}")

def apply_filters(rows: List[Dict[str, Any]], columns: List[Dict[str, Any]], q: Optional[str] = None, column_filters: Dict[str, str] = None, settings: Dict[str, Any] = None):
    result = rows
    
    # Global search
    if q and settings and settings.get("features", {}).get("search"):
        search = q.lower()
        searchable_keys = [col["key"] for col in columns]
        
        filtered_result = []
        for u in result:
            # Check if search term exists in any of the columns
            if any(search in str(u.get(key, '')).lower() for key in searchable_keys):
                filtered_result.append(u)
        result = filtered_result
        
    # Column filters
    if column_filters:
        for key, value in column_filters.items():
            if not value: continue
            needle = value.lower()
            result = [u for u in result if needle in str(u.get(key, '')).lower()]
            
    return result

def apply_sort(rows: List[Dict[str, Any]], sort_key: str, sort_dir: str):
    if not sort_key:
        return rows
        
    reverse = (sort_dir == 'desc')
    
    def sort_val(row):
        val = row.get(sort_key)
        if val is None: return ""
        if isinstance(val, (int, float)): return val
        return str(val).lower()
        
    return sorted(rows, key=sort_val, reverse=reverse)

def get_active_columns(session: Dict[str, Any], all_columns: List[Dict[str, Any]]):
    order = session["columns"]["order"]
    visible = set(session["columns"]["visible"])
    col_map = {c['key']: c for c in all_columns}
    
    return [col_map[key] for key in order if key in visible and key in col_map]
