import frappe
from frappe.utils import nowdate, getdate
from reva_hrms_api.api.utils import api_success, api_error
from bs4 import BeautifulSoup


@frappe.whitelist(methods=["GET"])
def get_leave_types():
    try:
        leave_types = frappe.get_all(
            "Leave Type",
            fields=[
                "name",
                "leave_type_name",
                "max_leaves_allowed",
                "is_lwp"
            ]
        )
        return api_success("Leave types fetched", leave_types)
    except Exception as e:
        
        return api_error(str(e))



# -----------------------------------------------------------
# 1. Get Leave Balance
# -----------------------------------------------------------
    



# used api
# @frappe.whitelist(methods=["GET"])
# def get_leave_balance(employee=None):
#     if not employee:
#         return api_error("Employee is required")

#     try:
#         leave_types = frappe.get_all("Leave Type", fields=["name"])
#         result = []

#         for lt in leave_types:
#             # Get total allocated
#             allocation = frappe.get_all(
#                 "Leave Allocation",
#                 filters={
#                     "employee": employee,
#                     "leave_type": lt.name,
#                     "docstatus": 1
#                 },
#                 fields=["total_leaves_allocated"],
#                 limit=1
#             )

#             total_allocated = allocation[0].total_leaves_allocated if allocation else 0

#             # Get balance using ERPNext method (remaining)
#             balance = frappe.call(
#                "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
#                 employee,
#                 lt.name,
#                 nowdate()
#             )

#             # Calculate used leaves
#             used = float(total_allocated) - float(balance)

#             result.append({
#                 "leave_type": lt.name,
#                 "total_leaves_allocated": float(total_allocated),
#                 "used_leaves": float(used),
#                 "balance": float(balance)
#             })

#         return api_success("Leave Balance fetched successfully.", result)

#     except Exception as e:
#         return api_error(str(e))





#----------------------------------------------------------------------------------
# --------------------Get Leave Balance And Total Allocated------------------------
# ---------------------------------------------------------------------------------



@frappe.whitelist(methods=["GET"])
def get_leave_balance(employee=None):
    if not employee:
        return api_error("Employee is required")

    try:
        leave_types = frappe.get_all("Leave Type", fields=["name"])
        result = []

        for lt in leave_types:

            # 1️⃣ Get allocated leaves
            allocation = frappe.get_all(
                "Leave Allocation",
                filters={
                    "employee": employee,
                    "leave_type": lt.name,
                    "docstatus": 1
                },
                fields=["total_leaves_allocated"],
                limit=1
            )

            total_allocated = float(allocation[0].total_leaves_allocated) if allocation else 0.0

            # 2️⃣ Get APPROVED used leaves (ERPNext Default Ledger)
            approved_leaves = frappe.db.sql(
                """
                SELECT ABS(SUM(leaves))
                FROM `tabLeave Ledger Entry`
                WHERE employee = %s
                AND leave_type = %s
                AND transaction_type = 'Leave Application'
                AND is_expired = 0
                AND docstatus = 1
                """,
                (employee, lt.name),
            )[0][0]

            approved_used = float(approved_leaves) if approved_leaves else 0.0

            # 3️⃣ Calculate final balance
            balance = total_allocated - approved_used

            # 4️⃣ Append result EXACTLY in your required format
            result.append({
                "leave_type": lt.name,
                "total_leaves_allocated": total_allocated,
                "approved_used": approved_used,
                "balance": balance
            })

        return api_success("Leave Balance updated successfully.", result)

    except Exception as e:
        return api_error(str(e))





# -------------------------------------------------------------------------------------
# ---------------------------- Leave Creation------------------------------------------
# -------------------------------------------------------------------------------------



    
# @frappe.whitelist(allow_guest=False, methods=["POST"])
# def Create_leave():
#     data = frappe.local.form_dict

#     try:
#         employee = str(data.get("employee"))
#         leave_type = str(data.get("leave_type"))
#         from_date = str(data.get("from_date"))
#         to_date = str(data.get("to_date"))
#         half_day = int(data.get("half_day") or 0)
#         half_day_date = data.get("half_day_date") or None
#         description = str(data.get("description") or "")

#         # Required field check
#         if not employee or not leave_type or not from_date or not to_date:
#             frappe.throw("Missing required fields")

