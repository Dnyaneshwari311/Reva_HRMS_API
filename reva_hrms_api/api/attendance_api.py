import frappe
from frappe import _
import json
from datetime import date
import calendar

def api_error(error, message):
    return {
        "errors": [
            {
                "error": error,
                "message": message
            }
        ]
    }

def api_success(message, data={}):
    return {
        "statusCode": 200,
        "message": message,
        "data": data
    }



# @frappe.whitelist(allow_guest=False)    # Only logged-in user can access
# def create_attendance():

#     try:
#         # -----------------------------
#         # 1. Logged-in employee check
#         # -----------------------------
#         logged_in_user = frappe.session.user

#         if logged_in_user == "Guest":
#             return api_error("Unauthorized", "You must be logged in to mark attendance.")

#         # Get Employee linked to this user
#         employee = frappe.db.get_value("Employee", {"user_id": logged_in_user})
#         if not employee:
#             return api_error("No Employee Found",
#                              "Your user account is not linked to an Employee record.")

#         data = frappe.local.form_dict

#         # -----------------------------
#         # 2. Prevent creating attendance for others
#         # -----------------------------
#         if "employee" in data and data.get("employee") and data.get("employee") != employee:
#             return api_error("Permission Denied",
#                              "You cannot mark attendance for another employee.")

#         # -----------------------------
#         # 3. Shift validation
#         # -----------------------------
#         shift = data.get("shift")
#         if shift and not frappe.db.exists("Shift Type", shift):
#             return api_error("Invalid Shift", f"Shift '{shift}' does not exist")

#         # -----------------------------
#         # 4. Optional: Prevent duplicate attendance
#         # -----------------------------
#         if frappe.db.exists("Attendance",
#                             {"employee": employee, "attendance_date": data.get("attendance_date")}):
#             return api_error("Already Marked",
#                              "You have already marked attendance today.")

#         # -----------------------------
#         # 5. Create Attendance
#         # -----------------------------
#         attendance = frappe.get_doc({
#             "doctype": "Attendance",
#             "employee": employee,                      # FORCE logged-in employee
#             "attendance_date": data.get("attendance_date"),
#             "status": data.get("status"),
#             "in_time": data.get("in_time"),
#             "out_time": data.get("out_time"),
#             "shift": shift,
#             "company": data.get("company")
#         })
#         attendance.insert(ignore_permissions=True)

#         return api_success("Attendance created successfully",
#                            {"attendance_id": attendance.name, "shift": shift})

#     except Exception as e:
#         return api_error("Attendance Creation Failed", str(e))




from frappe.utils import getdate, today

@frappe.whitelist(allow_guest=False)
def create_attendance():
    try:
        # -----------------------------
        # 1. Logged-in employee check
        # -----------------------------
        logged_in_user = frappe.session.user

        if logged_in_user == "Guest":
            return api_error("Unauthorized", "You must be logged in to mark attendance.")

        employee = frappe.db.get_value("Employee", {"user_id": logged_in_user})
        if not employee:
            return api_error(
                "No Employee Found",
                "Your User Account Is Not Linked To An Employee Record."
            )

        data = frappe.local.form_dict

        # -----------------------------
        # 2. Prevent marking for others
        # -----------------------------
        if data.get("employee") and data.get("employee") != employee:
            return api_error(
                "Permission Denied",
                "You Cannot Mark Attendance For Another Employee."
            )

        # -----------------------------
        # 3. Attendance Date validation
        # -----------------------------
        attendance_date = data.get("attendance_date")
        if not attendance_date:
            return api_error("Missing Date", "attendance_date is required.")

        if getdate(attendance_date) > getdate(today()):
            return api_error(
                "Invalid Attendance Date",
                "You Cannot Mark Attendance For A Future Date."
            )

        # -----------------------------
        # 4. Shift validation
        # -----------------------------
        shift = data.get("shift")
        if shift and not frappe.db.exists("Shift Type", shift):
            return api_error("Invalid Shift", f"Shift '{shift}' does not exist")

        # -----------------------------
        # 5. Prevent duplicate attendance
        # -----------------------------
        if frappe.db.exists(
            "Attendance",
            {"employee": employee, "attendance_date": attendance_date}
        ):
            return api_error(
                "Already Marked",
                "You Have Already Marked Attendance For This Date."
            )

        # -----------------------------
        # 6. Create Attendance
        # -----------------------------
        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": data.get("status"),
            "in_time": data.get("in_time"),
            "out_time": data.get("out_time"),
            "shift": shift,
            "company": data.get("company")
        })

        attendance.insert(ignore_permissions=True)

        return api_success(
            "Attendance Created Successfully",
            {
                "attendance_id": attendance.name,
                "attendance_date": attendance_date
            }
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Attendance API Error")
        return api_error("Attendance Creation Failed", str(e))













@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_attendance_list():
    try:
        data = frappe.form_dict

        page = int(data.get("page", 1))
        page_size = int(data.get("page_size", 10))

        month = data.get("month")
        year = data.get("year")

        # 🔐 Logged-in employee
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.session.user},
            "name"
        )

        if not employee:
            frappe.throw("Employee Is Not Linked To This User")

        filters = {
            "employee": employee,
            "docstatus": 1
        }

        # 📅 Month & Year filter
        if month and year:
            month = int(month)
            year = int(year)

            last_day = calendar.monthrange(year, month)[1]
            filters["attendance_date"] = [
                "between",
                [
                    f"{year}-{month:02d}-01",
                    f"{year}-{month:02d}-{last_day}"
                ]
            ]

        # 📊 Count
        total_records = frappe.db.count("Attendance", filters=filters)
        total_pages = (total_records + page_size - 1) // page_size
        start = (page - 1) * page_size

        records = frappe.get_all(
            "Attendance",
            filters=filters,
            fields=[
                "name",
                "attendance_date",
                "status",
                "in_time",
                "out_time",
                "shift",
                "company"
            ],
            limit=page_size,
            start=start,
            order_by="attendance_date desc"
        )

        return {
            "statusCode": 200,
            "message": "Attendance Fetched Successfully",
            "data": {
                "employee": employee,
                "page": page,
                "page_size": page_size,
                "total_records": total_records,
                "total_pages": total_pages,
                "records": records
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Employee Attendance API Error")
        frappe.throw(str(e))






@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_employee_checkin():
    """
    API: Create Employee Checkin (IN / OUT)
    JSON Body:
    {
        "employee": "EMP-0001",
        "log_type": "IN",
        "time": "2025-12-03 10:30:00"   // optional
    }
    """

    try:
        data = frappe.form_dict

        employee = data.get("employee")
        log_type = data.get("log_type")
        time = data.get("time") or now_datetime()    # Auto-assign time

        if not employee:
            return api_error("Employee Is Required")

        if log_type not in ["IN", "OUT"]:
            return api_error("Invalid log_type. Use IN or OUT")

        if not frappe.db.exists("Employee", employee):
            return api_error(f"Employee '{employee}' does not exist")

        # Create Checkin
        doc = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": employee,
            "log_type": log_type,
            "time": time
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        # Convert Doc to JSON
        checkin_data = doc.as_dict()

        # File URLs fix
        for key, value in checkin_data.items():
            if isinstance(value, str) and value.startswith("/files/"):
                checkin_data[key] = frappe.utils.get_url(value)

        return api_success("Checkin Created Successfully", {"checkin": checkin_data})

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Employee Checkin API Error")
        return api_error("Checkin Creation Failed", str(e))
