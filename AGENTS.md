# Local service startup

- The backend calls the user's configured external model service. Start it with normal host network access, outside the restricted execution sandbox (request `require_escalated` when using exec_command). A sandboxed backend can pass `/api/health` while every model request fails with Windows access denied.
- Use `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend` when dependencies are installed. Do not overwrite `.env`.
- Before replacing a listener on port 8000, verify that its command line belongs to this project's backend. Do not terminate unrelated processes or interrupt an active generation.
- After startup, verify frontend HTTP and the API proxy. Health checks alone do not establish external model connectivity. Run the minimal model connection test when authorized, and distinguish that result from full generation validation.
- Keep API keys, article text, and raw upstream exception messages out of diagnostics and tool output. Connection diagnostics contain only exception types and numeric error codes.