#         leave_doc = frappe.get_doc({
#             "doctype": "Leave Application",
#             "employee": employee,
#             "leave_type": leave_type,
#             "from_date": from_date,
#             "to_date": to_date,
#             "half_day": half_day,
#             "half_day_date": half_day_date,
#             "description": description,
#             "ignore_leave_allocation": 1
#         })

#         # IGNORE PERMISSIONS (safe)
#         leave_doc.flags.ignore_permissions = True
#         leave_doc.flags.ignore_validate = True
#         leave_doc.flags.ignore_mandatory = True
#         leave_doc.flags.ignore_links = True

#         leave_doc.insert()
#         leave_doc.save()

#         return {
#             "status": "success",
#             "message": "Leave Created Successfully",
#             "leave_application": leave_doc.name
#         }

#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Leave API Error")
#         return {
#             "status": "error",
#             "message": str(e)
#         }

    
    
@frappe.whitelist(allow_guest=False, methods=["POST"])
def Create_leave():
    data = frappe.local.form_dict

    try:
        # 1️⃣ Logged-in user
        logged_in_user = frappe.session.user

        # 2️⃣ Get logged-in employee
        logged_in_employee = frappe.db.get_value(
            "Employee", {"user_id": logged_in_user}, "name"
        )

        if not logged_in_employee:
            return {
                "status": "error",
                "message": "Only employees can create leave. No employee linked to this user."
            }

        # 3️⃣ Employee sent in request
        requested_employee = data.get("employee")

        # 4️⃣ STRICT CHECK: Both must match
        if requested_employee != logged_in_employee:
            return {
                "status": "error",
                "message": "You are not allowed to create leave for another employee."
            }

        # 5️⃣ Other fields
        leave_type = data.get("leave_type")
        from_date = data.get("from_date")
        to_date = data.get("to_date")
        half_day = int(data.get("half_day") or 0)
        half_day_date = data.get("half_day_date") or None
        description = data.get("description") or ""

        # 6️⃣ Required fields check
        if not leave_type or not from_date or not to_date:
            return {
                "status": "error",
                "message": "Missing required fields"
            }

        # 7️⃣ Create Leave Application (ONLY for logged-in employee)
        leave_doc = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": logged_in_employee,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "half_day": half_day,
            "half_day_date": half_day_date,
            "description": description,
            "ignore_leave_allocation": 1
        })

        leave_doc.insert(ignore_permissions=True)

        return {
            "status": "success",
            "message": "Leave Created Successfully",
            "leave_application": leave_doc.name,
            "employee": logged_in_employee
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def apply_leave():
    data = frappe.local.form_dict

    try:
        employee = str(data.get("employee"))
        leave_type = str(data.get("leave_type"))
        from_date = frappe.utils.getdate(data.get("from_date"))
        to_date = frappe.utils.getdate(data.get("to_date"))
        half_day = int(data.get("half_day") or 0)
        half_day_date = data.get("half_day_date") or None
        description = str(data.get("description") or "")

        # Required fields check
        if not employee or not leave_type or not from_date or not to_date:
            frappe.throw("Missing required fields")

        # ============================================================
        # 1️⃣ STRICT VALIDATION: EMPLOYEE MUST HAVE POLICY ASSIGNED
        # ============================================================

        policy = frappe.db.get_value(
            "Leave Policy Assignment",
            filters={
                "employee": employee,
                "docstatus": 1
            },
            fieldname=["effective_from", "effective_to"],
            as_dict=True
        )

        if not policy:
            frappe.throw("No Leave Policy Assigned to this employee. Leave cannot be created.")

        # Check leave is within policy date range
        if from_date < policy.effective_from:
            frappe.throw(
                f"Leave cannot be applied before Leave Policy Effective From: {policy.effective_from}"
            )

        if policy.effective_to and to_date > policy.effective_to:
            frappe.throw(
                f"Leave cannot be applied after Leave Policy Effective To: {policy.effective_to}"
            )

        # ============================================================
        # 2️⃣ VALIDATION: LEAVE ALLOCATION DATE CHECK
        # ============================================================

        allocation = frappe.db.get_value(
            "Leave Allocation",
            filters={
                "employee": employee,
                "leave_type": leave_type,
                "docstatus": 1
            },
            fieldname=["from_date", "to_date"],
            as_dict=True
        )

        if not allocation:
            frappe.throw(f"No Leave Allocation found for leave type: {leave_type}")

        # Check leave dates within allocation period
        if from_date < allocation.from_date:
            frappe.throw(
                f"Leave cannot be applied before allocation start date: {allocation.from_date}"
            )

        if to_date > allocation.to_date:
            frappe.throw(
                f"Leave cannot be applied after allocation end date: {allocation.to_date}"
            )

        # ============================================================
        # Create Leave Application
        # ============================================================

        leave_doc = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": employee,
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "half_day": half_day,
            "half_day_date": half_day_date,
            "description": description
        })

        leave_doc.flags.ignore_permissions = True  # allow API user
        leave_doc.insert()                         # ERPNext validations run here too

        return {
            "status": "success",
            "message": "Leave Created Successfully",
            "leave_application": leave_doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Leave API Error")
        return {
            "status": "error",
            "message": str(e)
        }

    

    
    
    


# -----------------------------------------------------------
# 4. Leave List API
# -----------------------------------------------------------
@frappe.whitelist(methods=["GET"])
def get_leave_list():

    employee = frappe.form_dict.get("employee")
    status = frappe.form_dict.get("status")
    page = int(frappe.form_dict.get("page", 1))
    page_size = int(frappe.form_dict.get("page_size", 10))
    offset = (page - 1) * page_size

    filters = {}
    if employee:
        filters["employee"] = employee
    if status:
        filters["status"] = status

    records = frappe.get_all(
        "Leave Application",
        filters=filters,
        fields=["name", "employee", "leave_type", "from_date", "to_date", "status"],
        limit=page_size,
        start=offset,
        order_by="from_date desc"
    )

    total = frappe.db.count("Leave Application", filters)

    next_page = None
    prev_page = None

    if offset + page_size < total:
        next_page = f"/api/method/reva_hrms_api.api.leave.get_leave_list?page={page+1}&page_size={page_size}"

    if page > 1:
        prev_page = f"/api/method/reva_hrms_api.api.leave.get_leave_list?page={page-1}&page_size={page_size}"

    return api_success(
        "Leave list fetched",
        {
            "page": page,
            "page_size": page_size,
            "total": total,
            "next_page": next_page,
            "prev_page": prev_page,
            "records": records
        }
    )



# -----------------------------------------------------------
# 5. Cancel Leave
# -----------------------------------------------------------


import frappe

@frappe.whitelist(allow_guest=False)
def cancel_leave():
    name = frappe.form_dict.get("name")
    if not name:
        return {"status": "error", "message": "Leave Application name required"}

    try:
        doc = frappe.get_doc("Leave Application", name)

        user = frappe.session.user
        employee_from_user = frappe.db.get_value("Employee", {"user_id": user}, "name")

        if not employee_from_user:
            return {"status": "error", "message": "You are not linked with any Employee record"}

        if employee_from_user != doc.employee:
            return {"status": "error", "message": "You are not allowed to cancel this leave"}

        if doc.docstatus != 1:
            return {"status": "error", "message": "Only submitted leaves can be cancelled"}

        doc.cancel()
        return {"status": "success", "message": "Leave cancelled successfully", "data": {"name": name, "status": "Cancelled"}}

    except Exception as e:
        return {"status": "error", "message": str(e)}






# --------------------------------------------------------------------------------------
# ---------------------------GET HOLIDAY LIST-------------------------------------------
# --------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def get_holiday_list():
    """
    Fetch holidays from all Holiday Lists.
    """
    try:
        all_holidays = []

        # Get all Holiday List records
        holiday_lists = frappe.get_all("Holiday List", fields=["name"])

        for hl in holiday_lists:
            doc = frappe.get_doc("Holiday List", hl.name)

            for h in doc.holidays:

                # Convert rich-text description into plain text
                clean_desc = ""
                if h.description:
                    clean_desc = BeautifulSoup(h.description, "html.parser").get_text()

                all_holidays.append({
                    "holiday_list": doc.name,
                    "holiday_date": h.holiday_date,
                    "description": clean_desc   # now plain text
                })

        return api_success("Holiday list fetched", {"holidays": all_holidays})

    except Exception as e:
        return api_error(str(e))
