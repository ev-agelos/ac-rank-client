"""Communication with the server."""


from queue import Queue
from urllib.parse import urljoin
import requests

from settings import DOMAIN
from server import handle_response, TASKS
from authentication import auth_required, AUTH
from setup import make_setup
from setup_tracker import _get_latest_setup_changes


LAPTIMES = Queue()
UNSAVED_CHANGES = {}


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
    basic_auth = requests.auth.HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/add')
    # TODO: refactor, doesnt make sense to get the setup when there are changes,
    # but because last setup doesnt exist to set it to None
    changes = _get_latest_setup_changes()
    setup = make_setup(car, changes)
    car_setup = {k.lower(): v for k, v in setup.items()}
    payload = dict(splits=splits, car=car, track=track, layout=layout,
                   car_setup=car_setup or None)
    response = requests.post(url, auth=basic_auth, json=payload)
    handle_response(response)
    if response.status_code == 200:
        if not setup:  # there might be changes
            laptime_id = response.json()['laptime_id']
            UNSAVED_CHANGES[laptime_id] = changes
        TASKS.put(dict(func=_get_laptimes, args=(car, track),
                       kwargs=dict(layout=layout)))


def _get_laptimes(car, track, layout=None):
    """Return response of getting the laptimes."""
    auth = requests.auth.HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/get')
    params = dict(car=car, track=track, layout=layout)
    response = requests.get(url, auth=auth, params=params)
    handle_response(response, msg_on_success='Laptimes updated.',
                    msg_on_failure='Could not retrieve laptimes from server.')
    if response.status_code == 200:
        data = response.json()
        LAPTIMES.put(data)