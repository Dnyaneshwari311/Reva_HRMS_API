import frappe
import random
import string
from frappe.utils import now_datetime, add_to_date
from reva_hrms_api.api.utils import api_error


# ---------------------------------------------------------
# STEP 1: SEND FORGOT PASSWORD OTP
# ---------------------------------------------------------
"""
API: Send Forgot Password OTP  
Method: POST  
URL: /api/method/reva_hrms_api.api.forgot_password.send_forgot_password_otp  

POST JSON Body:
{
    "email": "user@example.com"
}

Response:
{
    "statusCode": 201,
    "message": "OTP sent successfully.",
    "data": {
        "email": "user@example.com",
        "otp_expiry": "2025-12-03 10:15:00"
    }
}
"""
@frappe.whitelist(allow_guest=True, methods=["POST"])
def send_forgot_password_otp(email):
    user = frappe.db.get_value("User", {"email": email}, "name")
    if not user:
        return api_error("User With This Email Does Not Exist.", "UserNotFound")

    otp = ''.join(random.choices(string.digits, k=6))
    expiry_time = add_to_date(now_datetime(), minutes=10)

    frappe.db.set_value("User", user, {
        "otp": otp,
        "otp_expire_time": expiry_time
    })

    try:
        frappe.sendmail(
            recipients=[email],
            subject="Password Reset OTP",
            message=f"Your OTP is {otp}. It Expires In 10 Minutes."
        )
    except Exception as e:
        frappe.log_error(str(e), "OTP Email Error")
        return api_error("Failed To Send OTP Email.", "EmailSendError")

    return {
        "statusCode": 201,
        "message": "OTP Sent Successfully.",
        "data": {
            "email": email,
            "otp_expiry": str(expiry_time)
        }
    }


# ---------------------------------------------------------
# STEP 2: VERIFY OTP
# ---------------------------------------------------------
"""
API: Verify OTP  
Method: POST  
URL: /api/method/reva_hrms_api.api.forgot_password.verify_forgot_password_otp  

POST JSON Body:
{
    "email": "user@example.com",
    "otp": "123456"
}

Response:
{
    "statusCode": 200,
    "message": "OTP verified successfully.",
    "data": {
        "email": "user@example.com"
    }
}
"""
@frappe.whitelist(allow_guest=True, methods=["POST"])
def verify_forgot_password_otp(email, otp):
    if not email or not otp:
        return api_error("Email And OTP Are Required.", "MissingFields")

    stored_otp, expiry_time = frappe.db.get_value(
        "User",
        {"email": email},
        ["otp", "otp_expire_time"]
    )

    if not stored_otp:
        return api_error("No OTP found. Request a new one.", "OtpNotFound")

    if not expiry_time or now_datetime() > expiry_time:
        return api_error("OTP expired. Request a new one.", "OtpExpired")

    if str(otp).strip() != str(stored_otp).strip():
        return api_error("Invalid OTP.", "OtpMismatch")

    return {
        "statusCode": 200,
        "message": "OTP Verified Successfully.",
        "data": {
            "email": email
        }
    }


# ---------------------------------------------------------
# STEP 3: RESET PASSWORD WITH OTP
# ---------------------------------------------------------
"""
API: Reset Password With OTP  
Method: POST  
URL: /api/method/reva_hrms_api.api.forgot_password.reset_password_with_otp  

POST JSON Body:
{
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewPass123!",
    "confirm_password": "NewPass123!"
}

Response:
{
    "statusCode": 200,
    "message": "Password reset successfully.",
    "data": {
        "email": "user@example.com"
    }
}
"""
@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password_with_otp(email, otp, new_password, confirm_password):
    if not email or not otp or not new_password or not confirm_password:
        return api_error("All fields are required.", "MissingFields")

    if new_password != confirm_password:
        return api_error("Passwords Do Not Match.", "PasswordMismatch")

    stored_otp, expiry_time = frappe.db.get_value(
        "User",
        {"email": email},
        ["otp", "otp_expire_time"]
    )

    if not stored_otp:
        return api_error("No OTP Found. Request A New One.", "OtpNotFound")

    if not expiry_time or now_datetime() > expiry_time:
        return api_error("OTP expired.", "OtpExpired")

    if str(otp).strip() != str(stored_otp).strip():
        return api_error("Invalid OTP.", "OtpMismatch")

    # update password
    user = frappe.get_doc("User", {"email": email})
    user.new_password = new_password
    user.save(ignore_permissions=True)

    # clear OTP
    frappe.db.set_value("User", user.name, {
        "otp": 0,  # Important: use 0 not '' (empty string)
        "otp_expire_time": None
    })

    return {
        "statusCode": 200,
        "message": "Password Reset Successfully.",
        "data": {
            "email": email
        }
    }
