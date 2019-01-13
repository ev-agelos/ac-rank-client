import functools
from urllib.parse import urljoin

import requests

from settings import DOMAIN, write_auth, read_auth
from server import handle_response, MESSAGES, TASKS

AUTH = dict(user='', token='')
AUTH_IS_VALID = False


def _validate_token(user_id, token):
    """Validate token."""
    global AUTH_IS_VALID
    url = urljoin(DOMAIN, '{}/{}.json'.format(token, user_id))
    response = requests.get(url)
    handle_response(response, msg_on_success='Token is valid.',
                    msg_on_failure='Invalid token.')
    if response.status_code == 200:
        AUTH_IS_VALID = True
        write_auth('auth', token=token, user=user_id)
        AUTH['user'] = user_id
        AUTH['token'] = token
    else:
        AUTH['user'] = ''
        AUTH['token'] = ''
        AUTH_IS_VALID = False


def auth_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if AUTH_IS_VALID:
            return func(*args, **kwargs)
        MESSAGES.put('Invalid token. Request a new one.')    
    return wrapper


def validate_token(user_id, token):
    TASKS.put(dict(func=_validate_token, args=(user_id, token)))