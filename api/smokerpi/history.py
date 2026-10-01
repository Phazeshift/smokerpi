import logging
import math
import os
import threading
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

HEADER = 'point,time,temperature,blower,damper,target'
FILE_TIME = '%Y-%m-%d %H:%M:%S'      # what the CSV holds: sortable and understood by spreadsheets
GRAPH_TIME = '%d/%m/%Y %H:%M:%S'     # what the graph points have always used


def _number(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(text)
    return int(value) if value.is_integer() else value


class History:
    """The graph points, kept in a CSV file so the graph survives a restart and the whole
    session can be downloaded.

    It lives on the Pi's SD card and the Pi can lose power mid-write, so the file is capped at
    max_bytes (the oldest points go first), damaged lines are skipped, and nothing here ever
    raises: a disk problem is logged and the control loop carries on."""

    def __init__(self, path, max_bytes=5 * 1024 * 1024):
        # Fixed now, not looked up from the current directory at each write: the worker thread
        # keeps appending for the life of the process.
        self.path = Path(os.path.abspath(path))
        self.max_bytes = max_bytes
        self._lock = threading.Lock()

    def append(self, index, when, temperature, blower, damper, target):
        line = '%s,%s,%s,%s,%s,%s\n' % (index, when.strftime(FILE_TIME), temperature, blower, damper, target)
        try:
            with self._lock:
                self._prepare()
                with open(self.path, 'a', newline='') as history:
                    history.write(line)
                if os.path.getsize(self.path) > self.max_bytes:
                    self._trim()
        except Exception:
            log.exception('Could not write the history file %s', self.path)

    def recent(self, count):
        """The newest `count` points as graph points ({'i', 'x', 't', 'b', 'd', 's'}), with the
        point numbers they were written with. Those only ever go up, across restarts too: the
        browser asks for points from the last number it saw, so numbering from 0 again would
        leave an open tab waiting for hours."""
        try:
            with self._lock:
                with open(self.path, encoding='utf-8', errors='replace', newline='') as history:
                    lines = history.read().splitlines()
        except FileNotFoundError:
            return []
        except Exception:
            log.exception('Could not read the history file %s', self.path)
            return []
        points = []
        for line in lines:
            point = self._parse(line)
            if point is not None:
                points.append(point)
        return points[-count:] if count > 0 else []

    def read_all(self):
        """The whole file, for download. Just the header if there is none yet."""
        try:
            with self._lock:
                return self.path.read_bytes()
        except FileNotFoundError:
            pass
        except Exception:
            log.exception('Could not read the history file %s', self.path)
        return (HEADER + '\n').encode()

    @staticmethod
    def _parse(line):
        fields = line.split(',')
        if len(fields) != 6:
            return None
        try:
            index = int(fields[0])
            when = datetime.strptime(fields[1], FILE_TIME)
            temperature, blower, damper, target = (_number(field) for field in fields[2:])
        except ValueError:
            return None
        return {'i': index, 'x': when.strftime(GRAPH_TIME), 't': temperature, 'b': blower, 'd': damper, 's': target}

    def _prepare(self):
        """Make sure the file exists with its header and ends at a line boundary (a power
        loss can leave a half-written last line, which the next point must not join)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.path.write_text(HEADER + '\n')
            return
        with open(self.path, 'rb+') as history:
            history.seek(-1, os.SEEK_END)
            if history.read(1) != b'\n':
                history.write(b'\n')

    def _trim(self):
        """Keep the newest lines, about half the limit, replacing the file in one step so a
        power loss cannot leave it half rewritten."""
        with open(self.path, 'rb') as history:
            lines = history.read().splitlines(keepends=True)
        header, body = lines[0], lines[1:]
        kept, size = [], len(header)
        for line in reversed(body):
            if size + len(line) > self.max_bytes // 2:
                break
            kept.append(line)
            size += len(line)
        temporary = self.path.with_name(self.path.name + '.tmp')
        with open(temporary, 'wb') as trimmed:
            trimmed.write(header)
            trimmed.writelines(reversed(kept))
        os.replace(temporary, self.path)
