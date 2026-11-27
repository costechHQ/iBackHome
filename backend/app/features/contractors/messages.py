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
