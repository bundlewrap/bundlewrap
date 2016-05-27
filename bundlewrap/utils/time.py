from datetime import datetime, timedelta

from .text import mark_for_translation as _


def format_duration(duration):
    """
    Takes a timedelta and returns something like "1d 5h 4m 3s".
    """
    components = []
    if duration.days > 0:
        components.append(_("{}d").format(duration.days))
    seconds = duration.seconds
    if seconds >= 3600:
        hours = int(seconds / 3600)
        seconds -= hours * 3600
        components.append(_("{}h").format(hours))
    if seconds >= 60:
        minutes = int(seconds / 60)
        seconds -= minutes * 60
        components.append(_("{}m").format(minutes))
    if seconds > 0 or not components:
        components.append(_("{}s").format(seconds))
    return " ".join(components)


def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def parse_duration(duration):
    """
    Parses a string like "1d 5h 4m 3s" into a timedelta.
    """
    days = 0
    seconds = 0
    for component in duration.strip().split(" "):
        component = component.strip()
        if component[-1] == "d":
            days += int(component[:-1])
        elif component[-1] == "h":
            seconds += int(component[:-1]) * 3600
        elif component[-1] == "m":
            seconds += int(component[:-1]) * 60
        elif component[-1] == "s":
            seconds += int(component[:-1])
        else:
            raise ValueError(_("{} is not a valid duration string").format(repr(duration)))
    return timedelta(days=days, seconds=seconds)
