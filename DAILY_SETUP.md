# AI Job Hunter v1.3 — Daily email + saved matches

The existing public Streamlit resume upload and job search remain unchanged. Daily automation is for **one private owner profile**. Never share the daily dashboard password. The scheduled email contains links to job listings and a link to the Streamlit Daily Matches view; the Streamlit view requires the password.

## 1. Create a separate PRIVATE data repository

On GitHub, create a **private** repository named `ai-job-hunter-private-data` (initialize with a README). It will store `profile.json`, `latest.json`, `seen.json`, and dated daily matches. Never change this repo to public: your extracted resume text is stored there.

Create a **fine-grained personal access token** at GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens. Grant access only to `ai-job-hunter-private-data`, with **Contents: Read and write**. Save the token securely. You may need to enable access to the repository or approve organization access depending on GitHub settings.

## 2. Configure Streamlit Cloud secrets

In your existing AI Job Hunter app → Settings → Secrets, keep your current Adzuna and OpenAI keys and add:

```toml
DAILY_DATA_REPO = "YOUR_GITHUB_USERNAME/ai-job-hunter-private-data"
DAILY_GITHUB_TOKEN = "YOUR_FINE_GRAINED_GITHUB_TOKEN"
DAILY_DASHBOARD_PASSWORD = "A_LONG_UNIQUE_PRIVATE_PASSWORD"
```

**Security:** Your public Streamlit app is still accessible to everyone, but the daily dashboard and profile-saving controls require your private password. Avoid saving other users' profiles into the single-owner data repo.

## 3. Save your daily search profile

Open https://ai-job-hunter.streamlit.app/ and enter the private daily dashboard password. Upload your resume, edit your skills, and set target roles/locations in the sidebar. Expand **Save profile for automatic daily job searches**, then click **Save my daily search profile**. This stores your resume text and preferences in the private data repository.

## 4. Set up an SMTP sender

Use an SMTP provider/account that supports authenticated SMTP (for example, a transactional email provider with a verified sender). You **can receive at your Hotmail address** regardless of the sending provider. Do not assume your regular Microsoft account password will work for SMTP; providers often require a special credential or block basic SMTP authentication. Set the SMTP host, port, username, password, and verified sender address according to your provider's documentation. Use port 587 (STARTTLS) or 465 (SSL).

## 5. Configure GitHub Actions secrets

In your **public app code repository** `ai-job-hunter` → Settings → Secrets and variables → Actions → New repository secret, add:

| Secret | Value |
|---|---|
| `ADZUNA_APP_ID` | Your Adzuna app ID |
| `ADZUNA_APP_KEY` | Your Adzuna app key |
| `DAILY_DATA_REPO` | `YOUR_GITHUB_USERNAME/ai-job-hunter-private-data` |
| `DAILY_GITHUB_TOKEN` | Fine-grained token from step 1 |
| `DAILY_EMAIL_TO` | Your recipient email address |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | `587` or `465` |
| `SMTP_USERNAME` | SMTP account login |
| `SMTP_PASSWORD` | SMTP account credential |
| `SMTP_FROM` | Verified sender email address |

**No OpenAI key is required for the scheduled task:** v1.3 uses the existing explainable skills/keyword scoring algorithm, not a new OpenAI ranking call. The optional interactive OpenAI resume analysis is unchanged.

## 6. Deploy and test

Copy the updated files into your local GitHub project, then:

```powershell
git add .
git commit -m "Add private daily job matching and email digest v1.3"
git push origin main
```

Streamlit Cloud should redeploy. In GitHub Actions, open **Daily AI Job Hunter** → **Run workflow** for a manual test. Inspect logs for errors. A successful run saves today's results in the private repo, sends the email, and makes the dashboard view available at https://ai-job-hunter.streamlit.app/?view=daily (password required).

The workflow runs at **8 AM Eastern** using two UTC cron triggers and an Eastern-time check to account for daylight saving time. GitHub's scheduled workflows may be delayed and are not guaranteed to execute exactly on the minute. If no new jobs are found, it still emails a zero-match report. Job listings may be stale or expire. `seen.json` keeps up to 5,000 previously retrieved IDs to avoid repeats; this is a best-effort deduplication strategy.

**Operational caveats:** If sending email fails, the run exits with an error and the report is saved with `email_sent=false`; a manual retry may run another search. The private repository token can expire and will need rotation. Do not share the dashboard password or private token. For multiple users, replace this single-owner design with authenticated per-user storage.
