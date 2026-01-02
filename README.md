# htmx table

This is a proof-of-concept showing how to build a fully functional, interactive data table using **htmx**.

1.  **State**: Sort order, filters, and pagination are stored in the user's session on the backend.
2.  **Rendering**: When you click "Next Page" or "Sort", htmx sends a simple request.
3.  **Update**: The server returns just the new HTML for the table, and htmx swaps it into the page.


## Tech Stack

1.   **Backend**: Python (uv, FastAPI)
2.   **Frontend**: htmx + Jinja2 Templates + Bootstrap
3.   **Data**: Local JSON file (simulating a database)

## Quick Start

```bash
make build
make up
```

Open `http://localhost:8000` in your browser for the table and `http://localhost:8000/docs` for the openapi description.


## Example

Here is how a sortable header works. Instead of writing a JavaScript click handler, we just describe the network request directly in the HTML:

```html
<span
    hx-get="/table-data?sort=email&dir=asc"
    hx-target="#table-container">
    Email Address
</span>
```

When clicked, this fetches the sorted table HTML from server and replaces the content of `#table-container`.


## Configuration (app_settings.json)

The app is driven by a central config file in `data/app_settings.json`. This lets you tweak behavior without touching code.

*   **Features**: Toggle main capabilities like `search`, `pagination`, `row_selection` or `column_filters`.
*   **Defaults**: Set the initial rows per page and available options.
*   **Columns**: Define how each column behaves. You can change labels, enable/disable specific filters, provide dropdown options (like for "Status"), or set alignment and date formats.
