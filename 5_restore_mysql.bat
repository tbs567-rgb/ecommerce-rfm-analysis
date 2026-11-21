@echo off
rem ===== 5. Restore MySQL database from backup (for a NEW machine) =====
rem Prerequisite: MySQL 8 installed & running, root password set to 123456
set MYSQL="C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if not exist %MYSQL% set MYSQL=mysql
echo [1/1] Restoring ecommerce_rfm database (about 1-2 min)...
%MYSQL% -h localhost -uroot -p123456 < "D:\graduation_project\db_backup\ecommerce_rfm_backup.sql"
echo [DONE] Database restored. Open DBeaver and connect to verify.
pause
