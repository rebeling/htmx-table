import logging
import math
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.utils import (
    apply_filters,
    apply_sort,
    get_active_columns,
    load_json,
    save_json,
    format_date_string,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("htmx-table")

app = FastAPI()

# --- Config & Data ---
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DATA_PATH = DATA_DIR / "users_1000.json"
SESSION_FILE = DATA_DIR / "sessions.json"
SETTINGS_FILE = DATA_DIR / "app_settings.json"

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["date_format"] = format_date_string

# Global State
DATASET: List[Dict[str, Any]] = []
SESSIONS: Dict[str, Dict[str, Any]] = {}
APP_SETTINGS: Dict[str, Any] = {
    "features": {"search": True, "column_settings": True, "pagination": True},
    "defaults": {"per_page": 10, "per_page_options": [10, 25, 50, 100]},
}

COLUMNS = [
    {"key": "full_name", "label": "Name"},
    {"key": "email", "label": "Email"},
    {"key": "country", "label": "Country"},
    {"key": "status", "label": "Status"},
    {"key": "age", "label": "Age"},
    {"key": "balance_eur", "label": "Balance"},
    {"key": "created_date", "label": "Created"},
]

# Initialize
DATASET = load_json(DATA_PATH, [])
SESSIONS = load_json(SESSION_FILE, {})
APP_SETTINGS = load_json(SETTINGS_FILE, APP_SETTINGS)

# Merge column settings
for key, conf in APP_SETTINGS.get("columns", {}).items():
    for col in COLUMNS:
        if col["key"] == key:
            col.update(conf)


# --- Session Management ---
def get_session(request: Request, response: Response = None) -> Dict[str, Any]:
    sid = request.cookies.get("session_id")
    save_needed = False

    if not sid or sid not in SESSIONS:
        sid = str(uuid.uuid4())
        SESSIONS[sid] = {}
        if response:
            response.set_cookie(key="session_id", value=sid)
        save_needed = True

    session = SESSIONS[sid]
    default_per_page = APP_SETTINGS["defaults"]["per_page"]

    # Ensure defaults
    if "per_page" not in session:
        session["per_page"] = default_per_page
        save_needed = True

    if "columns" not in session:
        session["columns"] = {
            "order": [c["key"] for c in COLUMNS],
            "visible": [c["key"] for c in COLUMNS],
        }
        save_needed = True

    if "sort" not in session:
        session["sort"] = {"key": "created_date", "dir": "desc"}
        save_needed = True

    if "selection" not in session:
        session["selection"] = {"mode": "include", "ids": []}
        save_needed = True

    if save_needed:
        save_json(SESSION_FILE, SESSIONS)

    return session


# --- Routes ---


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"features": APP_SETTINGS["features"]},
    )


@app.get("/table-header", response_class=HTMLResponse)
async def get_table_header(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="header.html",
        context={"features": APP_SETTINGS["features"]},
    )


@app.get("/table-data", response_class=HTMLResponse)
async def get_table_data(
    request: Request,
    response: Response,
    q: Optional[str] = None,
    sort: Optional[str] = None,
    dir: Optional[str] = None,
    page: int = 1,
):
    session = get_session(request, response)

    # Extract column filters
    column_filters = {}
    known_keys = [c["key"] for c in COLUMNS]
    for key, value in request.query_params.items():
        if key in known_keys and value:
            column_filters[key] = value

    # Update session if sort params provided
    if sort:
        new_dir = dir or "asc"
        if session["sort"]["key"] != sort or session["sort"]["dir"] != new_dir:
            session["sort"]["key"] = sort
            session["sort"]["dir"] = new_dir
            save_json(SESSION_FILE, SESSIONS)

    current_sort = session["sort"]

    filtered_data = apply_filters(
        DATASET, COLUMNS, q=q, column_filters=column_filters, settings=APP_SETTINGS
    )
    sorted_data = apply_sort(filtered_data, current_sort["key"], current_sort["dir"])

    # Mark selected rows
    sel_mode = session["selection"]["mode"]
    sel_ids = set(session["selection"]["ids"])
    
    # Calculate selection stats
    total_matching = len(sorted_data)
    if sel_mode == "include":
        selection_count = len(sel_ids)
        is_global_selected = False
    else: # exclude
        selection_count = total_matching - len(sel_ids)
        is_global_selected = (len(sel_ids) == 0)

    for row in sorted_data:
        rid = str(row.get("id", "")) # Ensure we have ID
        if sel_mode == "include":
            row["_selected"] = rid in sel_ids
        else:
            row["_selected"] = rid not in sel_ids

    page_info = None
    if APP_SETTINGS["features"]["pagination"]:
        per_page = session.get("per_page", 10)
        total_items = len(sorted_data)
        total_pages = math.ceil(total_items / per_page)
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        start = (page - 1) * per_page
        end = start + per_page
        paged_data = sorted_data[start:end]
        page_info = {"current": page, "total": total_pages, "total_items": total_items}
    else:
        paged_data = sorted_data[:100]

    active_cols = get_active_columns(session, COLUMNS)

    # Filter string for pagination links
    filter_params = ""
    if column_filters:
        for k, v in column_filters.items():
            if v:
                filter_params += f"&{k}={v}"

    resp = templates.TemplateResponse(
        request=request,
        name="table.html",
        context={
            "rows": paged_data,
            "columns": active_cols,
            "current_sort": current_sort,
            "page_info": page_info,
            "filters": column_filters,
            "filter_params": filter_params,
            "show_filters": APP_SETTINGS["features"].get("column_filters", False),
            "show_row_selection": APP_SETTINGS["features"].get("row_selection", False),
            "selection_info": {
                "count": selection_count,
                "total": total_matching,
                "is_global": is_global_selected,
                "mode": sel_mode
            }
        },
    )
    # Ensure session cookie is preserved
    if response.headers.get("set-cookie"):
        resp.headers["set-cookie"] = response.headers["set-cookie"]
    return resp


