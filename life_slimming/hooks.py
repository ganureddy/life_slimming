from . import __version__ as app_version

app_name = "life_slimming"
app_title = "life_slimming"
app_publisher = "swathi"
app_description = "Life slimming"
app_email = "swathi.bollineni27@caratred.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/life_slimming/css/life_slimming.css"
# app_include_js = "/assets/life_slimming/js/life_slimming.js"

# include js, css files in header of web template
# web_include_css = "/assets/life_slimming/css/life_slimming.css"
# web_include_js = "/assets/life_slimming/js/life_slimming.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "life_slimming/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Lead" : "public/js/lead_module.js",
              "Appointment":"public/js/create_client.js",
              "Therapy Plan":"public/js/therapy_plan_si.js",
              "Clinical Procedure":"public/js/clinical_procedure_filter_template.js",
              "Patient Appointment":"public/js/patient_appointment.js",
              "Sales Invoice":"public/js/sales_invoice.js",
              "Therapy Session":"public/js/therapy_s.js"
            }
doctype_list_js = {"Lead" : "public/js/lead_status_list.js",
                   "Appointment" : "public/js/appointment_status_list.js",
                   "Patient Appointment": "public/js/patient_app_status.js"
                   }
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}


# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

fixtures = [
    {
        "dt":
            "Custom Field",
            "filters":[[
                "name",
                "in",
                {
                    "Lead-service_and_location",
                    "Lead-category",
                    "Lead-consultant",
                    "Lead-lead_assign_to_branch",
                    "Lead-date_of_birth",
                    "Lead-age",
                    "Lead-enquired_for",
                    "Lead-priority",
                    "Lead-followup",
                    "Lead-status_1",
                    "Lead-column_break_wh97e",
                    "Lead-height",
                    "Lead-weight",
                    "Lead-medical_history",
                    "Healthcare Practitioner-branch",
                    "Practitioner Service Unit Schedule-branch",
                    "Appointment-date",
                    "Appointment-duration",
                    "Appointment-time",
                    "Appointment-column_break_agl3e",
                    "Appointment-appointment_time",
                    "Appointment-branch",
                    "Appointment-category",
                    "Appointment-concern",
                    "Lead-ad_set",
                    "Purchase Receipt Item-addational_discount_",
                    "Appointment-full_name",
                    "Appointment-sex",
                    "Patient-agent_name",
                    "Clinical Procedure-general_procedure",
                    "Clinical Procedure-column_break_1",
                    "Clinical Procedure-pre_procedure",
                    "Clinical Procedure-column_break_3",
                    "Clinical Procedure-post_procedure",
                    "Clinical Procedure-section_break_5",
                    "Clinical Procedure Template-procedure_status",
                    "Therapy Plan-due_date",
                    "Therapy Plan-section_break_zyg18",
                    "Therapy Plan-consultant_name",
                    "Therapy Plan-sharing_incentive",
                    "Therapy Plan-select_incentive_employee",
                    "Therapy Plan-column_break_dr8wy",
                    "Therapy Plan-tele_caller",
                    "Therapy Plan-media",
                    "Therapy Plan-category",
                    "Patient Appointment-call_back_status",
                    "Patient Appointment-service_room",
                    "Patient Appointment-concern",
                    "Patient Appointment-branch",
                    "Appointment-call_back_status",
                    "Therapy Type-minimum_price",
                    "Therapy Type-maximum_price",
                    "Therapy Type-quantity",
                    "Patient Appointment-therapy_plan_1",
                    "Patient Appointment-therapy_type1",
                    "Therapy Session-section_break_9izn1",
                    "Therapy Session-consumed_items",
                    "Therapy Session-branch",
                    "Sales Invoice-branch",
                    "Payment Entry-branch",
                    "Therapy Session-session_details",
                    "Therapy Session-body_composition_analysis_measurement_details",
                    "Therapy Session-section_break_zydxy",
                    "Therapy Session-bmr",
                    "Therapy Session-lean_wt",
                    "Therapy Session-target_fat",
                    "Therapy Session-fat_to",
                    "Therapy Session-tummy_region_of_maximum_girth",
                    "Therapy Session-thighs_9",
                    "Therapy Session-triceps",
                    "Therapy Session-column_break_9tj3o",
                    "Therapy Session-fat",
                    "Therapy Session-water",
                    "Therapy Session-bmi",
                    "Therapy Session-neck",
                    "Therapy Session-waist_1_above_the_iliac_crest",
                    "Therapy Session-arms_mid_pt",
                    "Therapy Session-subscapullar",
                    "Therapy Session-column_break_ypd31",
                    "Therapy Session-lean",
                    "Therapy Session-tgt_wt",
                    "Therapy Session-w_h",
                    "Therapy Session-chest_4_below_arm_pit",
                    "Therapy Session-hip_most_prominent_widest_part_of_hipwhile_lying_down",
                    "Therapy Session-biceps",
                    "Therapy Session-measurements",
                    "Therapy Session-measurement_details",
                    "Patient-branch_name",
                    "Therapy Plan-branch",
                    "Sales Invoice-therapy_plan_reference_id",
                    "Therapy Session-section_break_gad1d",
                    "Therapy Session-before_weight",
                    "Therapy Session-column_break_wokno",
                    "Therapy Session-after_weight",
                    "Therapy Session-column_break_x8dwn",
                    "Therapy Session-weight_loss",
                    "Sales Invoice-service_unit",
                    "Sales Invoice-custom_narration",
                    "Sales Invoice-custom_referring_name",
                    "Sales Invoice-custom_incentive_employee_name",
                    "Sales Invoice-custom_tele_caller",
                    "Therapy Plan-custom_employee_name",
                    "Therapy Plan-custom_incentive_employee_name",
                    "Therapy Session-custom_practitioner_name",
                    "Sales Invoice-custom_section_break_axoph",
                    "Sales Invoice-custom_sharing",
                    "Patient Appointment-custom_duration_time",
                    "Patient Appointment-custom_client_mobile_no",
                    "Sales Invoice-custom_doctor_id",
                    "Sales Invoice-custom_column_break_oyovt",
                    "Sales Invoice-custom_doctor_name",
                    "Sales Invoice-custom_section_break_n2fcd",
                    "Therapy Session-custom_taking_by",
                    "Therapy Session-custom_column_break_mwgr0",
                    "Therapy Session-custom_doctor",
                    "Therapy Session-custom_doctor_name",
                    "Therapy Session-custom_column_break_2szxa",
                    "Therapy Session-custom_dietitian_id",
                    "Therapy Session-custom_dietitian_name",
                    "Therapy Plan Detail-custom_is_offer_",
                },                
            ]]
    }
]


# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "life_slimming.utils.jinja_methods",
#	"filters": "life_slimming.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "life_slimming.install.before_install"
# after_install = "life_slimming.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "life_slimming.uninstall.before_uninstall"
# after_uninstall = "life_slimming.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "life_slimming.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# send_token_via_sms = "life_slimming.two_factor.send_otp_via_msg91"

# Two Factor Authentication bypass
# --------------------------------
# Wraps frappe.twofactor.two_factor_is_enabled_for_ so users listed in
# "Two Factor Bypass Settings" log in without an OTP. See two_factor_bypass.py.
before_request = ["life_slimming.two_factor_bypass.install"]

override_doctype_class = {
    "Appointment": "life_slimming.cc_appointment.CCAppointment",
	# "ToDo": "custom_app.overrides.CustomToDo"
    "Patient Appointment":"life_slimming.get_availability_data.Validate_Patient_Appointment"
}
# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# "User": {
#     "on_update": "life_slimming.events.role_creation"
# }
"Appointment": {
                "after_insert": "life_slimming.events.fetch_details_data",
                "on_update": "life_slimming.events.set_appointment_time",
            },
"Lead": {
            "on_update": "life_slimming.events.restrict_duplicate_lead",
        },
"Lead Entry": {
            "after_insert":"life_slimming.events.new_lead_doc",
            "before_save": "life_slimming.events.duplicate_lead_details"
        },
    # "Contact": {
    #     "on_update": "life_slimming.user_wise_roles.send_whatsapp_on_change"
    # },
# "Purchase Order":{
#     "before_submit":"life_slimming.purchase_order_custom.check_purchase_order_validate"
#     },
# "Closing Checklist": {
#     "after_insert" : "life_slimming.events.closing_checklist_data"
# },
"Patient Appointment":{'on_update':"life_slimming.book_appointment.rename_base_on_conf_status",
                        "before_save":["life_slimming.book_appointment.service_room_restrict",
                                    #    "life_slimming.book_appointment.restrict_patient_appointment_without_payment"
                                    ]
                    },
