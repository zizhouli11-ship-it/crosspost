@echo off
REM 一键启动跨平台发布面板。清掉代理(避免本地请求被 socks 截走),起服务并打开浏览器。
cd /d %~dp0
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
set all_proxy=
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe -m uvicorn app:app --port 8765
