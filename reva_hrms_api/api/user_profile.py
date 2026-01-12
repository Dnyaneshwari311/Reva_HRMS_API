import frappe
from frappe import _

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


@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_user():
    try:
        data = frappe.local.form_dict

        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        password = data.get("password")
        roles = data.get("roles")  # comma-separated string → "Employee,HR User"

        if not email or not first_name or not password:
            return api_error(
                "Missing Fields",
                "email, first_name and password are Required"
            )

        # Check if user already exists
        if frappe.db.exists("User", email):
            return api_error(
                "User Exists",
                f"User With Email {email} Already Exists"
            )

        # Create new user
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "send_welcome_email": 0,
            "enabled": 1
        })

        user.insert(ignore_permissions=True)

        # Set password
        frappe.utils.password.update_password(user.name, password)

        # Assign Roles
        if roles:
            role_list = [r.strip() for r in roles.split(",")]
            for role in role_list:
                if frappe.db.exists("Role", role):
                    user.add_roles(role)

        frappe.db.commit()

        return api_success(
            "User Created Successfully",
            {
                "user_id": user.name,
                "email": email,
                "roles": roles
            }
        )

    except Exception as e:
        return api_error("User Creation Failed", str(e))














@frappe.whitelist(allow_guest=False, methods=["POST"])
def create_employee():
    try:
        data = frappe.local.form_dict

        first_name = data.get("first_name")
        last_name = data.get("last_name")
        employee_name = f"{first_name} {last_name or ''}".strip()
        company = data.get("company")
        date_of_birth = data.get("date_of_birth")
        date_of_joining = data.get("date_of_joining")
        gender = data.get("gender")
        email = data.get("email")
        create_user = data.get("create_user")  # "1" or "0"

        # Required fields validation
        required_fields = ["first_name", "company", "date_of_joining"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return api_error(
                "Missing Required Fields",
                f"Missing: {', '.join(missing_fields)}"
            )

        # Check duplicate employee by email
        if email and frappe.db.exists("Employee", {"company_email": email}):
            return api_error(
                "Employee Exists",
                f"Employee with email {email} already exists"
            )

        # Step 1: Create User (Optional)
        user_id = None
        if create_user == "1" and email:
            if not frappe.db.exists("User", email):
                user_doc = frappe.get_doc({
                    "doctype": "User",
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "send_welcome_email": 0,
                    "enabled": 1
                })
                user_doc.insert(ignore_permissions=True)
                user_id = user_doc.name
            else:
                user_id = email  # use existing user

        # Step 2: Create Employee
        employee = frappe.get_doc({
            "doctype": "Employee",
            "employee_name": employee_name,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "date_of_birth": date_of_birth,
            "date_of_joining": date_of_joining,
            "gender": gender,
            "company_email": email,
            "user_id": user_id  # link user to employee
        })

        employee.insert(ignore_permissions=True)
        frappe.db.commit()

        return api_success(
            "Employee created successfully",
            {
                "employee_id": employee.name,
                "employee_name": employee.employee_name,
                "user_id": user_id
            }
        )

    except Exception as e:
        return api_error("Employee Creation Failed", str(e))
    
    
    
    
    
    
    
    
    
    
    
    
@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_user_profile():
    """
    Returns the profile details of the currently logged in user.
    """
    try:
        user = frappe.session.user

        if user == "Guest":
            return {
                "status": "error",
                "message": "Authentication required"
            }

        doc = frappe.get_doc("User", user)

        profile = {
            "name": doc.name,
            "full_name": doc.full_name,
            "email": doc.email,
            "username": doc.username,
            "mobile_no": doc.mobile_no,
            "enabled": doc.enabled,
            "roles": [r.role for r in doc.get("roles")],
            "creation": doc.creation,
            "last_login": doc.last_login,
            "last_ip": doc.last_ip
        }

        return {
            "status": "success",
            "data": profile
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
















# import frappe

# def get_full_url(path):
#     """Convert /files/... or /private/files/... to full absolute URL"""
#     if not path:
#         return None
#     site_url = frappe.utils.get_url()   # https://yourdomain.com
#     return f"{site_url}{path}"


# @frappe.whitelist(allow_guest=False, methods=["GET"])
# def get_user_with_employee_details():
#     """
#     Returns logged-in user details + linked employee details in one API.
#     """
#     try:
#         user_id = frappe.session.user

#         if user_id == "Guest":
#             return {
#                 "success": False,
#                 "error": {
#                     "code": "AUTH_REQUIRED",
#                     "message": "Login required."
#                 }
#             }

#         # ----------------------------
#         # Get User Data
#         # ----------------------------
#         user_doc = frappe.get_doc("User", user_id)

#         user_data = {
#             "user_id": user_doc.name,
#             "full_name": user_doc.full_name,
#             "email": user_doc.email,
#             "mobile_no": user_doc.mobile_no,
#             "username": user_doc.username,
#             "enabled": user_doc.enabled,
#             "last_login": str(user_doc.last_login) if user_doc.last_login else None,
#             "roles": [r.role for r in user_doc.roles]
#         }

#         # ----------------------------
#         # Get Linked Employee Data
#         # ----------------------------
#         employee_id = frappe.db.get_value("Employee", {"user_id": user_id}, "name")

#         employee_data = None

#         if employee_id:
#             emp = frappe.get_doc("Employee", employee_id)
#             employee_data = {
#                 "employee_id": emp.name,
#                 "employee_name": emp.employee_name,
#                 "company": emp.company,
#                 "designation": emp.designation,
#                 "department": emp.department,
#                 "gender": emp.gender,
#                 "date_of_birth": str(emp.date_of_birth) if emp.date_of_birth else None,
#                 "date_of_joining": str(emp.date_of_joining) if emp.date_of_joining else None,
#                 "status": emp.status,
#                 "reports_to": emp.reports_to,
#                 "profile_image": get_full_url(emp.image),   # <<< FULL URL ADDED
#                 "contact": {
#                     "mobile_no": emp.cell_number,
#                     "personal_email": emp.personal_email,
#                     "company_email": emp.company_email
#                 },
#                 "address": emp.current_address,
#                 "blood_group": emp.blood_group,
#                 "employment_type": emp.employment_type
#             }

#         # ----------------------------
#         # Response
#         # ----------------------------
#         return {
#             "success": True,
#             "data": {
#                 "user": user_data,
#                 "employee": employee_data
#             }
#         }

#     except Exception as e:
#         return {
#             "success": False,
#             "error": {
#                 "code": "SERVER_ERROR",
#                 "message": str(e)
#             }
#         }








import frappe

def get_full_url(path):
    """Convert /files/... or /private/files/... to full absolute URL"""
    if not path:
        return None
    site_url = frappe.utils.get_url()
    return f"{site_url}{path}"


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_user_with_employee_details():
    """
    Returns full User doc and full Employee doc for logged-in user.
    """
    try:
        user_id = frappe.session.user

        if user_id == "Guest":
            return {
                "success": False,
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Login Required."
                }
            }

        # --------------------------------
        # Get Full User Doc (All Fields)
        # --------------------------------
        user_doc = frappe.get_doc("User", user_id)
        user_data = user_doc.as_dict()

        # Fix profile image (if exists)
        if user_data.get("user_image"):
            user_data["user_image"] = get_full_url(user_data["user_image"])

        # --------------------------------
        # Get Full Employee Doc (All Fields)
        # --------------------------------
        employee_id = frappe.db.get_value("Employee", {"user_id": user_id}, "name")

        employee_data = None

        if employee_id:
            emp_doc = frappe.get_doc("Employee", employee_id)
            employee_data = emp_doc.as_dict()

            # Convert profile image to full URL
            if employee_data.get("image"):
                employee_data["image"] = get_full_url(employee_data["image"])

        # --------------------------------
        # Response
        # --------------------------------
        return {
            "success": True,
            "data": {
                "user": user_data,
                "employee": employee_data
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e)
            }
        }
