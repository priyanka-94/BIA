uv run mcp install main.py 

## Steps to run the localhost
# uv sync
# uv run python -c "from mcp.server.fastmcp import FastMCP; print('mcp imported')"
# uv run python main_v2.py (Database initialized successfully at)
# sqlite3 hr_leave_management.db
# Open http://127.0.0.1:8000/database_query to use the browser query console
# Type any SELECT query and run it from the page itself
# API POST still works at /database_query with body: {"sql":"SELECT * FROM employees"}
# Browser-friendly MCP page and tool runner: http://127.0.0.1:8000/mcp
# Browser/API wrapper for HR Leave tools: http://127.0.0.1:8000/mcp/query
# Example: /mcp/query?tool=list_employees&arguments={}
# Example POST body: {"tool":"get_leave_balance","arguments":{"employee_id":"E001"}}
# Example Arguments JSON for add_employee:
# {
#   "employee_id": "E006",
#   "name": "Babu",
#   "email": "babu@company.com",
#   "department": "Engineering",
#   "position": "Developer",
#   "initial_leave_balance": 20
# }
# Actual MCP endpoint for the HR Leave Manager tools: http://127.0.0.1:8000/mcp/rpc
# MCP metadata / tool list: http://127.0.0.1:8000/mcp-info

## Steps to run the docker
# docker build -t hr-leave-mcp .
# docker build --no-cache -t hr-leave-mcp .
# docker run --rm -it -p 8000:8000 hr-leave-mcp

## Steps to run the podman
# podman build -t hr-leave-mcp .
# podman build --no-cache -t hr-leave-mcp .
# podman run --rm -it -p 8000:8000 hr-leave-mcp

## Steps to create pyproject.toml
# pip install pipreqs
# pipreqs . --force (requirements.txt)
# poetry init
# poetry add $(cat requirements.txt) - it creates pyproject.toml

## Steps to list the port pids and kill it
# lsof -i :8000
# kill -9 <pid>


curl -X POST http://127.0.0.1:8000/mcp/rpc/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"add_employee",
      "arguments":{
        "employee_id":"E006",
        "name":"Babu",
        "email":"babu@company.com",
        "department":"Engineering",
        "position":"Developer",
        "initial_leave_balance":20
      }
    }
  }'

curl -X POST http://127.0.0.1:8000/mcp/rpc/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc":"2.0",
    "id":2,
    "method":"tools/call",
    "params":{
      "name":"get_leave_balance",
      "arguments":{
        "employee_id":"E001"
      }
    }
  }'