# "Purchase Order":{"before_submit":"life_slimming.purchase_order_custom.check_purchase_order_validate"}
# "Purchase Order":{"before_submit":"life_slimming.purchase_order_custom.check_purchase_order_validate"},
# "Sales Invoice": {
#     "before_submit": {"life_slimming.events.sii_rate_within_therapy_type_min_max_rate","life_slimming.book_appointment.create_appointment_through_si"}
#     # "life_slimming.book_appointment.create_appointment_through_si"
# },
"Therapy Session":{
    "before_save": "life_slimming.events.restrict_therapy_session_without_payment",
    "before_submit":"life_slimming.book_appointment.create_appointment_through_therapy_s",
    "on_submit":["life_slimming.book_appointment.change_status",
                 "life_slimming.book_appointment.issue_consumed_items_from_stock",
                 "life_slimming.user_wise_roles.send_whatsapp_session_completion_to_client"
                 ]
    },
"Sales Invoice":{
    "on_cancel":"life_slimming.book_appointment.to_check_narration"
},
"Payment Entry":{
    "on_submit":"life_slimming.user_wise_roles.send_payment_details_to_customer"
},
"User":{
    "after_rename":"life_slimming.two_factor_bypass.clear_bypass_cache",
    "on_trash":"life_slimming.two_factor_bypass.clear_bypass_cache"
}
}
# }

# Scheduled Tasks
# ---------------
# scheduler_events = {
#        "cron": {
#            "30 20 * * *": [
#                "life_slimming.daily_sales_appointments_report.run_daily_report"
#            ]
#        }
#    }



# scheduler_events = {
#     "cron": {
#         # Morning closing report — yesterday's full data
#         "0 10 * * *": [
#             "life_slimming.daily_sales_appointments_report.run_morning_report"
#         ],
#         # Evening live update — today's same-day data
#         "30 20 * * *": [
#             "life_slimming.daily_sales_appointments_report.run_evening_report"
#         ],
#     }
# }
#scheduler_events = {
    # "cron":{
    
    #     "1 * * * *":['life_slimming.events.background_jobs_for_leads']
    # }
# scheduler_events = {
#     "cron":{
    
#         "1 * * * *":['life_slimming.events.background_jobs_for_leads']
#     }
# 	# "all": [
# 	# 	"life_slimming.tasks.all"
# 	# ],
# 	# "daily": [
# 	# 	"life_slimming.tasks.daily"
# 	# ],
# 	# "hourly": [
# 	# 	"life_slimming.tasks.hourly"
# 	# ],
# 	# "weekly": [
# 	# 	"life_slimming.tasks.weekly"
# 	# ],
# 	# "monthly": [
# 	# 	"life_slimming.tasks.monthly"
# 	# ],
# scheduler_events = {
#	"all": [
#		"life_slimming.tasks.all"
#	],
#	"daily": [
#		"life_slimming.tasks.daily"
#	],
#	"hourly": [
#		"life_slimming.tasks.hourly"
#	],
#	"weekly": [
#		"life_slimming.tasks.weekly"
#	],
#	"monthly": [
#		"life_slimming.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "life_slimming.install.before_tests"

# Overriding Methods
# ------------------------------
# #
# override_whitelisted_methods = {
# 	"healthcare.healthcare.doctype.patient_appointment.patient_appointment.PatientAppointment.validate_overlaps": "life_slimming.get_availability_data.validate_overlaps"
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "life_slimming.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "life_slimming.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]


# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"life_slimming.auth.validate"
# ]


website_redirects = [
    {"source": "/", "target": "/app"},
    {"source": "/me", "target": "/frontend"},
    # {"source": "/frontend", "target": "/frontend/timeslots"},
    # {"source": "/login", "target": "/frontend"},
]

# Keep the Vue SPA fallback confined to its own namespace.
website_route_rules = [
    {"from_route": "/life_portal/<path:app_path>", "to_route": "life_portal"},
]



try:
    from life_slimming.two_factor import patch as _patch_msg91_2fa
    _patch_msg91_2fa()
except Exception:
    pass

# Staff-based CC scheduler fields.
after_migrate = ["life_slimming.api.cc_appointment_setup.execute"]
