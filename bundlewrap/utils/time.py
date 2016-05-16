from .text import mark_for_translation as _


def format_duration(duration):
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
