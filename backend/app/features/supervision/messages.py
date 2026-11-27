"""Supervision messages. Owner: James.

Spot check assigned (spec: supervisor, push + SMS). Only the visiting supervisor is told: a spot check is
unannounced, so nothing about it ever goes to the contractor or the project's own supervisor.
"""

from app.base.notifications import Template

SPOT_CHECK_ASSIGNED = Template(
    name="spot_check.assigned",
    title="New spot check",
    text="New spot check: please visit {project} on {when}. Open iBackHome for the details.",
)


# The public application form (ADR 0005, slice 1). Email only: the applicant has no account yet.
# Plain text is the whole message; the review order sits in the ops email so nobody pays for an identity
# check before the registration number and the guarantors have passed.
APPLICATION_RECEIVED_OPS = Template(
    name="supervisor_application.received_ops",
    title="New supervisor application",
    text=(
        "New supervisor application\n\n"
        "Name: {full_name}\n"
        "Phone: {phone}\n"
        "Email: {email}\n"
        "Location: {city}, {state}\n"
        "Registration: {registration_body} {registration_no}\n"
        "Years of experience: {years_experience}\n"
        "Guarantor 1: {guarantor_1}\n"
        "Guarantor 2: {guarantor_2}\n"
        "Relatives who are contractors: {relatives}\n"
        "Application id: {application_id}\n"
        "Received: {received}\n\n"
        "Review in this order:\n"
        "1. Check the registration number on the body's own register and note what you saw.\n"
        "2. Call both guarantors.\n"
        "3. Only after 1 and 2 pass, ask the applicant for the NIN and run the paid identity check.\n"
        "Do not ask for the NIN before then."
    ),
)

APPLICATION_RECEIPT = Template(
    name="supervisor_application.receipt",
    title="We received your application",
    text=(
        "Hello {first_name}, we received your application to become an iBackHome supervisor.\n\n"
        "We check your registration number first, then call your guarantors, then contact you by phone or "
        "email. You do not need to do anything now. Please do not send your NIN until we ask for it."
    ),
)
