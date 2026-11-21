@echo off
chcp 936 >nul 2>nul
title 填写署名信息 - 课程设计报告与答辩 PPT
cd /d "%~dp0"

echo ============================================================
echo   一键填写小组成员 / 学号 / 班级 / 指导教师
echo   填完自动重新导出 PDF，并刷新「提交材料」目录
echo ------------------------------------------------------------
echo   接下来会打开 info.json，请把 4 个姓名等信息填全
echo   （第 1 位是组长，填完保存并关闭记事本）
echo ============================================================
echo.

notepad "ecommerce_rfm\docs\report\info.json"

echo.
echo 已保存？按任意键开始写入（Ctrl+C 可放弃）...
pause >nul
echo.

"python_env\Scripts\python.exe" "ecommerce_rfm\docs\report\fill_info.py"

echo.
echo ============================================================
echo   完成。请打开报告核对封面，并在附录 A 手写签名。
echo   提交目录：%~dp0提交材料
echo ============================================================
pause
