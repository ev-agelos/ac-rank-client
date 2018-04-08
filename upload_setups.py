import os
import sys
import json

import requests

from authentication import AUTH
from settings import ACPaths
from setup import load_last_setup, cast_changes


def _upload_setups(lap_changes, newer_last_setup):
    setups = {}
    for laptime_id, changes in lap_changes.items():
        setups[laptime_id] = newer_last_setup.copy()
        final_changes = cast_changes(changes, newer_last_setup)
        setups[laptime_id].update(final_changes)

    auth = requests.auth.HTTPBasicAuth(AUTH['user'], AUTH['token'])
    for i, (laptime_id, setup) in enumerate(setups.items()):
        car_setup = {k.lower(): v for k, v in setup.items()}
        payload = dict(car_setup=car_setup, laptime_id=laptime_id)
        # TODO: remove this when done
        with open('apps/python/acr_client/possible_setup_{}.json'.format(i), 'w') as fob:
            json.dump(car_setup, fob, indent = 4,sort_keys = True)
        requests.post('/api/laptimes/add-setup', auth=auth, json=payload)
    

if __name__ == '__main__':
    kwargs = json.loads(sys.argv[1])
    if kwargs['last_setup_timestamp'] is not None:  # file existed
        # wait for newer write on last.ini after game shutsdown
        while os.path.getmtime(ACPaths.last_setup(kwargs['car'])) == kwargs['last_setup_timestamp']:
            pass
    _upload_setups(kwargs['changes'], load_last_setup(kwargs['car']))


# FIXME: there is still unhandled exception in some thread
# FIXME: token is invalid but shows could not get laptimes from server