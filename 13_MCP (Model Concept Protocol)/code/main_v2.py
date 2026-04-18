from mcp.server.fastmcp import FastMCP
from typing import List, Optional
import sqlite3
import os
from datetime import datetime, date
import json
import uvicorn
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hr_leave_management.db")


def init_database():
    """Initialize the SQLite database with required tables"""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create employees table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                department TEXT,
                position TEXT,
                hire_date DATE,
                leave_balance INTEGER DEFAULT 20,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create leave_records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leave_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                leave_date DATE NOT NULL,
                leave_type TEXT DEFAULT 'Annual',
                status TEXT DEFAULT 'Approved',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
            )
        ''')
        
        # Create leave_balance_history table for tracking balance changes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leave_balance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                old_balance INTEGER,
                new_balance INTEGER,
                change_reason TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
            )
        ''')
    
        conn.commit()
        conn.close()
        print(f"Database initialized successfully at: {DATABASE_PATH}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        print(f"Database path: {DATABASE_PATH}")
        raise

init_database()

# Create MCP server
mcp = FastMCP("HRLeaveManager", streamable_http_path="/")


# Helper functions
def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)


def execute_read_only_query(sql: str):
    """Execute a read-only SQL query and return columns and rows."""
    cleaned_sql = sql.strip().rstrip(";")
    if not cleaned_sql:
        raise ValueError("SQL query is required.")

    normalized_sql = cleaned_sql.lower()
    if not normalized_sql.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    blocked_terms = (
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "attach",
        "detach",
        "pragma",
    )
    if any(term in normalized_sql for term in blocked_terms):
        raise ValueError("Only read-only SELECT queries are allowed.")

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(cleaned_sql)
        rows = [dict(row) for row in cursor.fetchall()]
        columns = [description[0] for description in cursor.description or []]
        return columns, rows
    finally:
        conn.close()


def render_query_page(sql: str = "", results: Optional[dict] = None, error: Optional[str] = None) -> str:
    """Render a simple browser UI for interactive SQL queries."""
    escaped_sql = json.dumps(sql)[1:-1]

    if error:
        result_block = f"""
        <div class="card error">
            <strong>Error:</strong> {error}
        </div>
        """
    elif results is not None:
        headers = "".join(f"<th>{column}</th>" for column in results["columns"])
        rows_html = ""
        for row in results["rows"]:
            rows_html += "<tr>" + "".join(f"<td>{row.get(column, '')}</td>" for column in results["columns"]) + "</tr>"

        table_html = (
            f"""
            <table>
                <thead>
                    <tr>{headers}</tr>
                </thead>
                <tbody>
                    {rows_html or '<tr><td colspan="100%">No rows returned.</td></tr>'}
                </tbody>
            </table>
            """
            if results["columns"]
            else "<p>No columns returned.</p>"
        )

        result_block = f"""
        <div class="card">
            <div class="meta">
                <span><strong>Rows:</strong> {results["row_count"]}</span>
            </div>
            {table_html}
        </div>
        """
    else:
        result_block = """
        <div class="card hint">
            <p>Enter any read-only <code>SELECT</code> query and run it directly from your browser.</p>
            <p>Examples:</p>
            <pre>SELECT * FROM employees;
SELECT employee_id, name, leave_balance FROM employees ORDER BY name;
SELECT department, COUNT(*) AS employee_count FROM employees GROUP BY department;</pre>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Database Query</title>
        <style>
            :root {{
                color-scheme: light;
                --bg: #f4efe6;
                --panel: #fffdf8;
                --ink: #1f2937;
                --muted: #6b7280;
                --accent: #0f766e;
                --accent-soft: #dff6f3;
                --error: #b91c1c;
                --error-soft: #fee2e2;
                --border: #d6d3d1;
            }}
            body {{
                margin: 0;
                font-family: Georgia, "Times New Roman", serif;
                background: linear-gradient(160deg, #f4efe6 0%, #efe7db 100%);
                color: var(--ink);
            }}
            .page {{
                max-width: 980px;
                margin: 40px auto;
                padding: 0 20px 40px;
            }}
            h1 {{
                margin-bottom: 8px;
            }}
            p {{
                color: var(--muted);
            }}
            .card {{
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 18px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
                margin-top: 18px;
            }}
            .hint {{
                background: var(--accent-soft);
            }}
            .error {{
                background: var(--error-soft);
                color: var(--error);
            }}
            textarea {{
                width: 100%;
                min-height: 140px;
                border-radius: 12px;
                border: 1px solid var(--border);
                padding: 14px;
                font: 14px/1.5 "SFMono-Regular", Consolas, "Liberation Mono", monospace;
                box-sizing: border-box;
                resize: vertical;
                background: #fff;
                color: var(--ink);
            }}
            .actions {{
                display: flex;
                gap: 12px;
                margin-top: 14px;
                flex-wrap: wrap;
            }}
            button {{
                border: 0;
                border-radius: 999px;
                padding: 12px 18px;
                background: var(--accent);
                color: white;
                font-weight: 600;
                cursor: pointer;
            }}
            a {{
                color: var(--accent);
                text-decoration: none;
            }}
            .meta {{
                margin-bottom: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                overflow-x: auto;
                display: block;
            }}
            th, td {{
                border-bottom: 1px solid var(--border);
                padding: 10px 12px;
                text-align: left;
                white-space: nowrap;
            }}
            th {{
                background: #f7f7f5;
            }}
            code, pre {{
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
            }}
            pre {{
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <main class="page">
            <h1>Database Query Console</h1>
            <p>Run your own SQLite <code>SELECT</code> queries from localhost. Write a query below and submit it.</p>
            <form method="get" action="/database_query" class="card">
                <textarea name="sql" placeholder="SELECT * FROM employees;">{escaped_sql}</textarea>
                <div class="actions">
                    <button type="submit">Run Query</button>
                    <a href="/database_query">Clear</a>
                </div>
            </form>
            {result_block}
        </main>
    </body>
    </html>
    """


