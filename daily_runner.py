"""Daily scheduled job matching and email delivery."""
import html
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from daily_store import read_json, write_json
from engine import search_jobs, score_job, split_search_terms

load_dotenv()


def required(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(f'Missing required secret: {name}')
    return value


def send_email(matches, date):
    host = required('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    username = required('SMTP_USERNAME')
    password = required('SMTP_PASSWORD')
    sender = required('SMTP_FROM')
    recipient = required('DAILY_EMAIL_TO')
    app_url = os.getenv('DAILY_APP_URL', 'https://ai-job-hunter.streamlit.app/').rstrip('/') + '/?view=daily'
    rows = []
    for job in matches[:10]:
        title = html.escape(job['title'])
        company = html.escape(job['company'])
        loc = html.escape(job['location'])
        url = html.escape(job['url'], quote=True)
        rows.append(f'<li><strong>{title}</strong> — {company} ({loc}), match {job["score"]}% — <a href="{url}">Apply</a></li>')
    msg = EmailMessage()
    msg['Subject'] = f'AI Job Hunter — {len(matches)} new matches — {date}'
    msg['From'] = sender
    msg['To'] = recipient
    msg.set_content(f'Your AI Job Hunter found {len(matches)} new job matches. View them: {app_url}')
    msg.add_alternative(f'<h2>Your AI Job Hunter matches — {date}</h2><p>{len(matches)} new opportunities found.</p><ol>{"".join(rows) or "<li>No new matches today.</li>"}</ol><p><a href="{html.escape(app_url, quote=True)}">View your saved matches in AI Job Hunter</a></p>', subtype='html')
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)


def main():
    now = datetime.now(ZoneInfo('America/New_York'))
    # GitHub Actions triggers at both 12:00 and 13:00 UTC to cover DST.
    if os.getenv('GITHUB_ACTIONS') == 'true' and os.getenv('GITHUB_EVENT_NAME') == 'schedule' and now.hour != 8:
        print('Not 8 AM Eastern; skipping this scheduled run.')
        return
    date = now.strftime('%Y-%m-%d')
    repo = required('DAILY_DATA_REPO')
    token = required('DAILY_GITHUB_TOKEN')
    profile = read_json(repo, 'profile.json', token)
    if not profile:
        raise RuntimeError('No saved profile. Open Streamlit and click Save profile for daily search.')
    existing = read_json(repo, f'daily/{date}.json', token)
    if existing and existing.get('email_sent'):
        print('Email already sent today; skipping duplicate.')
        return
    roles = split_search_terms(profile.get('roles', ''))
    locations = split_search_terms(profile.get('locations', '')) or ['']
    combinations = [(role, loc) for role in roles for loc in locations]
    if not combinations or len(combinations) > 12:
        raise ValueError('Saved profile must contain 1–12 role/location combinations.')
    found = {}
    failures = []
    for role, location in combinations:
        try:
            for job in search_jobs(required('ADZUNA_APP_ID'), required('ADZUNA_APP_KEY'), role, location,
                                   profile.get('country', 'us'), 1, profile.get('remote', False)):
                found.setdefault(job['id'], job)
        except Exception as exc:
            failures.append(f'{role} / {location}: {exc}')
    if not found and failures:
        raise RuntimeError('All job searches failed: ' + '; '.join(failures))
    previous = read_json(repo, 'seen.json', token) or {'ids': []}
    seen = set(previous.get('ids', []))
    skills = profile.get('skills', [])
    resume = profile.get('resume', '')
    jobs = []
    for job in found.values():
        job.update(score_job(resume, job, skills))
        if job['id'] not in seen:
            jobs.append(job)
    jobs.sort(key=lambda x: x['score'], reverse=True)
    matches = jobs[:10]
    data = {'date': date, 'matches': matches, 'total_new': len(jobs), 'email_sent': False, 'errors': failures}
    write_json(repo, f'daily/{date}.json', token, data)
    write_json(repo, 'latest.json', token, data)
    # Store seen IDs only after successful retrieval. Limit history to keep GitHub file small.
    new_ids = list(dict.fromkeys(list(previous.get('ids', [])) + [job['id'] for job in found.values()]))[-5000:]
    write_json(repo, 'seen.json', token, {'ids': new_ids})
    send_email(matches, date)
    data['email_sent'] = True
    write_json(repo, f'daily/{date}.json', token, data)
    write_json(repo, 'latest.json', token, data)
    print(f'Sent {len(matches)} job matches for {date}.')


if __name__ == '__main__':
    main()
