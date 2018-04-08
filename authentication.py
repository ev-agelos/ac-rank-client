import functools
from urllib.parse import urljoin

import requests

from settings import DOMAIN, write_auth, read_auth
from server import handle_response, MESSAGES, TASKS


AUTH = read_auth()


def _get_token(username, password):
    """Get new token from the server."""
    url = urljoin(DOMAIN, 'new.json')
    response = requests.post(url, dict(username=username, password=password))
    handle_response(response, msg_on_success='Token updated.',
                    msg_on_failure='Could not request new token.')
    if response.status_code == 200:
        data = response.json()
        auth = dict(token=data.get('token', ''), user=data.get('user', ''))
        write_auth('auth', **auth)


def _validate_auth():
    """Validate user and token."""
    url = urljoin(DOMAIN, '{}/{}.json'.format(AUTH['token'], AUTH['user']))
    response = requests.get(url)
    handle_response(
        response,
        msg_on_failure='Could not validate your token. Login to get a new one.',
        msg_on_success='Token is valid.'
    )


def auth_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if AUTH is not None:
            return func(*args, **kwargs)
        MESSAGES.put('Invalid token. Request a new one.')    
    return wrapper


@auth_required
def validate_auth():
    TASKS.put(dict(func=_validate_auth))


def get_token(username, password):
    TASKS.put(dict(func=_get_token, args=(username, password)))