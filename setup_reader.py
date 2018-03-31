import os
import time
import math
import queue
import configparser
from threading import Thread


AC_LOG = os.path.expanduser('~/Documents/Assetto Corsa/logs/log.txt')
IN_PIT_Q = queue.Queue()
SETUP_CHANGES_Q = queue.Queue()
LAST_SEEK_POS = None


def follow_ac_log():
    global LAST_SEEK_POS
    while 1:
        fob = None
        while IN_PIT_Q.get() == 1:
            if fob is None:
                fob = open(AC_LOG)
                if LAST_SEEK_POS is None:
                    fob.seek(0, os.SEEK_END)
                else:
                    fob.seek(LAST_SEEK_POS)

            line = fob.readline()
            if line.startswith("Setup change for Car: "):
                SETUP_CHANGES_Q.put(line)

        LAST_SEEK_POS = fob.tell()
        fob.close()


logger_reader = Thread(target=follow_ac_log)
logger_reader.setDaemon(True)
logger_reader.start()


def read_ac_log():
    global LAST_SEEK_POS
    fob = open(AC_LOG)
    if LAST_SEEK_POS is None:
        fob.seek(0, os.SEEK_END)
    else:
        fob.seek(LAST_SEEK_POS)
    lines = fob.readlines()
    LAST_SEEK_POS = fob.tell()
    fob.close()
    return lines


def load_setup(car):
    """Load and return the setup in a dictionary."""
    setup = {}
    latest_setup = os.path.expanduser(
        '~/Documents/Assetto Corsa/setups/{}/generic/last.ini'.format(car)
    )
    if not os.path.isfile(latest_setup):
        return setup

    config = configparser.ConfigParser()
    config.optionxform = str  # https://stackoverflow.com/a/19359720
    config.read(latest_setup)
    for section in config.sections():
        if section != 'CAR':
            setup[section.lower()] = int(float(config[section]['VALUE']))

    # cant figure out yet how to convert rod values to `clicks`, ignore them
    ignored_sections = [
        'ROD_LENGTH_LF',
        'ROD_LENGTH_RF',
        'ROD_LENGTH_LR',
        'ROD_LENGTH_RR',
        'TOE_OUT_LF',
        'TOE_OUT_RF',
        'TOE_OUT_LR',
        'TOE_OUT_RR'
    ]

    while not SETUP_CHANGES_Q.empty():
        line = SETUP_CHANGES_Q.get()
        section, value = get_section_value_from_line(line)
        if section not in ignored_sections:
            section, value = cast_setup_change(section, value)
            setup[section] = value

    for line in read_ac_log():
        if line.startswith("Setup change for Car: "):
            section, value = get_section_value_from_line(line)
            if section not in ignored_sections:
                section, value = cast_setup_change(section, value)
                setup[section] = value

    return setup


def get_section_value_from_line(line):
    line = line.replace("Setup change for Car: ", '').replace('\n', '')
    change = line.split(' [0] Changing: ')[1]
    # section|from|value_before|to|value_after
    section, *_, value = change.split(' ')
    return section , value


def cast_setup_change(section, value):
    if section in ('CAMPER_LF', 'CAMPER_LR', 'CAMPER_RL', 'CAMPER_RR'):
        value = -abs(round(math.degrees(value) * 10))
    else:
        value = int(float(value))
    return section.lower(), value