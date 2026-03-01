"""Mock BPO Employee Portal — a simple FastAPI app for demo purposes.

Simulates an internal employee management portal that the AI agent
can log into, navigate, and scrape data from during demonstrations.

Routes:
    GET  /login          — Login form
    POST /login          — Authenticate (admin / demo123)
    GET  /dashboard      — Dashboard with navigation links
    GET  /employees      — Employee list table
    GET  /employees/{id} — Employee detail with active-time stats
    GET  /kpi            — Daily KPI dashboard
    GET  /logout         — Clear session and redirect to login
"""

from __future__ import annotations

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from seed_data import EMPLOYEES, KPI_DATA

app = FastAPI(title="BPO Employee Portal", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="mock-portal-secret-key")

templates = Jinja2Templates(directory="templates")

# Credentials
VALID_USERNAME = "admin"
VALID_PASSWORD = "demo123"


def _is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated", False)


# -------------------------------------------------------------------------
# Auth routes
# -------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the login form."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
    })


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Validate credentials and set session."""
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid username or password.",
    })


@app.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# -------------------------------------------------------------------------
# Protected routes
# -------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard with navigation links."""
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "employee_count": len(EMPLOYEES),
    })


@app.get("/employees", response_class=HTMLResponse)
async def employees_list(request: Request):
    """Table of all employees."""
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("employees.html", {
        "request": request,
        "employees": EMPLOYEES,
    })


@app.get("/employees/{employee_id}", response_class=HTMLResponse)
async def employee_detail(request: Request, employee_id: int):
    """Employee detail page with active-time stats table."""
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    employee = next((e for e in EMPLOYEES if e["id"] == employee_id), None)
    if not employee:
        return HTMLResponse("<h1>Employee not found</h1>", status_code=404)

    # Calculate summary stats
    stats = employee["daily_stats"]
    avg_pct = sum(s["active_time_pct"] for s in stats) / len(stats) if stats else 0
    avg_hours = sum(s["hours_logged"] for s in stats) / len(stats) if stats else 0
    total_calls = sum(s["calls_handled"] for s in stats)

    return templates.TemplateResponse("employee_detail.html", {
        "request": request,
        "employee": employee,
        "avg_active_pct": round(avg_pct, 2),
        "avg_hours": round(avg_hours, 1),
        "total_calls": total_calls,
    })


@app.get("/kpi", response_class=HTMLResponse)
async def kpi_dashboard(request: Request):
    """Daily KPI stats table."""
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("kpi.html", {
        "request": request,
        "kpi_data": KPI_DATA,
    })
