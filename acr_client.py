"""Save laptimes to AC Ranking website."""


import sys
sys.path.append('apps/python/acr_client/Lib')

import ac
import acsys

from laptimes import LAPTIMES, add_laptime, get_laptimes
from server import MESSAGES
from authentication import AUTH, validate_token


TOTAL_LAPS_COUNTER = 0
CAR = ac.getCarName(0)
TRACK = ac.getTrackName(0)
LAYOUT = ac.getTrackConfiguration(0) or None


def validate_token_button_func(x, y):
    """Validate user's token."""
    user_id, token = ac.getText(USER_ID_INPUT), ac.getText(TOKEN_INPUT)
    # empty the inputs
    ac.setText(USER_ID_INPUT, '')
    ac.setText(TOKEN_INPUT, '')
    if not user_id or not token:
        ac.setText(NOTIFICATION, 'Check your input.')
    else:
        ac.setText(NOTIFICATION, 'Validating token..')
        validate_token(user_id, token)


def refresh_button_func(x, y):
    """Refresh laptimes."""
    get_laptimes(ac.getCarName(0), ac.getTrackName(0),
                 ac.getTrackConfiguration(0) or None)


def acMain(ac_version):
    """Main function that is invoked by Assetto Corsa."""
    global NOTIFICATION, USER_ID_INPUT, TOKEN_INPUT, LAPTIME_LABELS
    app = ac.newApp("AC-Ranking")
    ac.setSize(app, 400, 300)
    NOTIFICATION = ac.addLabel(app, '')
    ac.setPosition(NOTIFICATION, 15, 20)
    ac.setSize(NOTIFICATION, 190, 20)

    validate_token(AUTH['user'], AUTH['token'])

    USER_ID_INPUT = ac.addTextInput(app, 'User id: ')
    ac.setPosition(USER_ID_INPUT, 20, 50)
    ac.setSize(USER_ID_INPUT, 50, 20)

    TOKEN_INPUT = ac.addTextInput(app, 'Token: ')
    ac.setPosition(TOKEN_INPUT, 20, 80)
    ac.setSize(TOKEN_INPUT, 170, 20)
    validate_token_button = ac.addButton(app, 'Validate token')
    ac.setPosition(validate_token_button, 20, 110)
    ac.setSize(validate_token_button, 120, 20)
    ac.addOnClickedListener(validate_token_button, validate_token_button_func)

    refresh_button = ac.addButton(app, '\u21BB')
    ac.setPosition(refresh_button, 300, 5)
    ac.setSize(refresh_button, 15, 18)
    ac.addOnClickedListener(refresh_button, refresh_button_func)

    LAPTIME_LABELS = tuple(ac.addLabel(app, '#' + str(i)) for i in range(10))
    for index, label in enumerate(LAPTIME_LABELS):
        ac.setSize(label, 120, 20)
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
        if str(laptime['user']) == AUTH['user']:
            ac.setFontColor(label, 0, 0, 1, 1)
            ac.setBackgroundColor(label, 0, 0, 0)
            ac.setBackgroundOpacity(label, 1)
        ac.setText(label, '#{} - {}'.format(index + 1, laptime['laptime']))
    
    for label in LAPTIME_LABELS[len(laptimes):]:  # clear rest of labels
        ac.setText(label, '')
    with LAPTIMES.mutex:  # clear the rest queue
        LAPTIMES.queue.clear()


def acUpdate(delta_t):
    """Update continuously with the data from the game."""
    global TOTAL_LAPS_COUNTER
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