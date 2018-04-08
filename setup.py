import os
import math
import operator
import configparser
import functools
from itertools import tee

from settings import ACPaths


STEPS = {}


def load_last_setup(car):
    """Return the last.ini setup file as a dictionary."""
    if not os.path.isfile(ACPaths.last_setup(car)):
        return {}
    config = configparser.ConfigParser()
    config.optionxform = str  # https://stackoverflow.com/a/19359720
    config.read(ACPaths.last_setup(car))
    return {section: int(float(config[section]['VALUE']))
            for section in config.sections() if section != 'CAR'}


def make_setup(car, changes):
    last_setup = load_last_setup(car)
    if not last_setup:
        return {}

    setup = last_setup.copy()
    if not changes:
        return setup

    save_steps(changes)
    final_changes = cast_changes(changes, last_setup)
    setup.update(final_changes)
    return setup


def save_steps(changes):
    measured_with_clicks = ('TOE_OUT_', 'ROD_LENGTH_', 'DAMP_', 'ARB_',
                            'ENGINE_LIMITER')
    for key, value_before, value_after in changes.items():
        if key.startswith(measured_with_clicks):
            new_step = abs(value_before - value_after)
            current_step = STEPS.get(key)
            if current_step is None:
                STEPS[key] = new_step
            else:
                STEPS[key] = min([current_step, new_step])


def cast_changes(changes, last_setup):
    measured_with_clicks = ('TOE_OUT_', 'ROD_LENGTH_', 'DAMP_', 'ARB_',
                            'ENGINE_LIMITER')
    new_changes = {}
    for key, old, new in changes.items():
        if key.startswith('CAMBER_'):
            # in general value should be negative and the minus(-) should not
            # be needed, maybe there were positive camber values but car's setup
            # had negative clicks for them
            val = -abs(round(math.degrees(new) * 10))
        elif key.startswith(measured_with_clicks) and not isinstance(new, int):
            old_clicks = int(float(last_setup[key]))
            new_clicks = int((new - old) / STEPS[key])
            val = new_clicks + old_clicks
        else:
            val = int(float(new))
        new_changes[key] = val
    return new_changes