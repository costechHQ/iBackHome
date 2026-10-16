"""Report messages (spec: "Weekly report ready": client by WhatsApp + email). Owner: James.

`whatsapp_template` is the name to submit to Meta (utility); its parameters are the placeholders in
the order they appear in `text`.
"""

from app.base.notifications import Template

WEEKLY_REPORT_READY = Template(
    name="report.weekly_ready",
    title="Your weekly report is ready",
    subject="Your iBackHome weekly report",
    text="Your weekly report for {project} (week of {week}) is ready. Open iBackHome to read it.",
    whatsapp_template="weekly_report_ready",
)
