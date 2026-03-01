"""Generate realistic fake data for the mock BPO employee portal.

Creates 20 employees across 4 departments, each with 14 days of
active-time statistics and daily KPI aggregates.
"""

import random
from datetime import date, timedelta

random.seed(42)  # Reproducible data

DEPARTMENTS = ["Customer Support", "Technical Support", "Sales", "Back Office"]

# Realistic Filipino + international BPO employee names
_EMPLOYEES = [
    ("Maria Santos", "Customer Support"),
    ("Juan Dela Cruz", "Technical Support"),
    ("Ana Reyes", "Customer Support"),
    ("Carlos Garcia", "Sales"),
    ("Isabella Cruz", "Back Office"),
    ("Miguel Torres", "Technical Support"),
    ("Sofia Mendoza", "Customer Support"),
    ("Rafael Aquino", "Sales"),
    ("Camille Villanueva", "Customer Support"),
    ("Jose Bautista", "Technical Support"),
    ("Patricia Lim", "Back Office"),
    ("Antonio Ramos", "Sales"),
    ("Grace Fernandez", "Customer Support"),
    ("Mark Tan", "Technical Support"),
    ("Christine Navarro", "Back Office"),
    ("Daniel Castillo", "Sales"),
    ("Angelica Dizon", "Customer Support"),
    ("Bryan Pascual", "Technical Support"),
    ("Karen Flores", "Back Office"),
    ("Ryan Soriano", "Customer Support"),
]


def _generate_daily_stats(employee_id: int, days: int = 14) -> list[dict]:
    """Generate daily active-time stats for an employee."""
    stats = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        # Most employees hover 85-98%, a few dip below 90%
        if employee_id in (1, 7, 15):  # These employees sometimes underperform
            active_pct = round(random.uniform(0.78, 0.95), 2)
        else:
            active_pct = round(random.uniform(0.88, 0.99), 2)

        hours = round(random.uniform(7.5, 9.0), 1)
        calls = random.randint(18, 55)

        stats.append({
            "date": d.isoformat(),
            "hours_logged": hours,
            "active_time_pct": active_pct,
            "calls_handled": calls,
        })
    return stats


def generate_employees() -> list[dict]:
    """Return a list of 20 employee dicts with nested daily stats."""
    employees = []
    for idx, (name, dept) in enumerate(_EMPLOYEES, start=1):
        emp = {
            "id": idx,
            "employee_id": f"EMP-{idx:04d}",
            "name": name,
            "department": dept,
            "hire_date": (date.today() - timedelta(days=random.randint(180, 1200))).isoformat(),
            "status": "Active",
            "daily_stats": _generate_daily_stats(idx),
        }
        employees.append(emp)
    return employees


def generate_kpi_data(employees: list[dict], days: int = 14) -> list[dict]:
    """Aggregate daily KPI from all employees."""
    today = date.today()
    kpi = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        d_str = d.isoformat()

        total_calls = 0
        total_hours = 0.0
        total_pct = 0.0
        count = 0

        for emp in employees:
            for stat in emp["daily_stats"]:
                if stat["date"] == d_str:
                    total_calls += stat["calls_handled"]
                    total_hours += stat["hours_logged"]
                    total_pct += stat["active_time_pct"]
                    count += 1
                    break

        kpi.append({
            "date": d_str,
            "total_calls": total_calls,
            "avg_hours": round(total_hours / max(count, 1), 1),
            "avg_active_pct": round(total_pct / max(count, 1), 2),
            "headcount": count,
        })
    return kpi


# Pre-generate data at module load for use by the app
EMPLOYEES = generate_employees()
KPI_DATA = generate_kpi_data(EMPLOYEES)
