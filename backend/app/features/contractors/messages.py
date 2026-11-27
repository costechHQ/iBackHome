"""Contractor messages (ADR 0007). Owner: Christopher.

Email only: an applicant has no account until ops approve them. The ops email states the review order, so
nobody is approved before the registration (where one was given) and both references have been checked.
"""

from app.base.notifications import Template

APPLICATION_RECEIVED_OPS = Template(
    name="contractor_application.received_ops",
    title="New contractor application",
    text=(
        "New contractor application\n\n"
        "Business: {business_name}\n"
        "Contact: {contact_name}\n"
        "Phone: {phone}\n"
        "Email: {email}\n"
        "States served: {states}\n"
        "Specialties: {specialties}\n"
        "Years in business: {years}\n"
        "Projects completed (declared): {projects}\n"
        "CAC RC number: {cac}\n"
        "CORBON number: {corbon}\n"
        "Reference 1: {reference_1}\n"
        "Reference 2: {reference_2}\n"
        "Application id: {application_id}\n"
        "Received: {received}\n\n"
        "Review in this order:\n"
        "1. Check the registration number(s) given, on the body's own register, and note what you saw.\n"
        "2. Call both references.\n"
        "3. Open the application in the ops console, tick what you checked, write the profile summary "
        "clients will read, and approve or reject."
    ),
)

APPLICATION_RECEIPT = Template(
    name="contractor_application.receipt",
    title="We received your application",
    text=(
        "Hello {first_name}, we received {business_name}'s application to be listed as an "
        "iBackHome contractor.\n\n"
        "We check your registration first, then call your references, then contact you by phone or "
        "email. You do not need to do anything now."
    ),
)

APPLICATION_APPROVED = Template(
    name="contractor_application.approved",
    title="You are approved",
    text=(
        "Hello {first_name}, {business_name} is now an approved iBackHome contractor. When a client "
        "asks us for a contractor, we may put you forward and phone you first. You can sign in with "
        "this phone number at any time."
    ),
)

APPLICATION_REJECTED = Template(
    name="contractor_application.rejected",
    title="About your application",
    text=(
        "Hello {first_name}, we could not approve {business_name}'s application this time.\n\n"
        "Reason: {reason}\n\n"
        "You are welcome to apply again once this is sorted out."
    ),
)

# Match requests (ADR 0007, phase 2). The ops email goes to OPS_NOTIFY_EMAIL; the other two go to people with
# accounts, so they use notify() (WhatsApp, push, SMS, then email) and carry the project id for the app link.
MATCH_REQUESTED_OPS = Template(
    name="match_request.requested_ops",
    title="A client asked for a contractor",
    text=(
        "A client asked us to find a contractor.\n\n"
        "Project: {project_title}\n"
        "Address: {address}\n"
        "Budget: {budget}\n"
        "Looking in: {city}, {state}\n"
        "Kind of work: {work_type}\n"
        "Timeline: {timeline}\n"
        "Notes: {notes}\n"
        "Client: {client}\n"
        "Request id: {request_id}\n\n"
        "What to do:\n"
        "1. Open Contractors in the ops console and filter the directory by that state and kind of work.\n"
        "2. Phone each contractor you would put forward and check they are free and interested.\n"
        "3. Set a shortlist of 1 to 3 on the request. The client is told and chooses."
    ),
)

MATCH_SHORTLIST_READY = Template(
    name="match_request.shortlist_ready",
    title="Your shortlist is ready",
    text=(
        "We have chosen {count} contractor(s) for {project}. Open iBackHome to read about them and "
        "choose the one you want."
    ),
)

MATCH_CONTRACTOR_CHOSEN = Template(
    name="match_request.contractor_chosen",
    title="A client chose you",
    text=(
        "A client chose you for a project: {project}. Sign in to iBackHome to see it and price the "
        "work in a bill of quantities."
    ),
)