@app.get("/table-settings", response_class=HTMLResponse)
async def get_settings_control(request: Request, response: Response):
    if not APP_SETTINGS["features"]["pagination"]:
        return ""

    session = get_session(request, response)
    current = session.get("per_page", 10)
    options = APP_SETTINGS["defaults"]["per_page_options"]

    resp = templates.TemplateResponse(
        request=request,
        name="per_page.html",
        context={"options": options, "current": current},
    )
    if response.headers.get("set-cookie"):
        resp.headers["set-cookie"] = response.headers["set-cookie"]
    return resp


@app.get("/table-settings-modal", response_class=HTMLResponse)
async def get_settings_modal(request: Request, response: Response, q: Optional[str] = None):
    if not APP_SETTINGS["features"]["column_settings"]:
        return ""

    session = get_session(request, response)
    order = session["columns"]["order"]
    visible = set(session["columns"]["visible"])
    col_map = {c["key"]: c for c in COLUMNS}

    all_keys = list(order) + [c["key"] for c in COLUMNS if c["key"] not in order]

    items = []
    for key in all_keys:
        col = col_map.get(key)
        if not col:
            continue
        items.append({
            "key": key,
            "label": col["label"],
            "visible": key in visible,
            "custom_pattern": col.get("custom_pattern"),
            "default_pattern": col.get("default_pattern")
        })

    resp = templates.TemplateResponse(
        request=request, name="modal.html", context={"items": items, "q": q}
    )
    if response.headers.get("set-cookie"):
        resp.headers["set-cookie"] = response.headers["set-cookie"]
    return resp


@app.post("/table-settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    response: Response,
    per_page: Optional[int] = Form(None),
    q: Optional[str] = Form(None),
    visible: List[str] = Form(default=None),
    order: List[str] = Form(default=None),
    pattern_created_date: Optional[str] = Form(None)
):
    session = get_session(request, response)

    logger.info(f"Update settings: visible={visible}, order={order}, pattern={pattern_created_date}")

    if per_page is not None and APP_SETTINGS["features"]["pagination"]:
        session["per_page"] = per_page

    if APP_SETTINGS["features"]["column_settings"]:
        # If 'order' is present, it means the column settings form was submitted.
        # In this case, if 'visible' is missing (None), it implies all columns were unchecked.
        if order is not None:
            session["columns"]["order"] = order
            session["columns"]["visible"] = visible if visible is not None else []
            
            # Handle date pattern update
            if pattern_created_date is not None:
                # Update global settings
                if "created_date" not in APP_SETTINGS.get("columns", {}):
                    if "columns" not in APP_SETTINGS:
                        APP_SETTINGS["columns"] = {}
                    APP_SETTINGS["columns"]["created_date"] = {}
                
                APP_SETTINGS["columns"]["created_date"]["custom_pattern"] = pattern_created_date
                save_json(SETTINGS_FILE, APP_SETTINGS)
                
                # Update in-memory columns
                for col in COLUMNS:
                    if col["key"] == "created_date":
                        col["custom_pattern"] = pattern_created_date
                        break

    save_json(SESSION_FILE, SESSIONS)

    # Delegate to get_table_data to render the updated table
    return await get_table_data(request, response, q=q)


@app.post("/selection", response_class=HTMLResponse)
async def update_selection(
    request: Request,
    response: Response,
    action: str = Form(...),
    id: Optional[str] = Form(None),
    ids: Optional[str] = Form(None), # comma separated for page select
    q: Optional[str] = Form(None),
    page: int = Form(1)
):
    session = get_session(request, response)
    mode = session["selection"]["mode"]
    current_ids = set(session["selection"]["ids"])

    if action == "toggle":
        if not id:
            pass # Error?
        elif mode == "include":
            if id in current_ids:
                current_ids.remove(id)
            else:
                current_ids.add(id)
        else: # exclude
            if id in current_ids:
                current_ids.remove(id) # Re-include it (remove from exclude list)
            else:
                current_ids.add(id) # Exclude it

    elif action == "select_page":
        # We need the IDs on the current page. passed via hidden input or we assume ids param
        if ids:
            page_ids = ids.split(",")
            if mode == "include":
                current_ids.update(page_ids)
            else:
                current_ids.difference_update(page_ids)

    elif action == "deselect_page":
        if ids:
            page_ids = ids.split(",")
            if mode == "include":
                current_ids.difference_update(page_ids)
            else:
                current_ids.update(page_ids)

    elif action == "select_global":
        session["selection"]["mode"] = "exclude"
        current_ids = set() # Exclude nothing = Include all

    elif action == "clear":
        session["selection"]["mode"] = "include"
        current_ids = set()

    session["selection"]["ids"] = list(current_ids)
    save_json(SESSION_FILE, SESSIONS)
    
    # Delegate to get_table_data to render the updated table
    # The frontend should include current params.
    return await get_table_data(request, response, q=q, page=page)


app.mount("/examples", StaticFiles(directory=str(ROOT_DIR / "examples")), name="examples")
app.mount("/styles", StaticFiles(directory=str(ROOT_DIR / "styles")), name="styles")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
