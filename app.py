import os
import hashlib
import streamlit as st
from dotenv import load_dotenv
from engine import extract_resume, infer_profile, ai_profile, search_jobs, score_job, split_search_terms

load_dotenv()
st.set_page_config(page_title='AI Job Hunter', page_icon='🎯', layout='wide')

def secret(name):
    try:
        return st.secrets.get(name) or os.getenv(name, '')
    except Exception:
        return os.getenv(name, '')

st.title('🎯 AI Job Hunter')
st.caption('Upload your resume • Discover live opportunities • Understand your fit')
st.info('Privacy: this app does not intentionally save resumes to a database. Resume text is processed during your session. Enable AI analysis only if you agree to send your resume text to OpenAI. Job searches send search terms and location to Adzuna. Do not upload sensitive information you do not wish to share.')

with st.sidebar:
    st.header('Job search preferences')
    role = st.text_area('Target roles (comma or new line separated)', placeholder='Site Reliability Engineer, Production Engineer', height=76)
    location = st.text_area('Locations (comma or new line separated)', placeholder='Florida, North Carolina, Remote', height=76)
    country = st.selectbox('Country', ['us','gb','ca','au'], format_func=lambda x: {'us':'United States','gb':'United Kingdom','ca':'Canada','au':'Australia'}[x])
    remote = st.checkbox('Prioritize remote keywords')
    pages = st.slider('Search depth per combination (25 jobs/page)', 1, 3, 1)
    st.caption('Maximum 12 role/location combinations per search to control API usage.')
    use_ai = st.checkbox('Use OpenAI to analyze my resume', value=False)
    st.caption('AI analysis is optional. Matching scores are explainable keyword/skill heuristics.')

@st.cache_data(ttl=86400, show_spinner=False)
def cached_search(app_id, app_key, role, location, country, pages, remote):
    # 24-hour cache for identical searches; Streamlit does not expose credentials in UI.
    return search_jobs(app_id, app_key, role, location, country, pages, remote)

upload = st.file_uploader('Upload your resume (PDF or DOCX, max 5 MB)', type=['pdf','docx'])
if upload is not None:
    try:
        resume = extract_resume(upload.name, upload.getvalue())
    except Exception as exc:
        st.error(f'Could not read resume: {exc}')
        st.stop()
    profile = infer_profile(resume)
    resume_id = hashlib.sha256(upload.getvalue()).hexdigest()
    if st.session_state.get('skills_resume_id') != resume_id:
        st.session_state['skills_resume_id'] = resume_id
        st.session_state['edited_skills'] = ', '.join(profile['skills'])
        st.session_state.pop('results', None)
        st.session_state.pop('search_summary', None)
        st.session_state.pop('search_errors', None)
        st.session_state.pop('ai_profile', None)
    st.success(f'Resume parsed successfully. Detected {len(profile["skills"])} skills.')
    with st.expander('Detected skills — edit before searching', expanded=True):
        st.text_area('Your skills (comma or new-line separated)', key='edited_skills', height=120,
                     help='Add missing skills or remove incorrect ones. Edits affect job-match scores.')
        edited_skills = list(dict.fromkeys(
            part.strip().lower() for part in st.session_state['edited_skills'].replace('\n', ',').split(',')
            if part.strip()
        ))[:100]
        st.caption(f'{len(edited_skills)} skills selected. Changes are used when ranking jobs.')
        if st.button('Reset skills from resume'):
            st.session_state['edited_skills'] = ', '.join(profile['skills'])
            st.rerun()
    if use_ai:
        if not secret('OPENAI_API_KEY'):
            st.warning('AI analysis requires an OPENAI_API_KEY configured by the app owner.')
        elif st.button('Analyze resume with AI'):
            with st.spinner('Analyzing resume...'):
                try:
                    st.session_state['ai_profile'] = ai_profile(resume, secret('OPENAI_API_KEY'), secret('OPENAI_MODEL') or 'gpt-4o-mini')
                except Exception as exc:
                    st.error(f'AI analysis failed: {exc}')
        if st.session_state.get('ai_profile'):
            info = st.session_state['ai_profile']
            st.subheader('AI career profile')
            st.write(info['summary'])
            st.write('**Suggested roles:** ' + ', '.join(info['suggested_roles']))

    if st.button('🔎 Find matching jobs', type='primary', use_container_width=True):
        roles = split_search_terms(role)
        locations = split_search_terms(location) or ['']
        combinations = [(r, loc) for r in roles for loc in locations]
        if not roles:
            st.warning('Enter at least one target role.')
        elif len(combinations) > 12:
            st.warning(f'{len(combinations)} combinations requested. Please reduce to 12 or fewer to protect API quota.')
        elif not secret('ADZUNA_APP_ID') or not secret('ADZUNA_APP_KEY'):
            st.error('Live job search is not configured. The app owner must add Adzuna credentials.')
        else:
            found_by_id = {}
            errors = []
            progress = st.progress(0, text='Starting job searches...')
            for i, (one_role, one_location) in enumerate(combinations, 1):
                try:
                    matches = cached_search(secret('ADZUNA_APP_ID'), secret('ADZUNA_APP_KEY'),
                                            one_role, one_location, country, pages, remote)
                    for job in matches:
                        found_by_id.setdefault(job['id'], job)
                except Exception as exc:
                    errors.append(f'{one_role} / {one_location or "Anywhere"}: {exc}')
                progress.progress(i / len(combinations), text=f'Searched {i}/{len(combinations)} combinations')
            progress.empty()
            found = list(found_by_id.values())
            for job in found:
                job.update(score_job(resume, job, edited_skills))
            st.session_state['results'] = sorted(found, key=lambda j: j['score'], reverse=True)
            st.session_state['search_summary'] = f'{len(combinations)} searches completed · {len(found)} unique jobs'
            st.session_state['search_errors'] = errors
    if 'search_summary' in st.session_state:
        st.caption(st.session_state['search_summary'])
    if st.session_state.get('search_errors'):
        with st.expander(f"{len(st.session_state['search_errors'])} search(es) failed"):
            for error in st.session_state['search_errors']:
                st.error(error)
    if 'results' in st.session_state:
        results = st.session_state['results']
        for job in results:
            job.update(score_job(resume, job, edited_skills))
        results.sort(key=lambda j: j['score'], reverse=True)
        st.subheader(f'{len(results)} job recommendations')
        st.caption('Match percentages are heuristic relevance estimates, not hiring probabilities. Listings may expire or change.')
        for job in results:
            with st.container(border=True):
                a,b = st.columns([4,1])
                a.markdown(f'#### {job["title"]}')
                a.write(f'**{job["company"]}** · {job["location"]}')
                b.metric('Resume match', f'{job["score"]}%')
                if job['salary_min'] or job['salary_max']:
                    st.write('Salary (as listed): ' + ' – '.join(f'{int(v):,}' for v in [job['salary_min'],job['salary_max']] if v is not None))
                st.write(job['reason'])
                if job['missing']:
                    st.caption('Potential gaps: ' + ', '.join(job['missing'][:10]))
                st.link_button('View / apply at source ↗', job['url'])
else:
    st.markdown('### How it works\n1. Upload a text-based resume.\n2. Choose a target role and location.\n3. Get live listings ranked by skills overlap.\n4. Open the original posting to apply.')

st.divider()
st.caption('AI Job Hunter MVP · No automatic applications · No guarantee of employment · Job data provided by Adzuna')
