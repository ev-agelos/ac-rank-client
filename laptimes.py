"""Communication with the server."""


from queue import Queue
from urllib.parse import urljoin
import requests

from settings import DOMAIN
from server import handle_response, TASKS
from authentication import auth_required, AUTH


LAPTIMES = Queue()


@auth_required
def add_laptime(splits, car, track, layout=None):
    TASKS.put(dict(func=_add_laptime, args=(splits, car, track),
                   kwargs=dict(layout=layout)))


def get_laptimes(car, track, layout):
    TASKS.put(
        dict(func=_get_laptimes, args=(car, track), kwargs=dict(layout=layout))
    )


def _add_laptime(splits, car, track, layout=None):
    """Return response of adding a new laptime."""
    basic_auth = requests.auth.HTTPBasicAuth(AUTH['user'], AUTH['token'])
    url = urljoin(DOMAIN, 'api/laptimes/add')
    payload = dict(splits=splits, car=car, track=track, layout=layout,
                   car_setup=None)
    response = requests.post(url, auth=basic_auth, json=payload)
    handle_response(response)
    if response.status_code == 200:
        TASKS.put(dict(func=_get_laptimes, args=(car, track),
                       kwargs=dict(layout=layout)))


def _get_laptimes(car, track, layout=None):
    """Return response of getting the laptimes."""
    url = urljoin(DOMAIN, 'api/laptimes/get')
    params = dict(car=car, track=track, layout=layout)
    response = requests.get(url, params=params)
    handle_response(response)
    if response.status_code == 200:
        data = response.json()
        LAPTIMES.put(data)