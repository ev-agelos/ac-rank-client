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
    fob = open(AC_LOG)
    if LAST_SEEK_POS is None:
        fob.seek(0, os.SEEK_END)
    else:
        fob.seek(LAST_SEEK_POS)        
    while 1:       
        try:
            yield fob.readline()
        except GeneratorExit:
            LAST_SEEK_POS = fob.tell()
            fob.close()
            raise


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
    return [line.rstrip('\n') for line in lines]


def read_setup_changes(follow=False):
    pattern = "Setup change for Car: "
    if not follow:
        return filter(lambda x: x.startswith(pattern), read_ac_log())

    reader = follow_ac_log()
    for line in reader:
        change = None
        if line.startswith(pattern):
            change = line[len(pattern):]
        try:
            yield change
        except GeneratorExit:
            reader.close()
            raise


def read_log_while_in_pits():
    while 1:
        reader = None  # reset reader
        while IN_PIT_Q.get() == 1:
            if reader is None:
                reader = read_setup_changes(follow=True)
            change = next(reader)
            if change is not None:
                SETUP_CHANGES_Q.put(change)

        if reader is not None:
            reader.close()       


logger_reader = Thread(target=read_log_while_in_pits)
logger_reader.setDaemon(True)
logger_reader.start()


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
        if section.lower() != 'car':
            setup[section.lower()] = int(config[section]['VALUE'])

    while not SETUP_CHANGES_Q.empty():
        section, value = load_change_from_line(SETUP_CHANGES_Q.get())
        setup[section] = value

    for change in read_setup_changes():
        if change:
            section, value = load_change_from_line(change)
            setup[section] = value

    return setup


def load_change_from_line(line):
    # section, from, value_before, to, value_after
    section, *_, value = line.split(' ')
    if section in ('CAMPER_LF', 'CAMPER_LR', 'CAMPER_RL', 'CAMPER_RR'):
        value = -abs(round(math.degrees(value) * 10))
    return section.lower(), int(value)