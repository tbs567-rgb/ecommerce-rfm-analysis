@echo off
rem ===== 4. Open interactive dashboard (works offline) =====
start "" "%~dp0ecommerce_rfm\outputs\dashboard\客户价值分析看板.html"
echo [OK] Dashboard opened in browser (works fully offline).
ping -n 4 127.0.0.1 >nul
