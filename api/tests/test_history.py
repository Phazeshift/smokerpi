"""Graph points are kept in a CSV file so the graph survives a restart and the whole session
can be downloaded. It lives on the Pi's SD card (and the Pi runs from a power bank, so it can
lose power mid-write), so it is size-limited and tolerant of damage, and a disk problem must
never stop the control loop."""
import base64
import csv
import json
from datetime import datetime

import pytest

from smokerpi import create_app
from smokerpi.config import Config
from smokerpi.history import History

HEADER = 'time,temperature,blower,damper,target'


@pytest.fixture
def path(tmp_path):
    return tmp_path / 'data' / 'history.csv'


def when(n):
    return datetime(2026, 10, 1, 12, 0, n)


def fill(history, count, start=0):
    for n in range(start, start + count):
        history.append(datetime(2026, 10, 1, 12, (n // 60) % 60, n % 60), 100 + n, 0, 99, 105)


class TestFile:
    def test_the_first_point_creates_the_directory_and_the_header(self, path):
        History(path).append(when(1), 26.75, 0, 99, 105)
        lines = path.read_text().splitlines()
        assert lines == [HEADER, '2026-10-01 12:00:01,26.75,0,99,105']

    def test_the_header_is_written_once_across_restarts(self, path):
        History(path).append(when(1), 26.75, 0, 99, 105)
        History(path).append(when(2), 27.0, 100, 100, 105)
        assert path.read_text().splitlines().count(HEADER) == 1
        assert len(path.read_text().splitlines()) == 3

    def test_the_file_is_a_valid_csv(self, path):
        history = History(path)
        fill(history, 5)
        rows = list(csv.DictReader(path.open()))
        assert len(rows) == 5 and rows[0]['temperature'] == '100'

    def test_a_missing_file_downloads_as_just_the_header(self, path):
        assert History(path).read_all().decode().strip() == HEADER

    def test_read_all_returns_the_file(self, path):
        history = History(path)
        fill(history, 3)
        assert history.read_all() == path.read_bytes()


class TestRecent:
    def test_returns_graph_points_in_order_with_sequential_indexes(self, path):
        history = History(path)
        history.append(when(1), 26.75, 0, 99, 105)
        history.append(when(2), 27.0, 100, 52.33, 105)

        points = History(path).recent(10)

        assert points == [
            {'i': 0, 'x': '01/10/2026 12:00:01', 't': 26.75, 'b': 0, 'd': 99, 's': 105},
            {'i': 1, 'x': '01/10/2026 12:00:02', 't': 27.0, 'b': 100, 'd': 52.33, 's': 105},
        ]

    def test_returns_only_the_newest_ones(self, path):
        history = History(path)
        fill(history, 50)
        points = history.recent(10)
        assert [p['t'] for p in points] == [140 + n for n in range(10)]
        assert [p['i'] for p in points] == list(range(10))

    def test_no_file_means_no_points(self, path):
        assert History(path).recent(10) == []

    def test_damaged_lines_are_skipped(self, path):
        history = History(path)
        fill(history, 3)
        with path.open('a') as f:
            f.write('garbage\n2026-10-01 12:30:00,notanumber,0,99,105\n,,,,\n')
        fill(history, 2, start=100)
        points = History(path).recent(100)
        assert [p['t'] for p in points] == [100, 101, 102, 200, 201]

    def test_a_line_cut_off_by_a_power_loss_does_not_corrupt_the_next_one(self, path):
        history = History(path)
        fill(history, 2)
        with path.open('a') as f:
            f.write('2026-10-01 12:30:00,50.')          # power lost mid-write, no newline
        History(path).append(when(59), 77.0, 0, 99, 105)
        points = History(path).recent(100)
        assert [p['t'] for p in points] == [100, 101, 77.0]


class TestSizeLimit:
    def test_the_file_is_trimmed_to_the_newest_points_when_it_passes_the_limit(self, path):
        history = History(path, max_bytes=2000)
        fill(history, 300)
        assert path.stat().st_size <= 2000
        points = history.recent(1000)
        assert points[-1]['t'] == 399                    # the newest is kept
        assert 0 < len(points) < 300
        assert path.read_text().splitlines()[0] == HEADER

    def test_the_kept_points_are_contiguous_and_the_newest(self, path):
        history = History(path, max_bytes=2000)
        fill(history, 300)
        temps = [p['t'] for p in history.recent(1000)]
        assert temps == list(range(int(temps[0]), 400))

    def test_a_small_file_is_never_trimmed(self, path):
        history = History(path, max_bytes=1000000)
        fill(history, 100)
        assert len(history.recent(1000)) == 100

    def test_appending_still_works_after_a_trim(self, path):
        history = History(path, max_bytes=2000)
        fill(history, 300)
        history.append(when(59), 555.0, 0, 99, 105)
        assert history.recent(1)[0]['t'] == 555.0


class TestFailures:
    def test_a_write_error_is_logged_not_raised(self, tmp_path, caplog):
        blocked = tmp_path / 'blocked'
        blocked.write_text('a file where the directory should be')
        history = History(blocked / 'history.csv')
        history.append(when(1), 26.75, 0, 99, 105)        # must not raise
        assert 'history' in caplog.text.lower()

    def test_a_read_error_gives_no_points(self, tmp_path):
        assert History(tmp_path).recent(10) == []         # the path is a directory


def make_app(**overrides):
    config = dict(Config(test=True).defaultConfig(), **overrides)
    return create_app(test_config={'config': config, 'start_worker': False})


@pytest.fixture
def app():
    application = make_app()
    yield application
    application.smokerpi_running = False


class TestInTheApp:
    def test_each_graph_point_is_written_to_data_history_csv(self, app, tmp_path):
        app.smokerpi_workerStep()
        rows = list(csv.DictReader((tmp_path / 'data' / 'history.csv').open()))
        assert len(rows) == 1
        assert float(rows[0]['target']) == 105

    def test_the_graph_survives_a_restart(self, app):
        for _ in range(3):
            app.smokerpi_graphLast = 0                    # let every step record a point
            app.smokerpi_workerStep()
        before = json.loads(app.test_client().get('/api/graph').data)
        app.smokerpi_running = False

        restarted = make_app()
        try:
            after = json.loads(restarted.test_client().get('/api/graph').data)
            assert [p['t'] for p in after] == [p['t'] for p in before]
            assert len(after) == 3
            # and carries on numbering from there
            restarted.smokerpi_graphLast = 0
            restarted.smokerpi_workerStep()
            again = json.loads(restarted.test_client().get('/api/graph').data)
            assert [p['i'] for p in again] == [0, 1, 2, 3]
        finally:
            restarted.smokerpi_running = False

    def test_only_the_most_recent_two_thousand_points_are_restored(self, app):
        fill(app.smokerpi_history, 2500)
        app.smokerpi_running = False
        restarted = make_app()
        try:
            graph = json.loads(restarted.test_client().get('/api/graph').data)
            assert len(graph) == 2000
            assert graph[-1]['t'] == 100 + 2499
        finally:
            restarted.smokerpi_running = False

    def test_a_history_failure_does_not_fail_the_step_or_lose_the_graph_point(self, app, tmp_path, caplog):
        app.smokerpi_blower.on()
        blocker = tmp_path / 'blocker'
        blocker.write_text('a file where a directory is needed')
        app.smokerpi_history = History(blocker / 'x' / 'history.csv')
        caplog.clear()

        app.smokerpi_workerStep()

        assert len(app.smokerpi_graphData) == 1
        assert app.smokerpi_blower.state == 100          # no fail-safe: the control loop was fine
        assert [r for r in caplog.records if 'Worker step failed' in r.getMessage()] == []

    def test_the_size_limit_comes_from_config(self):
        application = make_app(history_max_mb=0.5)
        try:
            assert application.smokerpi_history.max_bytes == 524288
        finally:
            application.smokerpi_running = False

    def test_the_default_limit_is_five_megabytes(self, app):
        assert Config(test=True).defaultConfig()['history_max_mb'] == 5
        assert app.smokerpi_history.max_bytes == 5 * 1024 * 1024


class TestDownload:
    def test_serves_the_csv_as_an_attachment(self, app):
        app.smokerpi_workerStep()
        response = app.test_client().get('/api/history.csv')
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert 'attachment' in response.headers['Content-Disposition']
        assert '.csv' in response.headers['Content-Disposition']
        lines = response.data.decode().splitlines()
        assert lines[0] == HEADER and len(lines) == 2

    def test_with_no_points_yet_it_is_just_the_header(self, app):
        response = app.test_client().get('/api/history.csv')
        assert response.data.decode().strip() == HEADER

    def test_it_needs_the_password_when_one_is_set(self):
        application = make_app(password='pw')
        try:
            client = application.test_client()
            assert client.get('/api/history.csv').status_code == 401
            token = base64.b64encode(b'x:pw').decode()
            assert client.get('/api/history.csv', headers={'Authorization': 'Basic ' + token}).status_code == 200
        finally:
            application.smokerpi_running = False
