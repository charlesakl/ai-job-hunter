# AI Job Hunter — Public MVP

A Streamlit web app for PDF/DOCX resume parsing, optional OpenAI career profiling, Adzuna live job discovery, and explainable skill-match ranking.

## Local setup

1. Install Python 3.11+.
2. In this folder run `python -m venv .venv` then activate it.
3. Run `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set your Adzuna credentials (register at https://developer.adzuna.com/). Optionally set `OPENAI_API_KEY`.
5. Run `streamlit run app.py`.

## Deploy on Streamlit Community Cloud

1. Push the project to a GitHub repository (never commit `.env` or secrets).
2. In Streamlit Community Cloud create an app from the repository with `app.py` as the entrypoint.
3. Under app settings > Secrets, add:

```toml
ADZUNA_APP_ID = "..."
ADZUNA_APP_KEY = "..."
OPENAI_API_KEY = "..." # optional
OPENAI_MODEL = "gpt-4o-mini"
```

4. Deploy and test a sample resume. Verify your Adzuna API plan and usage terms support the expected public traffic.

## MVP limits and privacy

- Only text-based PDFs and DOCX are supported; no OCR.
- No account system, database, saved resumes, or automatic job applications.
- Files are processed in Streamlit server memory; hosting infrastructure may have its own logs/retention. Avoid logging resume contents.
- OpenAI receives resume text only when the user explicitly enables and runs AI analysis. Consult provider data-handling terms before public deployment.
- Adzuna receives role, location and country, not resume text.
- Matching is a transparent heuristic based on skills and overlapping terms, not a calibrated probability or hiring decision.
- Remote filter appends a keyword; it does not guarantee remote-only results.
- Public production launch should add a privacy policy, rate limiting, abuse protection, accessibility review, monitoring, and an appropriate data-processing/retention policy.
- No authentication is implemented. Any visitor could consume your API quota.

## Project structure

- `app.py`: Streamlit interface
- `engine.py`: parsing, search and ranking
- `requirements.txt`: dependencies
- `.env.example`: environment variable template
- `.streamlit/config.toml`: UI/server defaults

## Editable skills (v1.2)
The Detected Skills panel can be edited before or after a job search. Enter comma-separated or newline-separated skills; changes immediately re-rank any displayed results without using extra Adzuna calls. Reset skills from resume restores the automatic detection.