def get_mcp_tool_names() -> List[str]:
    """Return the registered MCP tool names for display and debugging."""
    return [tool.name for tool in mcp._tool_manager.list_tools()]


def get_mcp_tool_catalog() -> List[dict]:
    """Return basic metadata for registered MCP tools."""
    catalog = []
    for tool in mcp._tool_manager.list_tools():
        catalog.append(
            {
                "name": tool.name,
                "description": getattr(tool, "description", "") or "",
                "input_schema": getattr(tool, "parameters", {}) or {},
            }
        )
    return catalog


def get_mcp_tool_examples() -> dict:
    """Return example JSON arguments for each MCP tool."""
    return {
        "add_employee": {
            "employee_id": "E006",
            "name": "Babu",
            "email": "babu@company.com",
            "department": "Engineering",
            "position": "Developer",
            "initial_leave_balance": 20,
        },
        "remove_employee": {
            "employee_id": "E006",
        },
        "update_leave_balance": {
            "employee_id": "E001",
            "new_balance": 25,
            "reason": "Manual adjustment",
        },
        "list_employees": {},
        "get_employee_details": {
            "employee_id": "E001",
        },
        "get_leave_balance": {
            "employee_id": "E001",
        },
        "apply_leave": {
            "employee_id": "E001",
            "leave_dates": ["2026-04-21", "2026-04-22"],
            "leave_type": "Annual",
        },
        "get_leave_history": {
            "employee_id": "E001",
        },
        "get_department_summary": {
            "department": "Engineering",
        },
        "get_recent_leave_activity": {
            "days": 30,
        },
    }


def get_default_arguments_json(tool_name: str) -> str:
    """Return formatted example JSON for the selected tool."""
    examples = get_mcp_tool_examples()
    return json.dumps(examples.get(tool_name, {}), indent=2)


async def run_mcp_tool(tool_name: str, arguments: dict):
    """Execute a registered MCP tool directly for browser/API usage."""
    if not tool_name:
        raise ValueError("Tool name is required.")

    tool = mcp._tool_manager.get_tool(tool_name)
    if tool is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    return await mcp._tool_manager.call_tool(tool_name, arguments, convert_result=True)


