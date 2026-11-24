@echo off
chcp 936 >nul 2>nul
rem ===== 9. Stop HDFS (kill NameNode + DataNode by PID) =====
rem 注意：不能让 for /f 里的命令以引号开头，cmd 的 /c 会吞掉首尾引号导致
rem        “文件名、目录名或卷标语法不正确”。所以先把 jps 结果落到临时文件，
rem        再用 findstr 读文件（命令以 findstr 开头，没有首引号问题）。
setlocal enabledelayedexpansion
set "JPS=%~dp0bigdata\jdk-11.0.32.1+1\bin\jps.exe"
set "LIST=%TEMP%\hdfs_jps_%~n0.txt"

if not exist "%JPS%" (
    echo [错误] 找不到 jps：%JPS%
    echo         请确认整个包是完整解压的，没有单独移动过 bigdata 目录。
    pause
    exit /b 1
)

"%JPS%" -l > "%LIST%" 2>nul
set N=0
for /f "tokens=1" %%i in ('findstr /C:"NameNode" /C:"DataNode" "%LIST%"') do (
    echo killing PID %%i ...
    taskkill /PID %%i /F >nul 2>&1
    set /a N+=1
)

if "!N!"=="0" echo [i] 没有在运行的 NameNode / DataNode，HDFS 本来就是停的。

if not "!N!"=="0" (
    ping -n 3 127.0.0.1 >nul
    "%JPS%" -l > "%LIST%" 2>nul
    set LEFT=0
    for /f "tokens=1" %%i in ('findstr /C:"NameNode" /C:"DataNode" "%LIST%"') do set /a LEFT+=1
    if "!LEFT!"=="0" (
        echo [OK] HDFS stopped. 共结束 !N! 个进程。
    ) else (
        echo [警告] 还有 !LEFT! 个进程没停掉，请手动关闭那个最小化的 HDFS-Daemon 窗口。
    )
)

del "%LIST%" >nul 2>&1
pause
