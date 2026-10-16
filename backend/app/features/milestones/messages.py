"""Milestone messages (spec: "Background jobs and notifications").

Who hears what (notices.py sends them after the change is committed):

| Event                 | Client                  | Contractor     | Supervisor |
| --------------------- | ----------------------- | -------------- | ---------- |
| Milestone claimed     | WhatsApp                |                | push       |
| Milestone verified    | WhatsApp + email        | push           |            |
| Claim rejected        |                         | push           |            |
| Release completed     | WhatsApp + email        | WhatsApp       |            |
| Reminder (daily 09:00)| waiting > 48 h to approve |              | claim waiting > 24 h |

Each channel falls back to the next one (WhatsApp -> push -> SMS -> email) when it can't deliver.
`whatsapp_template` is the template name to submit to Meta; its parameters are the placeholders in
the order they appear in `text`.
"""

from app.base.notifications import Template

CLAIMED_CLIENT = Template(
    name="milestone.claimed.client",
    title="Milestone claimed",
    text="{contractor} says '{milestone}' on {project} is done. Your supervisor will check it on site next.",
    whatsapp_template="milestone_claimed_client",
)

CLAIMED_SUPERVISOR = Template(
    name="milestone.claimed.supervisor",
    title="Milestone to verify",
    text="'{milestone}' on {project} has been claimed. Please visit the site and verify it.",
    whatsapp_template="milestone_claimed_supervisor",
)

VERIFIED_CLIENT = Template(
    name="milestone.verified.client",
    title="Milestone verified",
    subject="A milestone is ready for your approval",
    text=(
        "Your supervisor has verified '{milestone}' on {project}. Review the evidence and approve it "
        "to release {amount} to your contractor."
    ),
    whatsapp_template="milestone_verified_client",
)

VERIFIED_CONTRACTOR = Template(
    name="milestone.verified.contractor",
    title="Milestone verified",
    text="'{milestone}' on {project} was verified by the supervisor. The client approves it next.",
    whatsapp_template="milestone_verified_contractor",
)

REJECTED_CONTRACTOR = Template(
    name="milestone.rejected.contractor",
    title="Claim not verified",
    text="'{milestone}' on {project} was not verified: {reason}. Fix the work and claim it again.",
    whatsapp_template="milestone_rejected_contractor",
)

RELEASED_CLIENT = Template(
    name="milestone.released.client",
    title="Payment released",
    text="{amount} for '{milestone}' on {project} has been released to your contractor.",
    whatsapp_template="milestone_released_client",
)

RELEASED_CONTRACTOR = Template(
    name="milestone.released.contractor",
    title="Payment released",
    text="{amount} for '{milestone}' on {project} has been released to you. The bank transfer follows.",
    whatsapp_template="milestone_released_contractor",
)

REMIND_CLIENT = Template(
    name="milestone.remind.client",
    title="Waiting for your approval",
    text="'{milestone}' on {project} was verified {days} days ago and is waiting for your approval.",
    whatsapp_template="milestone_remind_client",
)

REMIND_SUPERVISOR = Template(
    name="milestone.remind.supervisor",
    title="Claim waiting for you",
    text="'{milestone}' on {project} has been waiting for your verification since {claimed_on}.",
    whatsapp_template="milestone_remind_supervisor",
)
