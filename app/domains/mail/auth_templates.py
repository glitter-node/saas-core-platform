from html import escape


def build_magic_link_email(
    *,
    app_name: str,
    destination_name: str,
    destination_host: str,
    link_url: str,
    expire_minutes: int,
    title: str = "Sign in to your workspace",
    button_label: str = "Sign in",
) -> tuple[str, str, str]:
    safe_app_name = escape(app_name)
    safe_destination_name = escape(destination_name)
    safe_destination_host = escape(destination_host)
    safe_link_url = escape(link_url)
    subject = f"Sign in to {destination_name}"
    text_body = (
        f"{app_name}\n\n"
        f"{title}\n\n"
        "We received a request to sign in to your workspace. Use the link below to continue.\n\n"
        f"{link_url}\n\n"
        f"Destination: {destination_name}\n"
        f"Workspace address: {destination_host}\n\n"
        f"This link will expire in {expire_minutes} minutes.\n\n"
        "If you did not request this email, you can safely ignore it.\n\n"
        f"{app_name}"
    )
    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,sans-serif;color:#1f2933;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#f4f6f8;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:560px;background-color:#ffffff;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:32px 32px 16px 32px;font-size:14px;line-height:20px;font-weight:600;color:#4f5d75;">
                {safe_app_name}
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;font-size:28px;line-height:36px;font-weight:700;color:#111827;">
                {escape(title)}
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;font-size:16px;line-height:24px;color:#374151;">
                We received a request to sign in to your workspace. Use the button below to continue.
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;font-size:14px;line-height:22px;color:#4b5563;">
                Destination: <strong>{safe_destination_name}</strong><br>
                Workspace address: {safe_destination_host}
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px 24px 32px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="border-radius:10px;background-color:#111827;">
                      <a href="{safe_link_url}" style="display:inline-block;padding:14px 24px;font-size:16px;line-height:20px;font-weight:600;color:#ffffff;text-decoration:none;">
                        {escape(button_label)}
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;font-size:14px;line-height:22px;color:#4b5563;">
                This link will expire in {expire_minutes} minutes.
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px 32px;font-size:14px;line-height:22px;color:#4b5563;">
                If the button does not work, copy and paste this link into your browser:
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 24px 32px;font-size:14px;line-height:22px;word-break:break-all;">
                <a href="{safe_link_url}" style="color:#2563eb;text-decoration:underline;">{safe_link_url}</a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 24px 32px;font-size:13px;line-height:20px;color:#6b7280;">
                If you did not request this email, you can safely ignore it.
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px 32px 32px;border-top:1px solid #e5e7eb;font-size:13px;line-height:20px;color:#6b7280;">
                {safe_app_name}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return subject, text_body, html_body
