"""Delivery: push the latest digest to email. Closes the loop — the radar lands where you read,
not just in reports/. Stdlib only (smtplib + email); no provider SDK.

Configured entirely via env so it works with any SMTP provider (Gmail app password, Fastmail,
SES SMTP, Postmark, etc.) and stays a clean no-op when unconfigured (local runs don't email).

Required env to actually send:
  RADAR_EMAIL_TO        comma-separated recipients
  RADAR_SMTP_HOST       e.g. smtp.gmail.com
  RADAR_SMTP_USER       SMTP username
  RADAR_SMTP_PASS       SMTP password / app password   (store as a CI secret)
Optional:
  RADAR_SMTP_PORT       default 587 (STARTTLS); set 465 for implicit TLS
  RADAR_EMAIL_FROM      default = RADAR_SMTP_USER
  RADAR_REPORT_PATH     default = newest reports/*.md

If RADAR_EMAIL_TO or SMTP creds are missing, this prints a notice and exits 0 (never fails the
pipeline just because delivery isn't set up). Inside GitHub Actions every "not sent" outcome
is also raised as a warning annotation naming the missing variables, so a silent stop is
visible on the run page instead of buried in a green log.

Run: python -m distill.deliver
"""

from __future__ import annotations
import os
import sys
import ssl
import smtplib
import html
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT  # noqa: E402

REPORTS = ROOT / "reports"


def latest_report() -> Path | None:
    p = os.environ.get("RADAR_REPORT_PATH")
    if p:
        return Path(p)
    if not REPORTS.exists():
        return None
    latest = REPORTS / "latest.md"
    if latest.exists() and "# AI Radar — " in latest.read_text(encoding="utf-8"):
        return latest
    dated = sorted(
        p
        for p in REPORTS.glob("*-digest.md")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}-digest\.md", p.name)
        and p.read_text(encoding="utf-8").lstrip().startswith("# AI Radar — ")
    )
    return dated[-1] if dated else None


def md_to_html(md: str) -> str:
    """Tiny, dependency-free markdown->HTML good enough for a digest (headers, bold, links,
    list items, horizontal rules, paragraphs). Not a full parser — the digest format is known
    and narrow, so this stays small rather than pulling in a markdown lib."""
    out_lines, in_list = [], False

    def inline(t: str) -> str:
        t = html.escape(t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        return t

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            continue
        if re.match(r"^---+$", line):
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append("<hr>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            lvl = len(m.group(1))
            out_lines.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            continue
        m = re.match(r"^[-*]\s+(.*)$", line)
        if m:
            if not in_list:
                out_lines.append("<ul>")
                in_list = True
            out_lines.append(f"<li>{inline(m.group(1))}</li>")
            continue
        if in_list:
            out_lines.append("</ul>")
            in_list = False
        out_lines.append(f"<p>{inline(line)}</p>")
    if in_list:
        out_lines.append("</ul>")
    body = "\n".join(out_lines)
    return (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'max-width:680px;margin:0 auto;color:#1a1a1a;line-height:1.5;font-size:15px">'
        f"{body}</div>"
    )


def send(subject: str, md_body: str, recipients: list[str]) -> None:
    host = os.environ["RADAR_SMTP_HOST"]
    port = int(os.environ.get("RADAR_SMTP_PORT", "587"))
    user = os.environ["RADAR_SMTP_USER"]
    password = os.environ["RADAR_SMTP_PASS"]
    sender = os.environ.get("RADAR_EMAIL_FROM", user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(md_body, "plain", "utf-8"))
    msg.attach(MIMEText(md_to_html(md_body), "html", "utf-8"))

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, password)
            s.sendmail(sender, recipients, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, password)
            s.sendmail(sender, recipients, msg.as_string())


def github_report_url(report: Path) -> str | None:
    """Build a github.com blob URL for the report so the email can link to the rendered
    version. Uses GITHUB_REPOSITORY (always set in Actions) + GITHUB_REF_NAME (branch, defaults
    to main). Returns None off-CI / when the repo slug is unknown, so the link is simply
    omitted rather than pointing somewhere wrong."""
    repo = os.environ.get("GITHUB_REPOSITORY")  # e.g. "amaljithkuttamath/ai-radar"
    if not repo:
        return None
    branch = os.environ.get("RADAR_REPORT_BRANCH") or os.environ.get("GITHUB_REF_NAME") or "main"
    return f"https://github.com/{repo}/blob/{branch}/reports/{report.name}"


def _not_sent(reason: str) -> None:
    """Report an undelivered digest. Exit status stays 0 (the digest is already published),
    so in Actions the reason is raised as a warning annotation to keep it from going unseen."""
    print(f"[deliver] {reason}", file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        flat = " ".join(reason.split()).replace("%", "%25")
        print(f"::warning title=Digest email not sent::{flat}")


def main() -> None:
    to = [r.strip() for r in os.environ.get("RADAR_EMAIL_TO", "").split(",") if r.strip()]
    needed = ("RADAR_SMTP_HOST", "RADAR_SMTP_USER", "RADAR_SMTP_PASS")
    missing = ([] if to else ["RADAR_EMAIL_TO"]) + [k for k in needed if not os.environ.get(k)]
    if missing:
        _not_sent(f"email not configured; missing {', '.join(missing)}. Skipping.")
        return
    report = latest_report()
    if not report or not report.exists():
        _not_sent("no report found to send; skipping.")
        return
    md = report.read_text(encoding="utf-8")
    # Strip the reindex nav header (`<!-- radar:nav -->` block) so it doesn't show up as raw
    # markdown at the top of the email. Reuse reindex's stripper to keep the markers in sync.
    try:
        from distill.reindex import _strip_nav

        md = _strip_nav(md)
    except Exception:
        pass  # if reindex import ever changes, still send the (un-stripped) digest
    # Subject = first H1 if present, else the filename stem.
    m = re.search(r"^#\s+(.*)$", md, re.MULTILINE)
    subject = m.group(1).strip() if m else report.stem
    # Footer link to the rendered report on GitHub (omitted if the slug is unknown).
    url = github_report_url(report)
    if url:
        md = md.rstrip() + f"\n\n---\n\n[View this report on GitHub]({url})\n"
    try:
        send(subject, md, to)
        print(f"[deliver] sent '{subject}' to {len(to)} recipient(s).")
    except Exception as ex:
        # Delivery failure must not fail the pipeline (the digest is already committed).
        _not_sent(f"send failed: {type(ex).__name__}: {ex}")


if __name__ == "__main__":
    main()
