@echo off
cd /d D:\Dev\repos\fleet-agent-mcp
set PATH=C:\Users\sandr\.local\bin;%PATH%
set UV_PROJECT_ENVIRONMENT=D:\Dev\repos\fleet-agent-mcp\.venv
C:\Users\sandr\.local\bin\uv.exe run --directory D:\Dev\repos\fleet-agent-mcp python run_server.py
