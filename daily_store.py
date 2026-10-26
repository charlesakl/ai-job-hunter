"""Private GitHub repository JSON storage for daily profile and matches."""
import base64
import json
import requests

API = 'https://api.github.com'


def _request(method, repo, path, token, **kwargs):
    if not repo or not token:
        raise ValueError('Configure DAILY_DATA_REPO and DAILY_GITHUB_TOKEN.')
    if not all(part and part.replace('-', '').replace('_', '').replace('.', '').isalnum() for part in repo.split('/')) or len(repo.split('/')) != 2:
        raise ValueError('DAILY_DATA_REPO must be owner/repository.')
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    response = requests.request(method, f'{API}/repos/{repo}/contents/{path}', headers=headers, timeout=25, **kwargs)
    if response.status_code == 404 and method == 'GET':
        return None
    response.raise_for_status()
    return response.json()


def read_json(repo, path, token):
    item = _request('GET', repo, path, token)
    if item is None:
        return None
    if item.get('encoding') != 'base64':
        raise ValueError('Unexpected GitHub response encoding.')
    return json.loads(base64.b64decode(item['content']).decode('utf-8'))


def write_json(repo, path, token, value):
    current = _request('GET', repo, path, token)
    payload = {'message': f'Update AI Job Hunter {path}',
               'content': base64.b64encode(json.dumps(value, ensure_ascii=False, indent=2).encode()).decode()}
    if current:
        payload['sha'] = current['sha']
    return _request('PUT', repo, path, token, json=payload)
