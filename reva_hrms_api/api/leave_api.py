import frappe
from frappe.utils import nowdate, getdate
from reva_hrms_api.api.utils import api_success, api_error


@frappe.whitelist(methods=["GET"])
def get_leave_types():
    try:
        leave_types = frappe.get_all(
            "Leave Type",
            fields=["name", "max_leaves_allowed", "is_lwp", "include_holidays", "carry_forward"]
        )
        return api_success("Leave types fetched", leave_types)
    except Exception as e:
        return api_error(str(e))




# -----------------------------------------------------------
# 1. Get Leave Balance
# -----------------------------------------------------------
@frappe.whitelist(methods=["GET"])
def get_leave_balance(employee=None, leave_type=None, date=None):

    if not employee or not leave_type:
        return api_error("Employee and Leave Type are required")

    date = date or nowdate()

    try:
        # Returns float (remaining leaves)
        remaining = frappe.call(
            "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
            employee,
            leave_type,
            date
        )

        # Fetch leave allocations (total allocated)
        allocation = frappe.get_all(
            "Leave Allocation",
            filters={
                "employee": employee,
                "leave_type": leave_type,
                "from_date": ["<=", date],
                "to_date": [">=", date],
            },
            fields=["total_leaves_allocated"]
        )

        total_allocated = allocation[0].total_leaves_allocated if allocation else 0

        # Calculate leaves taken from approved leave applications
        leaves_taken = frappe.db.sql("""
            SELECT SUM(total_leave_days) 
            FROM `tabLeave Application`
            WHERE employee=%s 
            AND leave_type=%s 
            AND docstatus=1
        """, (employee, leave_type))

        taken = leaves_taken[0][0] or 0

        return api_success(
            "Leave balance fetched successfully",
            {
                "employee": employee,
                "leave_type": leave_type,
                "total_allocated": total_allocated,
                "taken": taken,
                "remaining": remaining
            }
        )

    except Exception as e:
        return api_error(str(e))
    
    
    
    
@frappe.whitelist(methods=["GET"])
def get_leave_allocations(employee=None):
    if not employee:
        return api_error("Employee is required")

    try:
        allocations = frappe.get_all(
            "Leave Allocation",
            filters={"employee": employee, "docstatus": 1},
            fields=[
                "name", "leave_type", "from_date", "to_date",
                "total_leaves_allocated", "total_leaves_consumed"
            ]
        )
        return api_success("Leave allocations fetched", allocations)

    except Exception as e:
        return api_error(str(e))

    
    
    
    
    
    
    
@frappe.whitelist(methods=["POST"])
def apply_leave():
    data = frappe.local.form_dict

    required = ["employee", "leave_type", "from_date", "to_date", "half_day"]
    for r in required:
        if r not in data:
            return api_error(f"{r} is required")

    try:
        doc = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": data.employee,
            "leave_type": data.leave_type,
            "from_date": data.from_date,
            "to_date": data.to_date,
            "half_day": data.half_day,
            "half_day_date": data.get("half_day_date"),
            "description": data.get("description")
        })

        doc.insert()
        return api_success("Leave Applied Successfully", {"name": doc.name})

    except Exception as e:
        return api_error(str(e))

    
    
    
    
    
@frappe.whitelist(methods=["POST"])
def submit_leave(name=None):
    if not name:
        return api_error("Leave Application Name is required")

    try:
        doc = frappe.get_doc("Leave Application", name)
        doc.submit()
        return api_success("Leave Approved Successfully", {"name": doc.name})

    except Exception as e:
        return api_error(str(e))

    
    
    

# -----------------------------------------------------------
# 2. Apply Leave
# -----------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def apply_leave():

    data = frappe.form_dict

    required = ["employee", "leave_type", "from_date", "to_date"]
    for r in required:
        if r not in data:
            return api_error(f"{r} is required")

    try:
        doc = frappe.get_doc({
            "doctype": "Leave Application",
            "employee": data.employee,
            "leave_type": data.leave_type,
            "from_date": data.from_date,
            "to_date": data.to_date,
            "half_day": data.get("half_day") or 0,
            "reason": data.get("reason") or "",
            "status": "Open"
        })

        doc.insert(ignore_permissions=True)
        doc.submit()

        return api_success(
            "Leave applied successfully",
            {"leave_application": doc.name, "status": doc.status}
        )

    except Exception as e:
        return api_error(str(e))



# -----------------------------------------------------------
# 3. Update Leave Status (Approve / Reject)
# -----------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def update_status():

    data = frappe.form_dict
    name = data.get("name")
    action = data.get("action")

    if not name or not action:
        return api_error("Leave name and action are required")

    try:
        doc = frappe.get_doc("Leave Application", name)

        if action == "Approve":
            doc.status = "Approved"
            doc.submit()

        elif action == "Reject":
            doc.status = "Rejected"
            doc.submit()

        else:
            return api_error("Invalid action")

        return api_success("Leave " + action.lower(), {"name": name, "status": doc.status})

    except Exception as e:
        return api_error(str(e))



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
@frappe.whitelist(methods=["POST"])
def cancel_leave():

    name = frappe.form_dict.get("name")
    if not name:
        return api_error("Leave Application name required")

    try:
        doc = frappe.get_doc("Leave Application", name)
        doc.cancel()
        return api_success("Leave cancelled", {"name": name, "status": "Cancelled"})

    except Exception as e:
        return api_error(str(e))