def employee_exists(employee_id: str) -> bool:
    """Check if employee exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


# HR Management Tools

@mcp.tool()
def add_employee(employee_id: str, name: str, email: str, department: str, position: str, initial_leave_balance: int = 20) -> str:
    """Add a new employee to the system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if employee already exists
        if employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} already exists."
        
        # Insert new employee
        cursor.execute('''
            INSERT INTO employees (employee_id, name, email, department, position, leave_balance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, name, email, department, position, initial_leave_balance))
        
        # Log balance change
        cursor.execute('''
            INSERT INTO leave_balance_history (employee_id, old_balance, new_balance, change_reason, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, 0, initial_leave_balance, "Initial balance", "HR System"))
        
        conn.commit()
        conn.close()
        
        return f"Employee {name} (ID: {employee_id}) added successfully with {initial_leave_balance} leave days."
    
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return f"Email {email} is already registered to another employee."
        return f"Database error: {str(e)}"
    except Exception as e:
        return f"Error adding employee: {str(e)}"
    

@mcp.tool()
def remove_employee(employee_id: str) -> str:
    """Remove an employee from the system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} not found."
        
        # Get employee name before deletion
        cursor.execute("SELECT name FROM employees WHERE employee_id = ?", (employee_id,))
        result = cursor.fetchone()
        employee_name = result[0] if result else "Unknown"
        
        # Delete related records first (due to foreign key constraints)
        cursor.execute("DELETE FROM leave_records WHERE employee_id = ?", (employee_id,))
        cursor.execute("DELETE FROM leave_balance_history WHERE employee_id = ?", (employee_id,))
        cursor.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
        
        conn.commit()
        conn.close()
        
        return f"Employee {employee_name} (ID: {employee_id}) and all related records removed successfully."
    
    except Exception as e:
        return f"Error removing employee: {str(e)}"



@mcp.tool()
def update_leave_balance(employee_id: str, new_balance: int, reason: str = "HR adjustment") -> str:
    """Update an employee's leave balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} not found."
        
        # Get current balance
        cursor.execute("SELECT leave_balance, name FROM employees WHERE employee_id = ?", (employee_id,))
        result = cursor.fetchone()
        old_balance = result[0]
        employee_name = result[1]
        
        # Update balance
        cursor.execute("UPDATE employees SET leave_balance = ? WHERE employee_id = ?", (new_balance, employee_id))
        
        # Log balance change
        cursor.execute('''
            INSERT INTO leave_balance_history (employee_id, old_balance, new_balance, change_reason, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, old_balance, new_balance, reason, "HR Manager"))
        
        conn.commit()
        conn.close()
        
        return f"Leave balance updated for {employee_name} (ID: {employee_id}): {old_balance} → {new_balance} days. Reason: {reason}"
    
    except Exception as e:
        return f"Error updating leave balance: {str(e)}"



@mcp.tool()
def list_employees(department: Optional[str] = None) -> str:
    """List all employees or filter by department"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if department:
            cursor.execute('''
                SELECT employee_id, name, email, department, position, leave_balance, hire_date
                FROM employees WHERE department = ? ORDER BY name
            ''', (department,))
        else:
            cursor.execute('''
                SELECT employee_id, name, email, department, position, leave_balance, hire_date
                FROM employees ORDER BY name
            ''')
        
        employees = cursor.fetchall()
        conn.close()
        
        if not employees:
            dept_msg = f" in {department}" if department else ""
            return f"No employees found{dept_msg}."
        
        result = "Employee List:\n" + "="*80 + "\n"
        result += f"{'ID':<8} {'Name':<20} {'Email':<25} {'Dept':<12} {'Position':<15} {'Balance':<8}\n"
        result += "-"*80 + "\n"
        
        for emp in employees:
            result += f"{emp[0]:<8} {emp[1]:<20} {emp[2]:<25} {emp[3]:<12} {emp[4]:<15} {emp[5]:<8}\n"
        
        return result
    
    except Exception as e:
        return f"Error listing employees: {str(e)}"
    

@mcp.tool()
def get_employee_details(employee_id: str) -> str:
    """Get detailed information about an employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} not found."
        
        # Get employee details
        cursor.execute('''
            SELECT employee_id, name, email, department, position, leave_balance, hire_date, created_at
            FROM employees WHERE employee_id = ?
        ''', (employee_id,))
        
        emp = cursor.fetchone()
        
        # Get leave history count
        cursor.execute('''
            SELECT COUNT(*) FROM leave_records WHERE employee_id = ?
        ''', (employee_id,))
        leave_count = cursor.fetchone()[0]
        
        # Get recent balance changes
        cursor.execute('''
            SELECT change_reason, old_balance, new_balance, changed_at
            FROM leave_balance_history WHERE employee_id = ?
            ORDER BY changed_at DESC LIMIT 5
        ''', (employee_id,))
        balance_history = cursor.fetchall()
        
        conn.close()
        
        result = f"Employee Details for {emp[1]} (ID: {emp[0]})\n"
        result += "="*50 + "\n"
        result += f"Email: {emp[2]}\n"
        result += f"Department: {emp[3]}\n"
        result += f"Position: {emp[4]}\n"
        result += f"Current Leave Balance: {emp[5]} days\n"
        result += f"Hire Date: {emp[6]}\n"
        result += f"Total Leaves Taken: {leave_count} days\n\n"
        
        if balance_history:
            result += "Recent Balance Changes:\n"
            result += "-"*30 + "\n"
            for change in balance_history:
                result += f"{change[0]}: {change[1]} → {change[2]} ({change[3]})\n"
        
        return result
    
    except Exception as e:
        return f"Error getting employee details: {str(e)}"



@mcp.tool()
def get_leave_balance(employee_id: str) -> str:
    """Check remaining leave days for an employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} not found."
        
        cursor.execute('''
            SELECT name, leave_balance FROM employees WHERE employee_id = ?
        ''', (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return f"{result[0]} (ID: {employee_id}) has {result[1]} leave days remaining."
        return "Employee ID not found."
    
    except Exception as e:
        return f"Error checking leave balance: {str(e)}"




@mcp.tool()
def apply_leave(employee_id: str, leave_dates: List[str], leave_type: str = "Annual") -> str:
    """Apply leave for specific dates"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} not found."
        
        # Get current balance and name
        cursor.execute('''
            SELECT leave_balance, name FROM employees WHERE employee_id = ?
        ''', (employee_id,))
        
        result = cursor.fetchone()
        available_balance = result[0]
        employee_name = result[1]
        requested_days = len(leave_dates)
        
        if available_balance < requested_days:
            return f"Insufficient leave balance for {employee_name}. Requested: {requested_days} days, Available: {available_balance} days."
        
        # Validate date format and check for duplicates
        valid_dates = []
        for date_str in leave_dates:
            try:
                # Validate date format (YYYY-MM-DD)
                datetime.strptime(date_str, '%Y-%m-%d')
                
                # Check if already applied for this date
                cursor.execute('''
                    SELECT 1 FROM leave_records WHERE employee_id = ? AND leave_date = ?
                ''', (employee_id, date_str))
                
                if cursor.fetchone():
                    continue  # Skip duplicate date
                
                valid_dates.append(date_str)
            except ValueError:
                continue  # Skip invalid date format
        
        if not valid_dates:
            return "No valid dates provided or all dates are already taken."
        
        # Apply leave for valid dates
        for leave_date in valid_dates:
            cursor.execute('''
                INSERT INTO leave_records (employee_id, leave_date, leave_type)
                VALUES (?, ?, ?)
            ''', (employee_id, leave_date, leave_type))
        
        # Update balance
        new_balance = available_balance - len(valid_dates)
        cursor.execute('''
            UPDATE employees SET leave_balance = ? WHERE employee_id = ?
        ''', (new_balance, employee_id))
        
        # Log balance change
        cursor.execute('''
            INSERT INTO leave_balance_history (employee_id, old_balance, new_balance, change_reason, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, available_balance, new_balance, f"Applied {len(valid_dates)} days leave", employee_name))
        
        conn.commit()
        conn.close()
        
        applied_days = len(valid_dates)
        return f"Leave applied successfully for {employee_name}. Applied: {applied_days} day(s), Remaining balance: {new_balance} days."
    
    except Exception as e:
        return f"Error applying leave: {str(e)}"


