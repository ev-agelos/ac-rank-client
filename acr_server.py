"""Communication with the server."""

from threading import Thread
from queue import Queue
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from settings import write_auth, read_auth

AUTH = read_auth()
DOMAIN = 'https://rank.pybook.site'
MESSAGES = Queue()  # info to be shown in the ac app
RESPONSES = Queue()  # for when response needs some sort of handling
LAPTIMES = Queue()


def _handle_response(response, msg_on_success=None, msg_on_failure=None):
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
        else:
            RESPONSES.put(result)


def _get_request(*args, msg_on_success=None, msg_on_failure=None, **kwargs):
    """Make a GET request to server."""
    response = requests.get(*args, **kwargs)
    _handle_response(response, msg_on_success, msg_on_failure)


def _post_request(*args, msg_on_success=None, msg_on_failure=None, **kwargs):
    """Make a POST request to server."""
    response = requests.post(*args, **kwargs)
    _handle_response(response, msg_on_success, msg_on_failure)


def save_auth_from_response(request_thread):
    """Wait until response arrived to save auth to settings.ini."""
    request_thread.join()  # wait for request to finish
    if RESPONSES.empty():  # something went bad with the request
        MESSAGES.put('Could not connect to server.')
    else:
        response = RESPONSES.get()
        auth = dict(token=response.get('token', ''),
                    user=response.get('user', ''))
        write_auth('auth', **auth)
        MESSAGES.put('Token updated.')


def get_token(username, password):
    """Get new token from the server."""
    url = urljoin(DOMAIN, 'token/new.json')
    payload = dict(username=username, password=password)

    request_thread = Thread(target=_post_request, args=[url, payload])
    request_thread.start()
    Thread(target=save_auth_from_response, args=[request_thread]).start()


def validate_auth():
    """Validate auth and put an appropriate message to MESSAGES queue."""
    msg_when_invalid = 'Current token is invalid. Login to get a new one.'
    if AUTH is None:
        MESSAGES.put(msg_when_invalid)
    else:
        url = urljoin(DOMAIN, 'token/{}/{}.json'.format(AUTH['token'],
                                                        AUTH['user']))
        Thread(target=_get_request, args=[url],
               kwargs=dict(msg_on_failure=msg_when_invalid,
                           msg_on_success='Token is valid.')).start()


def add_laptime(splits, car, track, layout=None):
    """Add laptime to server."""
    if AUTH is None:
        MESSAGES.put('Invalid token. Request a new one.')
    else:
        basic_auth = HTTPBasicAuth(AUTH['user'], AUTH['token'])
        url = urljoin(DOMAIN, 'api/laptimes/add')
        payload = dict(splits=splits, car=car, track=track, layout=layout)
        Thread(target=_post_request, args=[url],
               kwargs=dict(auth=basic_auth, json=payload)).start()


def get_laptimes(car, track, layout=None):
    """Return laptimes."""
    if AUTH is None:
        MESSAGES.put('Invalid token. Request a new one.')
    else:
        auth = HTTPBasicAuth(AUTH['user'], AUTH['token'])
        url = urljoin(DOMAIN, 'api/laptimes/get')
        params = dict(car=car, track=track, layout=layout)
        request_thread = Thread(target=_get_request, args=[url],
                                kwargs=dict(auth=auth, params=params))
        request_thread.start()
        Thread(target=update_laptimes, args=[request_thread]).start()


def update_laptimes(request_thread):
    """Update laptimes in the app."""
    request_thread.join()  # wait for laptimes to arrive
    if RESPONSES.empty():  # something went bad with the request
        MESSAGES.put('Could not retrieve laptimes from server.')
    else:
        LAPTIMES.put(RESPONSES.get())
        MESSAGES.put('Laptimes updated.')
