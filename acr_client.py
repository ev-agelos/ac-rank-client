"""Save laptimes to AC Ranking website."""


import os
import json
import subprocess
from copy import deepcopy
import sys
sys.path.append('apps/python/acr_client/Lib')

import ac
import acsys

from settings import ACPaths
from laptimes import LAPTIMES, add_laptime, get_laptimes, UNSAVED_CHANGES
from server import MESSAGES
from authentication import validate_auth, get_token
from setup_tracker import SetupTracker


TOTAL_LAPS_COUNTER = 0
CAR = ac.getCarName(0)
TRACK = ac.getTrackName(0)
LAYOUT = ac.getTrackConfiguration(0) or None
SETUP_TRACKER = SetupTracker(CAR)
SETUP_TRACKER.start()


def login_button(x, y):
    """Request a new token along with user id."""
    username, password = ac.getText(USERNAME_INPUT), ac.getText(PASSWORD_INPUT)
    # empty the inputs
    ac.setText(USERNAME_INPUT, '')
    ac.setText(PASSWORD_INPUT, '')
    if not username or not password:
        ac.setText(NOTIFICATION, 'Check your input.')
    else:
        ac.setText(NOTIFICATION, 'Requesting new token from server..')
        get_token(username, password)


def acMain(ac_version):
    """Main function that is invoked by Assetto Corsa."""
    global NOTIFICATION, USERNAME_INPUT, PASSWORD_INPUT, LAPTIME_LABELS
    app = ac.newApp("AC-Ranking")
    ac.setSize(app, 400, 300)
    NOTIFICATION = ac.addLabel(app, '')
    ac.setPosition(NOTIFICATION, 5, 20)
    ac.setSize(NOTIFICATION, 190, 20)
    validate_auth()

    USERNAME_INPUT = ac.addTextInput(app, 'Username: ')
    ac.setPosition(USERNAME_INPUT, 20, 50)
    ac.setSize(USERNAME_INPUT, 70, 20)
    PASSWORD_INPUT = ac.addTextInput(app, 'Password: ')
    ac.setPosition(PASSWORD_INPUT, 20, 80)
    ac.setSize(PASSWORD_INPUT, 70, 20)
    SUBMIT_BUTTON = ac.addButton(app, 'Get new token')
    ac.setPosition(SUBMIT_BUTTON, 20, 110)
    ac.setSize(SUBMIT_BUTTON, 70, 20)
    ac.addOnClickedListener(SUBMIT_BUTTON, login_button)

    LAPTIME_LABELS = tuple(ac.addLabel(app, '#' + str(i)) for i in range(10))
    for index, label in enumerate(LAPTIME_LABELS):
        ac.setSize(label, 70, 20)
        ac.setPosition(label, 200, (index*20) + 50)
    get_laptimes(ac.getCarName(0), ac.getTrackName(0),
                 ac.getTrackConfiguration(0) or None)
    return "ACR"


def update_laptimes():
    """Update the laptimes labels with the laptimes from server."""
    if LAPTIMES.empty():
        return
    
    laptimes = LAPTIMES.get()
    for index, (label, laptime) in enumerate(zip(LAPTIME_LABELS, laptimes)):
        ac.setText(label, '#{} - {}'.format(index + 1, laptime['laptime']))
    
    for label in LAPTIME_LABELS[len(laptimes):]:  # clear rest of labels
        ac.setText(label, '')
    with LAPTIMES.mutex:  # clear the rest queue
        LAPTIMES.queue.clear()


def acUpdate(delta_t):
    """Update continuously with the data from the game."""
    global TOTAL_LAPS_COUNTER
    SETUP_TRACKER.pit.put(ac.isCarInPit(0))
    if not MESSAGES.empty():
        ac.setText(NOTIFICATION, MESSAGES.get())
    update_laptimes()

    total_laps = ac.getCarState(0, acsys.CS.LapCount)
    # delay a bit(100 milliseconds) cause just after start/finish line data is
    # not yet correct by the game
    if total_laps != TOTAL_LAPS_COUNTER and \
        ac.getCarState(0, acsys.CS.LapTime) > 100:
        TOTAL_LAPS_COUNTER = total_laps
        if TOTAL_LAPS_COUNTER > 0:  # laps might got reset
            add_laptime(ac.getLastSplits(0), CAR, TRACK, LAYOUT)


def acShutdown():
    SETUP_TRACKER.pit.put('shutdown')

    try:
        timestamp = os.path.getmtime(ACPaths.last_setup(CAR))
    except FileNotFoundError:
        timestamp = None
    kwargs = dict(changes=deepcopy(UNSAVED_CHANGES), car=CAR,
                  last_setup_timestamp=timestamp)
    subprocess.Popen(
        ['cmd', '/K', 'python', 'apps/python/acr_client/upload_setups.py',
        json.dumps(kwargs)],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )