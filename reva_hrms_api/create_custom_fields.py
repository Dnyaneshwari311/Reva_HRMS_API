import frappe

def create_custom_fields():
    custom_fields = [
        {
            "doctype": "Custom Field",
            "dt": "User",  # DocType where the custom field will be added
            "fieldname": "otp",
            "fieldtype": "Int",
            "label": "OTP",
            "insert_after": "last_name",
            "mandatory": 0,
            "reqd": 0,
            "print_hide": 0,
            "hidden": 0,
            "read_only": 0
        },
        {
            "doctype": "Custom Field",
            "dt": "User",
            "fieldname": "otp_expire_time",
            "fieldtype": "Datetime",
            "label": "OTP Expire Time",
            "insert_after": "otp",
            "mandatory": 0,
            "reqd": 0,
            "print_hide": 0,
            "hidden": 0,
            "read_only": 0
        }
    ]

    # Loop through the custom fields and create them
    for field in custom_fields:
        custom_field = frappe.get_doc(field)
        custom_field.insert(ignore_permissions=True)
        print(f"Custom field '{field['fieldname']}' created successfully")

create_custom_fields()
