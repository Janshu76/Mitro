r"""Optional local preview; keeps the normal Mitro home page intact.

Run from the project root:
    .venv\Scripts\python -m uvicorn design.preview:app --host 127.0.0.1 --port 8001
Open http://127.0.0.1:8001/design/mitro-optimus.html
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from mitro.api.app import app as mitro_app

app = FastAPI(title="Mitro design preview")
app.mount("/design", StaticFiles(directory=Path(__file__).parent), name="design")
app.mount("/", mitro_app)
