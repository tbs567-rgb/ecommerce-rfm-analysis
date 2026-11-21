@echo off
chcp 936 >nul 2>nul
title 启动绿色版 MySQL（端口 3307）
setlocal
set "ROOT=%~dp0"
set "MYSQLD=%ROOT%mysql_portable\bin\mysqld.exe"
set "INI=%ROOT%mysql_portable\my.ini"
set "DATA=%ROOT%mysql_portable\data"

if not exist "%MYSQLD%" (
    echo [错误] 找不到 mysql_portable\bin\mysqld.exe
    echo        请确认压缩包完整解压，没有丢文件。
    pause
    exit /b 1
)

rem 先查路径：中文 / 空格会让 MySQL 起不来，这里直接给中文提示
"%ROOT%python_env\Scripts\python.exe" "%ROOT%ecommerce_rfm\scripts\pathguard.py" "%ROOT%"
if errorlevel 9 (
    pause
    exit /b 9
)

if not exist "%DATA%\ibdata1" (
    echo [提示] 数据目录未初始化，正在首次导入数据（约 40 秒）...
    call "%~dp05_restore_mysql.bat" /auto
    if errorlevel 1 exit /b 1
)

echo ============================================================
echo   正在启动 MySQL 8.0（端口 3307，账号 root/123456）
echo   这个黑窗口可以最小化，关掉它数据库就停了
echo ============================================================
echo.

start "MySQL-3307" /min "%MYSQLD%" --defaults-file="%INI%" --standalone
echo 等待数据库就绪...
set /a TRY=0
:WAIT
ping -n 3 127.0.0.1 >nul
"%ROOT%mysql_portable\bin\mysqladmin.exe" -h 127.0.0.1 -P 3307 -uroot -p123456 ping >nul 2>&1
if not errorlevel 1 goto READY
set /a TRY+=1
if %TRY% LSS 15 goto WAIT

echo [失败] 15 次探测都没连上，请查看 mysql_portable\runtime.log
pause
exit /b 1

:READY
echo [OK] MySQL 已就绪：127.0.0.1:3307
"%ROOT%mysql_portable\bin\mysql.exe" -h 127.0.0.1 -P 3307 -uroot -p123456 -e "SELECT COUNT(*) AS customers FROM ecommerce_rfm.customer_rfm;" 2>nul
echo.
echo 下一步：双击 1_start_hdfs.bat 启动大数据环境
pause
