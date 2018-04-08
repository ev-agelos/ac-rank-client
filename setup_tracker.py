import os
import queue
from threading import Thread

from settings import ACPaths


SETUP_LINES = queue.Queue()


def track_setup_changes():
    log = None
    passed_default_setup_changes = False
    while 1:
        in_pit = SetupTracker.pit.get()
        if in_pit not in (0, 1):
            break  # ac shuts down, exit the loop
        elif in_pit == 1:
            if log is None:
                log = open(ACPaths.log)
                if SetupTracker.last_seek_pos is None:
                    log.seek(0, os.SEEK_END)
                else:
                    log.seek(SetupTracker.last_seek_pos)

            line = log.readline()
            if not passed_default_setup_changes and line.startswith('WAS LATE, HAD TO LOOP '):
                passed_default_setup_changes = True

            if passed_default_setup_changes and line.startswith("Setup change for Car: "):
                SETUP_LINES.put(line)
        else:  # left pits or started outside of pits
            if log is not None:
                SetupTracker.last_seek_pos = log.tell()
                log.close()
                log = None


class SetupTracker:

    pit = queue.Queue()
    last_seek_pos = None

    def __init__(self, car):
        self.car = car

    def start(self):
        Thread(target=track_setup_changes).start()

    @classmethod
    def read_ac_log(cls):
        log = open(ACPaths.log)
        if cls.last_seek_pos is None:
            log.seek(0, os.SEEK_END)
        else:
            log.seek(cls.last_seek_pos)
        lines = log.readlines()
        cls.last_seek_pos = log.tell()
        log.close()
        return lines


def get_section_values_from_line(line):
    line = line.replace("Setup change for Car: ", '').replace('\n', '')
    change = line.split(' [0] Changing: ')[1]
    # section|from|value_before|to|value_after
    section, _, value_before, _, value_after = change.split(' ')
    return section , value_before, value_after


def _get_latest_setup_changes():
    """Return changes happened while in pits."""
    changes = {}
    while not SETUP_LINES.empty():
        line = SETUP_LINES.get()
        section, old_value, new_value = get_section_values_from_line(line)
        changes[section] = float(old_value), float(new_value)

    for line in SetupTracker.read_ac_log():
        if line.startswith("Setup change for Car: "):
            section, old_value, new_value = get_section_values_from_line(line)
            changes[section] = float(old_value), float(new_value)

    return changes