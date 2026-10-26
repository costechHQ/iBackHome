"""Subscription messages: the client is told when billing pauses or resumes their project."""

from app.base.notifications import Template

SUBSCRIPTION_PAUSED = Template(
    name="subscription.paused",
    title="Your project is paused",
    subject="Your iBackHome project is paused",
    text=(
        "We could not take your monthly supervision payment for {project}, so work on it is paused "
        "(no claims, approvals or releases). Update your payment details in iBackHome to resume."
    ),
    whatsapp_template="subscription_paused",
)

SUBSCRIPTION_RESUMED = Template(
    name="subscription.resumed",
    title="Your project is running again",
    subject="Your iBackHome project is running again",
    text="Thank you. Your payment for {project} went through and work on it has resumed.",
    whatsapp_template="subscription_resumed",
)
