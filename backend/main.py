import math
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils import (
    apply_filters,
    apply_sort,
    get_active_columns,
    load_json,
    save_json,
)

app = FastAPI()

# --- Config & Data ---
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DATA_PATH = DATA_DIR / "users_1000.json"
SESSION_FILE = DATA_DIR / "sessions.json"
SETTINGS_FILE = DATA_DIR / "app_settings.json"

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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

    if save_needed:
        save_json(SESSION_FILE, SESSIONS)

    return session


# --- Routes ---


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/examples/src3-simple.html")


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
        session["sort"]["key"] = sort
        session["sort"]["dir"] = dir or "asc"
        save_json(SESSION_FILE, SESSIONS)

    current_sort = session["sort"]

    filtered_data = apply_filters(
        DATASET, q=q, column_filters=column_filters, settings=APP_SETTINGS
    )
    sorted_data = apply_sort(filtered_data, current_sort["key"], current_sort["dir"])

    page_info = None
    if APP_SETTINGS["features"]["pagination"]:
        per_page = session.get("per_page", 10)
        total_items = len(sorted_data)
        total_pages = math.ceil(total_items / per_page)
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1

        start = (page - 1) * per_page
        end = start + per_page
        paged_data = sorted_data[start:end]
        page_info = {"current": page, "total": total_pages}
    else:
        paged_data = sorted_data[:100]

    active_cols = get_active_columns(session, COLUMNS)

    # Filter string for pagination links
    filter_params = ""
    if column_filters:
        for k, v in column_filters.items():
            if v:
                filter_params += f"&{k}={v}"

    return templates.TemplateResponse(
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
        },
    )


@app.get("/table-settings", response_class=HTMLResponse)
async def get_settings_control(request: Request, response: Response):
    if not APP_SETTINGS["features"]["pagination"]:
        return ""

    session = get_session(request, response)
    current = session.get("per_page", 10)
    options = APP_SETTINGS["defaults"]["per_page_options"]

    return templates.TemplateResponse(
        request=request,
        name="per_page.html",
        context={"options": options, "current": current},
    )


@app.get("/table-settings-modal", response_class=HTMLResponse)
async def get_settings_modal(request: Request, response: Response):
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
        items.append({"key": key, "label": col["label"], "visible": key in visible})

    return templates.TemplateResponse(
        request=request, name="modal.html", context={"items": items}
    )


@app.post("/table-settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    response: Response,
    per_page: Optional[int] = Form(None),
    q: Optional[str] = Form(None),
    visible: List[str] = Form(None),
    order: List[str] = Form(None),
):
    session = get_session(request, response)

    if per_page is not None and APP_SETTINGS["features"]["pagination"]:
        session["per_page"] = per_page

    if APP_SETTINGS["features"]["column_settings"]:
        if visible is not None:
            session["columns"]["visible"] = visible
        if order is not None:
            session["columns"]["order"] = order

    save_json(SESSION_FILE, SESSIONS)

    # Delegate to get_table_data to render the updated table
    return await get_table_data(request, response, q=q)


app.mount("/examples", StaticFiles(directory=str(ROOT_DIR / "examples")), name="examples")
app.mount("/styles", StaticFiles(directory=str(ROOT_DIR / "styles")), name="styles")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
