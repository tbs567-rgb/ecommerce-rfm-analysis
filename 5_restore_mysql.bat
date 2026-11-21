@echo off
chcp 936 >nul 2>nul
title 初始化 / 重置数据库（内置绿色版 MySQL）
setlocal
set "ROOT=%~dp0"
set "BIN=%ROOT%mysql_portable\bin"
set "INI=%ROOT%mysql_portable\my.ini"
set "DATA=%ROOT%mysql_portable\data"
set "DUMP=%ROOT%db_backup\ecommerce_rfm_backup.sql"

if not exist "%BIN%\mysqld.exe" (
    echo [错误] 找不到内置 MySQL：mysql_portable\bin\mysqld.exe
    pause
    exit /b 1
)
if not exist "%DUMP%" (
    echo [错误] 找不到备份文件：db_backup\ecommerce_rfm_backup.sql
    pause
    exit /b 1
)

rem 被 0_start_mysql.bat 以 /auto 调用时跳过确认
if /i not "%~1"=="/auto" (
    echo 警告：这会删除现有数据库并重新导入 54 万条原始数据。
    choice /c YN /m "继续"
    if errorlevel 2 exit /b 1
    echo.
)

if exist "%DATA%" (
    echo [0/5] 清理旧数据目录...
    rd /s /q "%DATA%"
)

echo [1/5] 初始化数据目录（约 10 秒）...
"%BIN%\mysqld.exe" --defaults-file="%INI%" --basedir="%ROOT%mysql_portable" --datadir="%DATA%" --initialize-insecure --console > "%ROOT%mysql_portable\init.log" 2>&1
if errorlevel 1 (
    echo [失败] 初始化失败，详见 mysql_portable\init.log
    pause
    exit /b 1
)

echo [2/5] 启动临时实例...
start "MySQL-init" /min "%BIN%\mysqld.exe" --defaults-file="%INI%" --standalone

set /a TRY=0
:WAIT
ping -n 3 127.0.0.1 >nul
"%BIN%\mysqladmin.exe" -h 127.0.0.1 -P 3307 -uroot ping >nul 2>&1
if not errorlevel 1 goto SETPW
set /a TRY+=1
if %TRY% LSS 20 goto WAIT
echo [失败] 实例起不来，详见 mysql_portable\runtime.log
pause
exit /b 1

:SETPW
echo [3/5] 设置 root 密码...
"%BIN%\mysql.exe" -h 127.0.0.1 -P 3307 -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';" 2>nul

echo [4/5] 导入数据（118 MB，约 15-30 秒）...
"%BIN%\mysql.exe" -h 127.0.0.1 -P 3307 -uroot -p123456 --default-character-set=utf8mb4 < "%DUMP%" 2>nul
if errorlevel 1 (
    echo [失败] 导入出错
    pause
    exit /b 1
)

echo [5/5] 核对数据并关闭临时实例...
"%BIN%\mysql.exe" -h 127.0.0.1 -P 3307 -uroot -p123456 -e "SELECT 'transactions_raw' AS t, COUNT(*) AS n FROM ecommerce_rfm.transactions_raw UNION ALL SELECT 'transactions_clean', COUNT(*) FROM ecommerce_rfm.transactions_clean UNION ALL SELECT 'customer_rfm', COUNT(*) FROM ecommerce_rfm.customer_rfm UNION ALL SELECT 'customer_segments', COUNT(*) FROM ecommerce_rfm.customer_segments;" 2>nul
"%BIN%\mysqladmin.exe" -h 127.0.0.1 -P 3307 -uroot -p123456 shutdown 2>nul

echo.
echo [OK] 数据库已重建完成。
echo      现在可以双击 0_start_mysql.bat 启动使用。
pause
