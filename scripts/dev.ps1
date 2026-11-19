# Start the backend (port 8000) and the frontend (port 5173) in two PowerShell windows. Windows-first helper.
$root = Split-Path -Parent $PSScriptRoot
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; uv run uvicorn app.main:create_app --factory --reload --no-access-log"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
Write-Host "Backend: http://127.0.0.1:8000/api/docs   Frontend: http://localhost:5173"
