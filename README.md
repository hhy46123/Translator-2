# Offline EN↔KO Translator + Notebook

Production-safe, 100% offline English↔Korean translation and learning notebook.

## Features
- **Offline only**: uses a local ZIP of Korean Basic Dictionary JSON files.
- **FastAPI + SQLite** backend with WAL for Windows safety.
- **Server-rendered HTML** (Jinja2) + vanilla JS.
- **Sense-level indexing** with multiple meanings per term.
- **Notebook quiz** with 40 items per page (20+20 book layout).

## Project Structure
```
project_root/
  README.md
  requirements.txt
  backend/
    __init__.py
    main.py
    config.py
    db.py
    dict_indexer.py
    dict_query.py
    notebook.py
    schemas.py
    routes_translate.py
    routes_notebook.py
    startup.py
    tools/diag.py
  templates/
    base.html
    translate.html
    notebook.html
  static/
    app.css
    translate.js
    notebook.js
  data/
    cache/offline_dict.sqlite
    notebook.sqlite
```

## Windows PowerShell Setup
```powershell
# 1) Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -r requirements.txt

# 3) Set offline dictionary ZIP (required)
$env:OFFLINE_DICT_ZIP_PATH = "C:\path\to\offline_dict.zip"

# 4) Run (stable)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Dev Run (optional)
Use the same command as stable run. Do **not** use `--reload` in production.

## Offline Dictionary
- Provide a local ZIP containing Korean Basic Dictionary JSON files.
- The app builds the index **only at startup** and only if the ZIP changed.
- Build lock: `data/cache/offline_build.lock` prevents multiple Windows processes building.

## CLI Diagnostic Tool
```powershell
python -m backend.tools.diag
```
Shows ZIP path, build status, and table counts.

## Reset Database
```powershell
# Stop the app, then delete cached DBs
Remove-Item -Force data\cache\offline_dict.sqlite
Remove-Item -Force data\notebook.sqlite
```
On next startup, the dictionary and notebook databases rebuild.

## Manual Test Checklist
1. **Offline startup**: disconnect from internet and start the server.
2. **Translate EN→KO**:
   - Input `edge` and confirm multiple Korean senses.
3. **Translate KO→EN**:
   - Input `가장자리` and confirm English senses.
4. **Save gate**:
   - Try to save when no translation results (should remain disabled).
5. **Notebook quiz**:
   - Open Notebook and verify 40-item layout and reveal/correct/wrong flows.
6. **Details modal**:
   - Ensure details show sense list + equivalent terms.

## Acceptance Tests
- `edge` returns KO senses offline.
- `가장자리` returns EN senses offline.
- Notebook quiz works.

## Notes
- No external API calls or runtime downloads.
- SQLite uses WAL + `check_same_thread=False` for Windows safety.