@mcp.tool()
def get_leave_history(employee_id: str) -> str:
    """Get list of leave dates for employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not employee_exists(employee_id):
            conn.close()
            return f"Employee with ID {employee_id} not found."
        
        # Get employee name
        cursor.execute("SELECT name FROM employees WHERE employee_id = ?", (employee_id,))
        employee_name = cursor.fetchone()[0]
        
        # Get leave history
        cursor.execute('''
            SELECT leave_date, leave_type, status, applied_at
            FROM leave_records WHERE employee_id = ?
            ORDER BY leave_date DESC
        ''', (employee_id,))
        
        leave_records = cursor.fetchall()
        conn.close()
        
        if not leave_records:
            return f"No leave records found for {employee_name} (ID: {employee_id})."
        
        result = f"Leave History for {employee_name} (ID: {employee_id})\n"
        result += "="*60 + "\n"
        result += f"{'Date':<12} {'Type':<10} {'Status':<10} {'Applied At':<20}\n"
        result += "-"*60 + "\n"
        
        for record in leave_records:
            result += f"{record[0]:<12} {record[1]:<10} {record[2]:<10} {record[3]:<20}\n"
        
        return result
    
    except Exception as e:
        return f"Error getting leave history: {str(e)}"


# Reporting and Analytics Tools

@mcp.tool()
def get_department_summary(department: Optional[str] = None) -> str:
    """Get leave summary by department or overall"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if department:
            cursor.execute('''
                SELECT COUNT(*) as emp_count, 
                       SUM(leave_balance) as total_balance,
                       AVG(leave_balance) as avg_balance
                FROM employees WHERE department = ?
            ''', (department,))
            
            result = cursor.fetchone()
            if not result or result[0] == 0:
                return f"No employees found in {department} department."
            
            emp_count, total_balance, avg_balance = result
            
            summary = f"Department Summary for {department}\n"
            summary += "="*40 + "\n"
            summary += f"Total Employees: {emp_count}\n"
            summary += f"Total Leave Balance: {total_balance} days\n"
            summary += f"Average Leave Balance: {avg_balance:.1f} days\n"
            
        else:
            # Overall summary
            cursor.execute('''
                SELECT department, COUNT(*) as emp_count, 
                       SUM(leave_balance) as total_balance,
                       AVG(leave_balance) as avg_balance
                FROM employees 
                GROUP BY department
                ORDER BY department
            ''')
            
            dept_summaries = cursor.fetchall()
            
            if not dept_summaries:
                return "No employees found in the system."
            
            summary = "Overall Leave Summary by Department\n"
            summary += "="*60 + "\n"
            summary += f"{'Department':<15} {'Employees':<10} {'Total Balance':<15} {'Avg Balance':<12}\n"
            summary += "-"*60 + "\n"
            
            total_employees = 0
            total_balance = 0
            
            for dept_data in dept_summaries:
                dept, emp_count, dept_total, dept_avg = dept_data
                summary += f"{dept:<15} {emp_count:<10} {dept_total:<15} {dept_avg:<12.1f}\n"
                total_employees += emp_count
                total_balance += dept_total
            
            summary += "-"*60 + "\n"
            summary += f"{'TOTAL':<15} {total_employees:<10} {total_balance:<15} {total_balance/total_employees:<12.1f}\n"
        
        conn.close()
        return summary
    
    except Exception as e:
        return f"Error generating summary: {str(e)}"

