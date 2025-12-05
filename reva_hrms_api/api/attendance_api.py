import frappe
from frappe import _
import json

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


@frappe.whitelist(allow_guest=True)
def create_attendance():
    """
    Create an Attendance record.

    Expected JSON body (POST or form-data):
    {
        "employee": "EMP/001",
        "attendance_date": "2025-12-03",
        "status": "Present",
        "in_time": "09:00",
        "out_time": "18:00",
        "shift": "Morning",
        "company": "My Company"
    }

    Returns:
    {
        "statusCode": 200,
        "message": "Attendance created successfully",
        "data": {
            "attendance_id": "ATT/0001",
            "shift": "Morning"
        }
    }
    """
    try:
        data = frappe.local.form_dict

        # Validate shift
        shift = data.get("shift")
        if shift and not frappe.db.exists("Shift Type", shift):
            return api_error(
                "Invalid Shift",
                f"Shift '{shift}' does not exist"
            )

        attendance = frappe.get_doc({
            "doctype": "Attendance",
            "employee": data.get("employee"),
            "attendance_date": data.get("attendance_date"),
            "status": data.get("status"),
            "in_time": data.get("in_time"),
            "out_time": data.get("out_time"),
            "shift": data.get("shift"),                      # << Added shift field
            "company": data.get("company")
        })
        attendance.insert(ignore_permissions=True) 
        # attendance.insert()

        return api_success(
            "Attendance created successfully",
            {
                "attendance_id": attendance.name,
                "shift": shift
            }
        )

    except Exception as e:
        return api_error("Attendance Creation Failed", str(e))















# @frappe.whitelist(allow_guest=True)
# def get_attendance_list():
#     """
#     Fetch paginated Attendance records.

#     Expected JSON body (POST or GET params):
#     {
#         "employee": "EMP/001",          # optional filter
#         "status": "Present",            # optional filter
#         "from_date": "2025-12-01",     # optional filter
#         "to_date": "2025-12-03",       # optional filter
#         "search": "Morning",            # optional keyword search
#         "page": 1,                      # optional, default 1
#         "page_size": 10                 # optional, default 10
#     }

#     Returns:
#     {
#         "statusCode": 200,
#         "message": "Attendance list fetched successfully",
#         "data": {
#             "page": 1,
#             "page_size": 10,
#             "total_records": 35,
#             "total_pages": 4,
#             "records": [
#                 {
#                     "name": "ATT/0001",
#                     "employee": "EMP/001",
#                     "employee_name": "John Doe",
#                     "attendance_date": "2025-12-03",
#                     "status": "Present",
#                     "in_time": "09:00",
#                     "out_time": "18:00",
#                     "shift": "Morning",
#                     "company": "My Company"
#                 },
#                 ...
#             ]
#         }
#     }
#     """
#     try:
#         data = frappe.local.form_dict

#         # Pagination
#         page = int(data.get("page", 1))
#         page_size = int(data.get("page_size", 10))
#         start = (page - 1) * page_size

#         # Build WHERE conditions manually
#         where_clause = "WHERE docstatus < 2"
#         conditions = []

#         # Filters
#         if data.get("employee"):
#             conditions.append(f"employee LIKE '%{data.get('employee')}%'")

#         if data.get("status"):
#             conditions.append(f"status = '{data.get('status')}'")

#         if data.get("from_date") and data.get("to_date"):
#             conditions.append(
#                 f"(attendance_date BETWEEN '{data.get('from_date')}' AND '{data.get('to_date')}')"
#             )

#         # Search keyword
#         if data.get("search"):
#             search = data.get("search")
#             conditions.append(
#                 f"(name LIKE '%{search}%' OR employee LIKE '%{search}%' OR shift LIKE '%{search}%')"
#             )

#         # Merge conditions
#         if conditions:
#             where_clause += " AND " + " AND ".join(conditions)

#         # Main Query
#         query = f"""
#             SELECT
#                 name,
#                 employee,
#                 employee_name,
#                 attendance_date,
#                 status,
#                 in_time,
#                 out_time,
#                 shift,
#                 company
#             FROM `tabAttendance`
#             {where_clause}
#             ORDER BY attendance_date DESC
#             LIMIT {start}, {page_size}
#         """

#         records = frappe.db.sql(query, as_dict=True)

#         # Count Query
#         count_query = f"""
#             SELECT COUNT(*) as total
#             FROM `tabAttendance`
#             {where_clause}
#         """
#         total = frappe.db.sql(count_query, as_dict=True)[0].total

#         return api_success(
#             "Attendance list fetched successfully",
#             {
#                 "page": page,
#                 "page_size": page_size,
#                 "total_records": total,
#                 "total_pages": (total + page_size - 1) // page_size,
#                 "records": records
#             }
#         )

#     except Exception as e:
#         return api_error("Attendance Fetch Failed", str(e))


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_attendance_list():
    try:
        data = frappe.form_dict

        page = int(data.get("page", 1))
        page_size = int(data.get("page_size", 10))
        employee = data.get("employee")

        filters = {}
        if employee:
            filters["employee"] = employee

        # Count total records
        total_records = frappe.db.count("Attendance", filters=filters)
        total_pages = (total_records + page_size - 1) // page_size
        start = (page - 1) * page_size

        # Fetch records
        records = frappe.get_all(
            "Attendance",
            filters=filters,
            fields=[
                "name", "employee", "employee_name", "attendance_date",
                "status", "in_time", "out_time", "shift", "company"
            ],
            limit=page_size,
            start=start,      # <-- FIXED (use start instead of offset)
            order_by="attendance_date desc"
        )

        # Base API URL
        base_url = frappe.utils.get_url(
            "/api/method/reva_hrms_api.api.attendance_api.get_attendance_list"
        )

        # Build next/prev URLs
        next_page_url = (
            f"{base_url}?page={page + 1}&page_size={page_size}&employee={employee}"
            if page < total_pages else None
        )

        prev_page_url = (
            f"{base_url}?page={page - 1}&page_size={page_size}&employee={employee}"
            if page > 1 else None
        )

        return {
            "message": {
                "statusCode": 200,
                "message": "Attendance list fetched successfully",
                "data": {
                    "page": page,
                    "page_size": page_size,
                    "total_records": total_records,
                    "total_pages": total_pages,
                    "next_page": next_page_url,
                    "prev_page": prev_page_url,
                    "records": records
                }
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Attendance List API Error")
        return {
            "message": {
                "errors": [
                    {
                        "error": "Attendance list fetch failed",
                        "message": str(e)
                    }
                ]
            }
        }





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
            return api_error("Employee is required")

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
