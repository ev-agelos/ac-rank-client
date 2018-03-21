"""Save laptimes to AC Ranking website."""

import sys
sys.path.append('apps/python/acr_client/Lib')

import ac
import acsys

from acr_server import (MESSAGES, LAPTIMES, validate_auth, get_token,
                        add_laptime, get_laptimes)

TOTAL_LAPS_COUNTER = 0


def login_button(x, y):
    """Request a new token along with user id."""
    username, password = ac.getText(USERNAME_INPUT), ac.getText(PASSWORD_INPUT)
    # empty inputs
    ac.setText(USERNAME_INPUT, '')
    ac.setText(PASSWORD_INPUT, '')
    if not username or not password:
        ac.setText(NOTIFICATION, 'No input given.')
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

    LAPTIME_LABELS = {ac.addLabel(app, str(index)) for index in range(10)}
    for index, label in enumerate(LAPTIME_LABELS):
        ac.setSize(label, 70, 20)
        ac.setPosition(label, 200, (index*20) + 50)
    get_laptimes(ac.getCarName(0), ac.getTrackName(0),
                 ac.getTrackConfiguration(0) or None)
    return "ACR"


def update_notification():
    """Update notification label if any message are in the Queue."""
    # TODO slower updates to give a chance to read them
    if not MESSAGES.empty():
        ac.setText(NOTIFICATION, MESSAGES.get())


def update_laptimes():
    """Update the laptimes labels with the laptimes from server."""
    if not LAPTIMES.empty():
        for label, laptime in zip(LAPTIME_LABELS, LAPTIMES.get()):
            ac.setText(label, laptime['laptime'])
        while not LAPTIMES.empty():  # clear the rest queue
            LAPTIMES.get()


def acUpdate(delta_t):
    """Update continuously with the data from the game."""
    global TOTAL_LAPS_COUNTER
    update_notification()
    update_laptimes()
    total_laps = ac.getCarState(0, acsys.CS.LapCount)
    # delay a bit(50 milliseconds) cause just after start/finish line data is
    # not yet correct by the game
    if total_laps != TOTAL_LAPS_COUNTER and \
        ac.getCarState(0, acsys.CS.LapTime) > 50:
        TOTAL_LAPS_COUNTER = total_laps
        if TOTAL_LAPS_COUNTER > 0:  # laps might got reset
            add_laptime(ac.getLastSplits(0),
                        ac.getCarName(0),
                        ac.getTrackName(0),
                        ac.getTrackConfiguration(0) or None)