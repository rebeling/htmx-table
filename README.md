# HTMX Data Table

This is a proof-of-concept showing how to build a fully functional, interactive data table using **FastAPI**, **Jinja2**, and **HTMX**.

The goal is to show that you don't always need React or a heavy client-side framework to build rich UI components.

## How it works

The architecture is simple: **The server is the source of truth.**

1.  **State**: Sort order, filters, and pagination are stored in the user's session on the backend.
2.  **Rendering**: When you click "Next Page" or "Sort", HTMX sends a simple request.
3.  **Update**: The server returns just the new HTML for the table, and HTMX swaps it into the page.

No JSON APIs, no complex state management on the client. Just HTML over the wire.

## Tech Stack

*   **Backend**: Python (FastAPI)
*   **Frontend**: HTML + Jinja2 Templates + Bootstrap 5
*   **Interactivity**: HTMX
*   **Data**: Local JSON file (simulating a database)

## Quick Start

1.  Install dependencies:
    ```bash
    uv sync
    ```

2.  Run the server:
    ```bash
    uv run backend/main.py
    ```

3.  Open `http://localhost:8000` in your browser.

## Example

Here is how a sortable header works. Instead of writing a JavaScript click handler, we just describe the network request directly in the HTML:

```html
<span 
    hx-get="/table-data?sort=email&dir=asc"
    hx-target="#table-container">
    Email Address
</span>
```

When clicked, this fetches the sorted table HTML and replaces the content of `#table-container`. Simple.

## Configuration (app_settings.json)

The app is driven by a central config file in `data/app_settings.json`. This lets you tweak behavior without touching code.

*   **Features**: Toggle main capabilities like `search`, `pagination`, `row_selection` or `column_filters`.
*   **Defaults**: Set the initial rows per page and available options.
*   **Columns**: Define how each column behaves. You can change labels, enable/disable specific filters, provide dropdown options (like for "Status"), or set alignment and date formats.
