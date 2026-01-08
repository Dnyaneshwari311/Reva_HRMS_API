import frappe
from frappe.utils import today, getdate
from datetime import datetime


@frappe.whitelist()
def employee_hrms_dashboard(from_date=None, to_date=None, employee_id=None):
    """
    Date-wise HRMS Dashboard API for Employee (NO TASKS)
    """

    # Detect employee for logged-in user
    if not employee_id:
        employee_id = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user},
            "name"
        )

    if not employee_id:
        frappe.throw("No Employee Linked With This User")

    # Default date range = Current month
    if not from_date:
        from_date = getdate().replace(day=1)
    if not to_date:
        to_date = today()

    emp = frappe.get_doc("Employee", employee_id)

    # ------------------------ ATTENDANCE ---------------------------
    present = frappe.db.count("Attendance", {
        "employee": employee_id,
        "status": "Present",
        "attendance_date": ["between", [from_date, to_date]]
    })

    absent = frappe.db.count("Attendance", {
        "employee": employee_id,
        "status": "Absent",
        "attendance_date": ["between", [from_date, to_date]]
    })

    late_entries = frappe.db.count("Attendance", {
        "employee": employee_id,
        "late_entry": 1,
        "attendance_date": ["between", [from_date, to_date]]
    })

    # ------------------------ LEAVE ---------------------------
    leave_apps = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee_id,
            "status": "Approved",
            "from_date": ["<=", to_date],
            "to_date": [">=", from_date]
        },
        fields=["leave_type", "total_leave_days"]
    )

    leave_summary = {}
    for l in leave_apps:
        leave_summary.setdefault(l.leave_type, 0)
        leave_summary[l.leave_type] += l.total_leave_days

    leave_list = [
        {"leave_type": lt, "taken": leave_summary[lt]}
        for lt in leave_summary
    ]

    # ------------------------ HOLIDAYS ---------------------------
    holidays = frappe.get_all("Holiday",
        filters={
            "parent": emp.holiday_list,
            "holiday_date": ["between", [from_date, to_date]]
        },
        fields=["holiday_date", "description"]
    )

    # ------------------------ FINAL RESPONSE ---------------------------
    return {
        "employee": employee_id,
        "employee_name": emp.employee_name,
        "image": emp.image,
        "designation": emp.designation,

        "from_date": str(from_date),
        "to_date": str(to_date),

        "attendance_summary": {
            "present": present,
            "absent": absent,
            "late": late_entries
        },

        "leave_summary": leave_list,

        "holidays": holidays
    }












@frappe.whitelist(methods=["GET", "POST"])
def get_checkin_list():
    """
    API: Get month-wise attendance summary for logged-in employee
    Returns working days based on attendance.
    
    Optional filters:
    - month (1-12)
    - year (YYYY)
    - from_date / to_date (overrides month/year if provided)
    """

    try:
        # Logged-in user
        user = frappe.session.user
        if user == "Guest":
            return {"success": False, "message": "Login Required To Access This API"}

        # Employee linked to user
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee:
            return {"success": False, "message": "No Employee Linked With This User"}

        data = frappe.form_dict

        # Month & Year filter
        month = int(data.get("month") or datetime.today().month)
        year = int(data.get("year") or datetime.today().year)

        # Override with from_date / to_date if provided
        from_date = data.get("from_date") or datetime(year, month, 1).strftime("%Y-%m-%d")
        to_date = data.get("to_date") or datetime(year, month, 28).strftime("%Y-%m-%d")  # can adjust dynamically

        # Fetch check-ins
        checkins = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
            },
            fields=["log_type", "time"],
            order_by="time asc"
        )

        # Group by date
        daily_summary = {}
        for c in checkins:
            day = str(getdate(c.time))
            daily_summary.setdefault(day, {"check_in": None, "check_out": None})

            if c.log_type == "IN" and not daily_summary[day]["check_in"]:
                daily_summary[day]["check_in"] = str(c.time)
            elif c.log_type == "OUT":
                daily_summary[day]["check_out"] = str(c.time)

        # Count working days = days with both IN and OUT
        working_days = sum(1 for d in daily_summary.values() if d["check_in"] and d["check_out"])

        # Sort by date
        daily_summary = dict(sorted(daily_summary.items()))

        return {
            "success": True,
            "employee": employee,
            "month": month,
            "year": year,
            "total_working_days": working_days,
            "attendance": daily_summary
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Monthly Attendance API Error")
        return {"success": False, "message": "Failed To Fetch Monthly Attendance", "error": str(e)}










@frappe.whitelist(methods=["GET"])
def get_dashboard():
    try:
        user = frappe.session.user
        if user == "Guest":
            return {"message": {"success": False, "message": "Login required"}}

        # Logged-in employee
        logged_employee = frappe.db.get_value(
            "Employee", {"user_id": user}, "name"
        )

        if not logged_employee:
            return {"message": {"success": False, "message": "Employee not linked"}}

        data = frappe.form_dict

        # 🚫 SECURITY CHECK
        if data.get("employee") and data.get("employee") != logged_employee:
            return {
                "message": {
                    "success": False,
                    "message": "You are not allowed to access another employee’s data"
                }
            }

        date_filter = data.get("date")
        from datetime import datetime
        import calendar

        if not date_filter:
            return {"message": {"success": False, "message": "Date is required"}}

        from_date = f"{date_filter} 00:00:00"
        to_date = f"{date_filter} 23:59:59"

        logs = frappe.get_all(
            "Employee Checkin",
            filters={
                "employee": logged_employee,
                "time": ["between", [from_date, to_date]]
            },
            fields=["time"],
            order_by="time asc"
        )

        if not logs:
            return {
                "message": {
                    "success": True,
                    "employee": logged_employee,
                    "date": date_filter,
                    "check_in": "Not Checked In",
                    "check_out": "Not Checked Out",
                    "total_working_days": 0
                }
            }

        check_in = logs[0].time.strftime("%Y-%m-%d %H:%M:%S")
        check_out = (
            logs[-1].time.strftime("%Y-%m-%d %H:%M:%S")
            if len(logs) > 1 else "Not Checked Out"
        )

        return {
            "message": {
                "success": True,
                "employee": logged_employee,
                "date": date_filter,
                "check_in": check_in,
                "check_out": check_out,
                "total_working_days": 1
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Dashboard API Error")
        return {"message": {"success": False, "error": str(e)}}
