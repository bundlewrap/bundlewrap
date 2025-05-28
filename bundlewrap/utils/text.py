from datetime import datetime, timedelta
from io import BytesIO
from os import environ
from os.path import normpath
from random import choice
import re
from string import digits, ascii_letters

from . import Fault, STDERR_WRITER


ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
VALID_NAME_CHARS = digits + ascii_letters + "-_.+"


def ansi_clean(input_string):
    return ANSI_ESCAPE.sub("", force_text(input_string))


def ansi_wrapper(colorizer):
    if environ.get("BW_COLORS", "1") != "0":
        return colorizer
    else:
        return lambda s, **kwargs: s


@ansi_wrapper
def blue(text):
    return "\033[34m{}\033[0m".format(text)


@ansi_wrapper
def bold(text):
    return "\033[1m{}\033[0m".format(text)


@ansi_wrapper
def cyan(text):
    return "\033[36m{}\033[0m".format(text)


@ansi_wrapper
def italic(text):
    return "\033[3m{}\033[0m".format(text)


@ansi_wrapper
def green(text):
    return "\033[32m{}\033[0m".format(text)


@ansi_wrapper
def red(text):
    return "\033[31m{}\033[0m".format(text)


@ansi_wrapper
def yellow(text):
    return "\033[33m{}\033[0m".format(text)


def cyan_unless_zero(number):
    if number == 0:
        return "0"
    else:
        return cyan(str(number))


def green_unless_zero(number):
    if number == 0:
        return "0"
    else:
        return green(str(number))


def red_unless_zero(number):
    if number == 0:
        return "0"
    else:
        return red(str(number))


def yellow_unless_zero(number):
    if number == 0:
        return "0"
    else:
        return yellow(str(number))


def error_summary(errors):
    if not errors:
        return

    if len(errors) == 1:
        STDERR_WRITER.write(_("\n{x} There was an error, repeated below.\n\n").format(
            x=red("!!!"),
        ))
        STDERR_WRITER.flush()
    else:
        STDERR_WRITER.write(_("\n{x} There were {count} errors, repeated below.\n\n").format(
            count=len(errors),
            x=red("!!!"),
        ))
        STDERR_WRITER.flush()

    for e in errors:
        STDERR_WRITER.write(e)
        STDERR_WRITER.write("\n")
        STDERR_WRITER.flush()


def force_text(data):
    """
    Try to return a text aka unicode object from the given data.
    """
    if isinstance(data, bytes):
        return data.decode('utf-8', 'replace')
    elif isinstance(data, Fault):
        return data.value
    return data


def is_subdirectory(parent, child):
    """
    Returns True if the given child is a subdirectory of the parent.
    """
    parent = normpath(parent)
    child = normpath(child)

    if not parent.startswith("/") or not child.startswith("/"):
        raise ValueError(_("directory paths must be absolute"))

    if parent == child:
        return False

    if parent == "/":
        return True

    return child.startswith(parent + "/")


def mark_for_translation(s):
    return s
_ = mark_for_translation


def prefix_lines(lines, prefix):
    output = ""
    for line in lines.splitlines():
        output += prefix + line + "\n"
    return output


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def randstr(length=24):
    """
    Returns a random alphanumeric string of the given length.
    """
    return ''.join(choice(ascii_letters + digits) for c in range(length))


def validate_name(name):
    """
    Checks whether the given string is a valid name for a node, group,
    or bundle.
    """
    try:
        for char in name:
            assert char in VALID_NAME_CHARS
        assert not name.startswith(".")
    except AssertionError:
        return False
    return True


def wrap_question(title, body, question, prefix=""):
    output = ("{0}\n"
              "{0} ╭─ {1}\n"
              "{0} │\n".format(prefix, title))
    for line in body.splitlines():
        output += "{0} │  {1}\n".format(prefix, line)
    output += ("{0} │\n"
               "{0} ╰─ ".format(prefix) + question)
    return output


class LineBuffer:
    def __init__(self, target):
        self.buffer = b""
        self.record = BytesIO()
        self.target = target if target else lambda s: None

    def close(self):
        self.flush()
        if self.buffer:
            self.record.write(self.buffer)
            self.target(self.buffer)

    def flush(self):
        while b"\n" in self.buffer:
            chunk, self.buffer = self.buffer.split(b"\n", 1)
            self.record.write(chunk + b"\n")
            self.target(chunk + b"\n")

    def write(self, msg):
        self.buffer += msg
        self.flush()


def format_duration(duration, msec=False):
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
        if msec:
            seconds += duration.microseconds / 1000000.0
            components.append(_("{:.3f}s").format(seconds))
        else:
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


def toml_clean(s):
    """
    Removes duplicate sections from TOML, e.g.:

        [foo]     <--- this line will be removed since it's redundant
        [foo.bar]
        baz = 1
    """
    lines = list(s.splitlines())
    result = []
    previous = ""
    for line in lines.copy():
        if line.startswith("[") and line.endswith("]"):
            if line[1:].startswith(previous + "."):
                result.pop()
            previous = line[1:-1]
        else:
            previous = ""
        result.append(line)
    return "\n".join(result) + "\n"


def trim_visible_len_to(line, target_len):
    use_until = 0
    visible_len = 0
    in_sequence = False
    while use_until < len(line) and visible_len < target_len:
        if line[use_until] == "\033":
            in_sequence = True
        elif in_sequence and line[use_until] == "m":
            in_sequence = False
        elif not in_sequence:
            visible_len += 1
        use_until += 1

    return line[:use_until]
