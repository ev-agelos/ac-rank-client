"""Communication with the server."""


from threading import Thread
from queue import Queue
from urllib.parse import urljoin
import functools

import requests
from requests.auth import HTTPBasicAuth

from settings import write_auth, read_auth


AUTH = read_auth()
DOMAIN = 'https://rank.evagelos.xyz'
MESSAGES = Queue()  # info to be shown in the ac app
LAPTIMES = Queue()
TASKS = Queue()


def handle_response(response, msg_on_success=None, msg_on_failure=None):
    """Handle the response of a request."""
    if response.status_code != 200:
        if msg_on_failure is not None:
            MESSAGES.put(msg_on_failure)
        else:
            MESSAGES.put(response.reason)
    else:
        result = response.json()
        if isinstance(result, dict) and result.get('errors'):
            MESSAGES.put(result['errors'])
        elif isinstance(result, dict) and 'message' in result:
            MESSAGES.put(result['message'])
        elif msg_on_success is not None:  # if custom msg was given
            MESSAGES.put(msg_on_success)


def _get_token(username, password):
    """Get new token from the server."""
    url = urljoin(DOMAIN, 'new.json')
    response = requests.post(url, username=username, password=password)
    if response.status_code == 200:
        data = response.json()
        auth = dict(token=data.get('token', ''), user=data.get('user', ''))
        write_auth('auth', **auth)
        MESSAGES.put('Token updated.')
    else:
        MESSAGES.put('Could not request new token.')


def _validate_auth():
    """Validate auth and put an appropriate message to MESSAGES queue."""
    msg_when_invalid = 'Current token is invalid. Login to get a new one.'
    if AUTH is None:
        MESSAGES.put(msg_when_invalid)
    else:
        url = urljoin(DOMAIN,
                      '{}/{}.json'.format(AUTH['token'], AUTH['user']))
        response = requests.get(url)
        handle_response(response,
                        msg_on_failure=msg_when_invalid,
                        msg_on_success='Token is valid.')


def validate_auth():
    TASKS.put(dict(func=_validate_auth))


def get_token(username, password):
    TASKS.put(dict(func=_get_token, args=(username, password)))


def auth_required(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if AUTH is not None:
            return func(*args, **kwargs)
        MESSAGES.put('Invalid token. Request a new one.')    
    return wrapper


@auth_required
def add_laptime(splits, car, track, layout=None):
    TASKS.put([
        dict(func=_add_laptime, args=(splits, car, track),
             kwargs=dict(layout=layout)),
        dict(func=_get_laptimes, args=(car, track),
             kwargs=dict(layout=layout))
    ])


@auth_required
def get_laptimes(car, track, layout):
    TASKS.put(
        dict(func=_get_laptimes, args=(car, track), kwargs=dict(layout=layout))
    )


def _add_laptime(splits, car, track, layout=None):
    """Return response of adding a new laptime."""
    basic_auth = HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/add')
    payload = dict(splits=splits, car=car, track=track, layout=layout)
    response = requests.post(url, auth=basic_auth, json=payload)
    handle_response(response)


def _get_laptimes(car, track, layout=None):
    """Return response of getting the laptimes."""
    auth = HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/get')
    params = dict(car=car, track=track, layout=layout)
    response = requests.get(url, auth=auth, params=params)
    if response.status_code != 200:
        MESSAGES.put('Could not retrieve laptimes from server.')
    else:
        data = response.json()
        LAPTIMES.put(data)
        MESSAGES.put('Laptimes updated.')


def process_tasks():
    while 1:
        if TASKS.empty():
            continue

        task = TASKS.get()
        if isinstance(task, list):
            # prepare lambdas to execute all functions in 1 thread
            maps = map(
                lambda t: t['func'](*t['args'], **t['kwargs']), task
            )
            Thread(target=lambda: list(maps)).start()
        else:
            Thread(target=task['func'],
                   args=task.get('args'),
                   kwargs=task.get('kwargs')).start()


Thread(target=process_tasks, daemon=True).start()