@mcp.tool()
def get_recent_leave_activity(days: int = 30) -> str:
    """Get recent leave applications"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.name, e.employee_id, lr.leave_date, lr.leave_type, lr.applied_at
            FROM leave_records lr
            JOIN employees e ON lr.employee_id = e.employee_id
            WHERE lr.applied_at >= datetime('now', '-{} days')
            ORDER BY lr.applied_at DESC
        '''.format(days))
        
        recent_leaves = cursor.fetchall()
        conn.close()
        
        if not recent_leaves:
            return f"No leave applications found in the last {days} days."
        
        result = f"Recent Leave Activity (Last {days} days)\n"
        result += "="*70 + "\n"
        result += f"{'Employee':<20} {'ID':<8} {'Leave Date':<12} {'Type':<10} {'Applied At':<20}\n"
        result += "-"*70 + "\n"
        
        for leave in recent_leaves:
            result += f"{leave[0]:<20} {leave[1]:<8} {leave[2]:<12} {leave[3]:<10} {leave[4]:<20}\n"
        
        return result
    
    except Exception as e:
        return f"Error getting recent activity: {str(e)}"

# Resources and Prompts


@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}! Welcome to the HR Leave Management System. How can I assist you today?"


@mcp.prompt()
def hr_dashboard_prompt() -> str:
    """Generate a comprehensive HR dashboard prompt"""
    return """Create a comprehensive HR dashboard showing:
