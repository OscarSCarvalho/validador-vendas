@echo off
rem Abre o backend (Flask) e o frontend (Vite) em janelas separadas e depois o navegador.
rem Para parar, feche as duas janelas.
start "Validador de Vendas - backend (nao feche)" cmd /k "cd /d "%~dp0backend" && python app.py"
start "Validador de Vendas - frontend (nao feche)" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 5 /nobreak >nul
start "" http://localhost:5173
