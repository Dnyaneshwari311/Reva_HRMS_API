import frappe
from frappe import _
from frappe.auth import LoginManager
from reva_hrms_api.api.utils import api_error

@frappe.whitelist(allow_guest=True)
def login_and_get_token():
    """
    POST JSON or form-data:
      { "usr": "email@example.com" or phone number, "pwd": "password" }

    Returns JSON with API key, API secret, and user info.
    """
    data = frappe.local.form_dict or frappe.request.get_json(force=True, silent=True) or {}
    login_input = data.get("usr") or data.get("username") or data.get("email")
    pwd = data.get("pwd") or data.get("password")

    if not login_input or not pwd:
        return {
            "errors": [
                {
                    "error": "Missing Credentials",
                    "message": _("Username/Email/Phone and password are required")
                }
            ]
        }, 400  # 400 is the HTTP status code for Bad Request

    # Detect phone number and fetch actual username/email from DB
    usr = get_user_id_from_input(login_input)

    try:
        # 1️⃣ Authenticate
        lm = LoginManager()
        lm.authenticate(user=usr, pwd=pwd)
        lm.post_login()

        # 2️⃣ Create new API key + secret for this login
        user_doc = frappe.get_doc("User", frappe.session.user)
        api_key, api_secret = _generate_new_api_token(user_doc)
        
        try:
            emp_details = frappe.get_doc("Employee", {"user_id": user_doc.name})
            company = emp_details.company
        except:
            company = ""
            emp_details = {}

        # 3️⃣ Return success with tokens + user info
        return {
            "statusCode": 200,
            "message": "Login successful",
            "data": {
                "user": {
                    "name": user_doc.name,
                    "email": user_doc.email,
                    "full_name": user_doc.full_name,
                    "roles": [r.role for r in user_doc.roles],
                    "company": company,
                    "emp_details": emp_details,
                },
                "token": {
                    "api_key": api_key,
                    "api_secret": api_secret
                }
            }
        }

    except frappe.AuthenticationError:
        return {
            "errors": [
                {
                    "error": "Authentication Error",
                    "message": _("Invalid login credentials")
                }
            ]
        }, 401  # 401 is the HTTP status code for Unauthorized
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Login and Token API Error")
        return {
            "errors": [
                {
                    "error": "Internal Error",
                    "message": str(e)
                }
            ]
        }, 500  # 500 is the HTTP status code for Internal Server Error


def get_user_id_from_input(login_input):
    """Detect phone number and fetch corresponding user id."""
    if login_input.isdigit():  # If numeric, treat as phone number
        user = frappe.db.get_value("User", {"phone": login_input}, "name")
        if user:
            return user
    return login_input


def _generate_new_api_token(user_doc):
    """Generates a fresh API key & secret for the given user."""
    import secrets

    # Generate API key & secret (shortened to 15 chars)
    api_key = secrets.token_urlsafe(15)
    api_secret = secrets.token_urlsafe(15)

    # Store in the User record (overwrite old ones)
    user_doc.api_key = api_key
    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)

    return api_key, api_secret







from frappe.utils.password import check_password, update_password

@frappe.whitelist(allow_guest=False)
def reset_password():
    """
    Reset password for the currently logged-in user.

    POST JSON or form-data:
    {
        "previous_password": "oldPass123",
        "new_password": "NewPass456",
        "confirm_password": "NewPass456"
    }

    Requires authentication.
    """
    if frappe.session.user == "Guest":
        return {
            "errors": [
                {
                    "error": "Not Authenticated",
                    "message": "You must be logged in to change your password"
                }
            ]
        }, 403  # 403 is the HTTP status code for Forbidden

    data = frappe.local.form_dict or frappe.request.get_json(force=True, silent=True) or {}
    previous_password = data.get("previous_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    # Validate inputs
    if not previous_password or not new_password or not confirm_password:
        return {
            "errors": [
                {
                    "error": "Missing Fields",
                    "message": "All fields (previous_password, new_password, confirm_password) are required"
                }
            ]
        }, 400  # 400 for Bad Request

    if new_password != confirm_password:
        return {
            "errors": [
                {
                    "error": "Password Mismatch",
                    "message": "New password and confirm password do not match"
                }
            ]
        }, 400  # 400 for Bad Request

    try:
        # Check old password
        check_password(frappe.session.user, previous_password)

        # Update password
        update_password(frappe.session.user, new_password)

        return {
            "statusCode": 200,
            "message": "Password updated successfully",
            "data": {}
        }

    except frappe.AuthenticationError:
        return {
            "errors": [
                {
                    "error": "Authentication Error",
                    "message": "Previous password is incorrect"
                }
            ]
        }, 401  # 401 Unauthorized
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Reset Password API Error")
        return {
            "errors": [
                {
                    "error": "Internal Error",
                    "message": str(e)
                }
            ]
        }, 500  # 500 Internal Server Error
