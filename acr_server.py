"""Communication with the server."""


from threading import Thread
from queue import Queue
from urllib.parse import urljoin
import functools

import requests
from requests.auth import HTTPBasicAuth

from settings import write_auth, read_auth
from setup_reader import load_setup


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


@auth_required
def add_laptime(splits, car, track, layout=None):
    TASKS.put(dict(func=_add_laptime, args=(splits, car, track),
                   kwargs=dict(layout=layout)))


@auth_required
def get_laptimes(car, track, layout):
    TASKS.put(
        dict(func=_get_laptimes, args=(car, track), kwargs=dict(layout=layout))
    )


def _add_laptime(splits, car, track, layout=None):
    """Return response of adding a new laptime."""
    basic_auth = HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/add')
    payload = dict(splits=splits, car=car, track=track, layout=layout,
                   car_setup=load_setup(car) or None)
    response = requests.post(url, auth=basic_auth, json=payload)
    handle_response(response)
    if response.status_code == 200:
        TASKS.put(dict(func=_get_laptimes, args=(car, track),
                       kwargs=dict(layout=layout)))


def _get_laptimes(car, track, layout=None):
    """Return response of getting the laptimes."""
    auth = HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/get')
    params = dict(car=car, track=track, layout=layout)
    response = requests.get(url, auth=auth, params=params)
    handle_response(response, msg_on_success='Laptimes updated.',
                    msg_on_failure='Could not retrieve laptimes from server.')
    if response.status_code == 200:
        data = response.json()
        LAPTIMES.put(data)


def process_tasks():
    while 1:
        if TASKS.empty():
            continue
        task = TASKS.get()
        Thread(target=task['func'], args=task.get('args'),
               kwargs=task.get('kwargs')).start()


Thread(target=process_tasks, daemon=True).start()