1. Employee overview with key metrics
2. Leave balance distribution
3. Recent leave activity
4. Department-wise summaries
5. Any alerts or recommendations

Format it as a professional dashboard with clear sections and visual indicators where appropriate."""


@mcp.prompt()
def leave_report_prompt(employee_id: str) -> str:
    """Generate a detailed leave report prompt for an employee"""
    return f"""Generate a detailed leave report for employee {employee_id} including:
1. Current leave balance and status
2. Leave history with dates and types
3. Balance change history
4. Recommendations for leave planning
5. Any patterns or insights from their leave usage

Make it professional and actionable for HR review."""

# Initialize with sample data
def init_sample_data():
    """Initialize database with sample data for demo purposes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return  # Data already exists
    
    # Sample employees
    sample_employees = [
        ("E001", "John Smith", "john.smith@company.com", "Engineering", "Senior Developer", 18),
        ("E002", "Sarah Johnson", "sarah.johnson@company.com", "HR", "HR Manager", 22),
        ("E003", "Mike Wilson", "mike.wilson@company.com", "Marketing", "Marketing Specialist", 20),
        ("E004", "Emily Brown", "emily.brown@company.com", "Engineering", "Junior Developer", 20),
        ("E005", "David Lee", "david.lee@company.com", "Sales", "Sales Manager", 15),
    ]
    
    for emp_data in sample_employees:
        cursor.execute('''
            INSERT INTO employees (employee_id, name, email, department, position, leave_balance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', emp_data)
        
        # Log initial balance
        cursor.execute('''
            INSERT INTO leave_balance_history (employee_id, old_balance, new_balance, change_reason, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (emp_data[0], 0, emp_data[5], "Initial balance", "System"))
    
    # Sample leave records
    sample_leaves = [
        ("E001", "2024-12-25", "Holiday"),
        ("E001", "2024-12-26", "Holiday"),
        ("E002", "2024-12-30", "Personal"),
        ("E005", "2024-12-31", "Personal"),
    ]
    
    for leave_data in sample_leaves:
        cursor.execute('''
            INSERT INTO leave_records (employee_id, leave_date, leave_type)
            VALUES (?, ?, ?)
        ''', leave_data)
    
    conn.commit()
    conn.close()

# Initialize sample data
init_sample_data()


async def database_query(request: Request):
    """HTTP endpoint for running read-only database queries."""
    sql = request.query_params.get("sql", "").strip()

    if request.method == "GET" and not sql:
        return HTMLResponse(render_query_page())

    if request.method == "POST":
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Request body must be valid JSON."}, status_code=400)
        sql = str(payload.get("sql", sql)).strip()

    try:
        columns, rows = execute_read_only_query(sql)
        result = {
            "query": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
        if request.method == "GET":
            return HTMLResponse(render_query_page(sql=sql, results=result))
        return JSONResponse(result)
    except ValueError as exc:
        if request.method == "GET":
            return HTMLResponse(render_query_page(sql=sql, error=str(exc)), status_code=400)
        return JSONResponse({"error": str(exc)}, status_code=400)
    except sqlite3.Error as exc:
        if request.method == "GET":
            return HTMLResponse(render_query_page(sql=sql, error=f"Database error: {exc}"), status_code=400)
        return JSONResponse({"error": f"Database error: {exc}"}, status_code=400)


async def healthcheck(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "database_path": DATABASE_PATH,
            "database_query_endpoint": "/database_query",
            "mcp_endpoint": "/mcp/rpc",
            "mcp_tools": get_mcp_tool_names(),
        }
    )


async def mcp_info(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "name": "HRLeaveManager",
            "transport": "streamable-http",
            "endpoint": "/mcp/rpc",
            "description": "MCP endpoint for HR leave management tools backed by the SQLite database.",
            "tools": get_mcp_tool_names(),
        }
    )


