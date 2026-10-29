"""HTML layout for emails that deserve more than plain text (today: the login code).

The plain-text body is always sent too; this is the second part of a multipart message. Email
clients ignore stylesheets and web fonts, so everything is inline and tables do the layout. The
logo is attached to the message and referenced by Content-ID, because a link to our own server
would be blocked as a remote image by most clients (and does not exist on localhost).
Colours come from the web design tokens (web/src/common/theme/tokens.css).
"""

from html import escape
from pathlib import Path

from app.base.notifications.templates import Rendered

LOGO_CID = "ibackhome-logo"
LOGO_PATH = Path(__file__).parent / "assets" / "ibackhome-logo-on-dark.png"

SUPPORT_EMAIL = "support@ibackhome.com"

NAVY = "#00022E"  # --ibh-navy-900
INK = "#0B1324"  # --ibh-ink
SLATE = "#3A4354"  # --ibh-slate
MUTED = "#5F6878"  # --ibh-muted
CANVAS = "#F1F3F5"  # --ibh-canvas
ACCENT = "#2F5FC4"  # --ibh-accent
ACCENT_TINT = "#E8EFFC"  # --ibh-accent-tint
FRAME = "#D5DBE3"  # --ibh-frame
FONT = "Inter, 'Segoe UI', Roboto, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, 'Courier New', monospace"


def login_code_html(code: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:0;background:{CANVAS};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};">
<tr><td align="center" style="padding:24px 12px;">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0"
         style="width:100%;max-width:560px;background:#FFFFFF;border-radius:16px;overflow:hidden;">
    <tr><td align="center" style="background:{NAVY};padding:28px 24px;">
      <img src="cid:{LOGO_CID}" alt="iBackHome" width="170"
           style="display:block;width:170px;height:auto;border:0;">
    </td></tr>
    <tr><td style="padding:32px 32px 8px;font-family:{FONT};">
      <h1 style="margin:0 0 20px;font-size:22px;line-height:28px;letter-spacing:0.04em;
                 text-transform:uppercase;color:{INK};">Your sign-in code</h1>
      <p style="margin:0 0 12px;font-size:16px;line-height:24px;color:{SLATE};">Hello,</p>
      <p style="margin:0 0 24px;font-size:16px;line-height:24px;color:{SLATE};">
        Use the one-time code below to sign in to your iBackHome account.</p>
    </td></tr>
    <tr><td style="padding:0 32px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="background:{ACCENT_TINT};border:1px solid {FRAME};border-radius:12px;">
        <tr><td style="padding:22px 24px;font-family:{FONT};">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
            <td style="font-family:{FONT};font-size:12px;line-height:16px;font-weight:600;
                       letter-spacing:0.08em;text-transform:uppercase;color:{ACCENT};">
              Verification code</td>
            <td align="right" style="font-family:{FONT};font-size:12px;line-height:16px;
                                     font-weight:600;color:{ACCENT};white-space:nowrap;">
              <span style="font-size:15px;">&#128203;</span>&nbsp;Copy</td>
          </tr></table>
          <div style="margin:14px 0 12px;font-family:{MONO};font-size:34px;line-height:40px;
                      font-weight:700;letter-spacing:0.3em;color:{NAVY};
                      -webkit-user-select:all;user-select:all;">{escape(code)}</div>
          <div style="font-size:14px;line-height:20px;color:{MUTED};">
            Valid for 5 minutes. Press and hold the code to copy it.</div>
        </td></tr>
      </table>
    </td></tr>
    <tr><td style="padding:24px 32px 32px;font-family:{FONT};">
      <p style="margin:0 0 16px;font-size:15px;line-height:22px;color:{MUTED};">
        Never share this code with anyone, including iBackHome staff. If you did not try to sign
        in, you can safely ignore this email.</p>
      <p style="margin:0 0 8px;font-size:14px;line-height:20px;color:{MUTED};">
        Questions? Reply to this email or contact
        <a href="mailto:{SUPPORT_EMAIL}" style="color:{INK};">{SUPPORT_EMAIL}</a>.</p>
      <p style="margin:0;font-size:13px;line-height:20px;color:{MUTED};">
        iBackHome &middot; Far from home, never out of sight.</p>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>
"""


def html_for(message: Rendered) -> str | None:
    """The HTML body for this message, or None when it goes as plain text only."""
    if message.template == "auth.login_code" and message.params:
        return login_code_html(message.params[0])
    return None