def render_mcp_page(selected_tool: str = "", arguments_json: str = "{}", result: Optional[str] = None, error: Optional[str] = None) -> str:
    """Render a browser console for invoking HR Leave MCP tools."""
    catalog = get_mcp_tool_catalog()
    examples_json = json.dumps({tool["name"]: get_default_arguments_json(tool["name"]) for tool in catalog})
    if not selected_tool and catalog:
        selected_tool = catalog[0]["name"]
    if arguments_json == "{}" and selected_tool:
        arguments_json = get_default_arguments_json(selected_tool)
    tool_options = "".join(
        f"<option value=\"{tool['name']}\"{' selected' if tool['name'] == selected_tool else ''}>{tool['name']}</option>"
        for tool in catalog
    )

    tool_cards = ""
    for tool in catalog:
        schema_preview = json.dumps(tool["input_schema"], indent=2)
        tool_cards += f"""
        <details class="tool-card">
            <summary><code>{tool['name']}</code></summary>
            <p>{tool['description'] or 'No description available.'}</p>
            <pre>{schema_preview}</pre>
        </details>
        """

    result_block = ""
    if error:
        result_block = f'<div class="card error"><strong>Error:</strong> {error}</div>'
    elif result is not None:
        result_block = f'<div class="card"><h2>Result</h2><pre>{result}</pre></div>'

    return (
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>HR Leave MCP</title>
            <style>
                body {{
                    margin: 0;
                    font-family: Georgia, "Times New Roman", serif;
                    background: linear-gradient(160deg, #f4efe6 0%, #efe7db 100%);
                    color: #1f2937;
                }}
                main {{
                    max-width: 900px;
                    margin: 40px auto;
                    padding: 0 20px 40px;
                }}
                .card {{
                    background: #fffdf8;
                    border: 1px solid #d6d3d1;
                    border-radius: 16px;
                    padding: 20px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
                    margin-top: 18px;
                }}
                .error {{
                    background: #fee2e2;
                    color: #b91c1c;
                }}
                code {{
                    font-family: "SFMono-Regular", Consolas, monospace;
                }}
                select, textarea {{
                    width: 100%;
                    box-sizing: border-box;
                    border-radius: 12px;
                    border: 1px solid #d6d3d1;
                    padding: 12px;
                    font: 14px/1.5 "SFMono-Regular", Consolas, monospace;
                    background: #fff;
                    color: #1f2937;
                }}
                textarea {{
                    min-height: 180px;
                    resize: vertical;
                }}
                button {{
                    border: 0;
                    border-radius: 999px;
                    padding: 12px 18px;
                    background: #0f766e;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 14px;
                }}
                a {{
                    color: #0f766e;
                    text-decoration: none;
                }}
                pre {{
                    white-space: pre-wrap;
                    overflow-wrap: anywhere;
                }}
                .tool-card {{
                    margin-top: 12px;
                    border-top: 1px solid #e7e5e4;
                    padding-top: 12px;
                }}
            </style>
        </head>
        <body>
            <main>
                <h1>HR Leave MCP Console</h1>
                <p>Use this page to run the HR Leave MCP tools from localhost. The low-level MCP client endpoint remains <code>/mcp/rpc</code>.</p>
                <div class="card">
                    <form method="get" action="/mcp">
                        <label for="tool"><strong>Tool</strong></label>
                        <select id="tool" name="tool">{tool_options}</select>
                        <p><strong>Arguments JSON</strong></p>
                        <textarea id="arguments" name="arguments">{arguments_json}</textarea>
                        <button type="submit">Run Tool</button>
                    </form>
                </div>
                {result_block}
                <div class="card">
                    <p><strong>MCP transport endpoint:</strong> <code>http://127.0.0.1:8000/mcp/rpc</code></p>
                    <p><strong>Browser/API tool endpoint:</strong> <code>http://127.0.0.1:8000/mcp/query</code></p>
                    <p><strong>Metadata endpoint:</strong> <a href="/mcp-info">/mcp-info</a></p>
                    <p><strong>Registered HR tools:</strong></p>
                    {tool_cards}
                </div>
            </main>
        </body>
        <script>
            const toolExamples = {examples_json};
            const toolSelect = document.getElementById("tool");
            const argumentsBox = document.getElementById("arguments");
            let lastAutoValue = argumentsBox.value;

            toolSelect.addEventListener("change", () => {{
                const nextValue = toolExamples[toolSelect.value] || "{{}}";
                if (argumentsBox.value.trim() === "" || argumentsBox.value === lastAutoValue) {{
                    argumentsBox.value = nextValue;
                }}
                lastAutoValue = nextValue;
            }});
        </script>
    </html>
        """
    )


async def mcp_home(request: Request) -> HTMLResponse:
    tool_name = request.query_params.get("tool", "").strip()
    arguments_json = request.query_params.get("arguments", "{}")

    if not tool_name:
        default_tool = get_mcp_tool_names()[0] if get_mcp_tool_names() else ""
        return HTMLResponse(render_mcp_page(selected_tool=default_tool, arguments_json="{}"))

    try:
        arguments = json.loads(arguments_json or "{}")
        if not isinstance(arguments, dict):
            raise ValueError("Arguments JSON must be an object.")
        result = await run_mcp_tool(tool_name, arguments)
        pretty_result = json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
        return HTMLResponse(render_mcp_page(selected_tool=tool_name, arguments_json=arguments_json, result=pretty_result))
    except json.JSONDecodeError as exc:
        return HTMLResponse(
            render_mcp_page(selected_tool=tool_name, arguments_json=arguments_json, error=f"Invalid JSON: {exc}"),
            status_code=400,
        )
    except Exception as exc:
        return HTMLResponse(
            render_mcp_page(selected_tool=tool_name, arguments_json=arguments_json, error=str(exc)),
            status_code=400,
        )


async def mcp_query(request: Request) -> JSONResponse:
    tool_name = request.query_params.get("tool", "").strip()
    arguments: dict = {}

    if request.method == "POST":
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Request body must be valid JSON."}, status_code=400)
        tool_name = str(payload.get("tool", tool_name)).strip()
        raw_arguments = payload.get("arguments", {})
        if not isinstance(raw_arguments, dict):
            return JSONResponse({"error": "The `arguments` field must be a JSON object."}, status_code=400)
        arguments = raw_arguments
    else:
        raw_arguments = request.query_params.get("arguments", "{}")
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            return JSONResponse({"error": f"Invalid JSON in `arguments`: {exc}"}, status_code=400)
        if not isinstance(arguments, dict):
            return JSONResponse({"error": "The `arguments` field must decode to a JSON object."}, status_code=400)

    try:
        result = await run_mcp_tool(tool_name, arguments)
        return JSONResponse({"tool": tool_name, "arguments": arguments, "result": result})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


mcp_http_app = mcp.streamable_http_app()


@asynccontextmanager
async def app_lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    lifespan=app_lifespan,
    routes=[
        Route("/", healthcheck),
        Route("/mcp", mcp_home),
        Route("/mcp-info", mcp_info),
        Route("/mcp/query", mcp_query, methods=["GET", "POST"]),
        Route("/database_query", database_query, methods=["GET", "POST"]),
        Mount("/mcp/rpc", app=mcp_http_app),
    ]
)




# To start the server:
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
