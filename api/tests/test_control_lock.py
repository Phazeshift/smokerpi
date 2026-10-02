"""The control routes and the worker thread take turns at the hardware.

Flask serves each request on its own thread while the worker runs the PID on another. Without
a lock between them a button press could land between the worker deciding the PID is running
and the worker moving the hardware, so the worker undid it: "PID off" (or "blower off") left the
blower on with nothing supervising it."""
import threading

import pytest


class GatedController:
    """Stops at the start of set() until released: the worker has decided the PID is running
    but has not moved the hardware yet. It then asks for full output, blower on."""
    def __init__(self, real):
        self.real = real
        self.entered = threading.Event()
        self.release = threading.Event()

    def set(self, value):
        self.entered.set()
        self.release.wait(5)
        self.real.set(100)


class Recorder:
    def __init__(self):
        self.calls = []

    def set(self, value):
        self.calls.append(value)


def interleave(app, url, enabled):
    """Press a control while the worker is halfway through a step. Returns the response."""
    app.smoker.setAutomatic(True)
    gate = GatedController(app.smoker.pitController)
    app.smoker.pitController = gate
    worker = threading.Thread(target=app.worker.step)
    worker.start()
    try:
        assert gate.entered.wait(5), 'the worker never reached the hardware'
        responses = []
        client = app.test_client()
        press = threading.Thread(target=lambda: responses.append(client.post(url, json={'enabled': enabled})))
        press.start()
        # Without a lock the request finishes here, before the worker moves the hardware.
        press.join(0.3)
    finally:
        gate.release.set()
    worker.join(5)
    press.join(5)
    return responses[0]


class TestControlsDuringAWorkerStep:
    def test_turning_the_pid_off_leaves_the_blower_off(self, app):
        response = interleave(app, '/api/pid', False)
        assert response.status_code == 200
        assert app.smoker.automatic is False
        assert app.smoker.blower.state == 0

    def test_turning_the_blower_off_leaves_it_off(self, app):
        response = interleave(app, '/api/blower', False)
        assert response.status_code == 200
        assert app.smoker.blower.state == 0

    def test_closing_the_damper_leaves_it_closed(self, app):
        response = interleave(app, '/api/damper', False)
        assert response.status_code == 200
        assert app.smoker.damper.state == 0


class TestALoopThatHoldsTheLock:
    """A worker stuck in a hardware call holds the lock. A button press must not hang with it."""

    @pytest.fixture
    def held(self, app):
        app.smoker.lockTimeout = 0.1
        holder_has_it, done = threading.Event(), threading.Event()

        def hold():
            with app.smoker.lock:
                holder_has_it.set()
                done.wait(5)

        holder = threading.Thread(target=hold)
        holder.start()
        assert holder_has_it.wait(5)
        yield
        done.set()
        holder.join(5)

    @pytest.mark.parametrize('url', ['/api/pid', '/api/blower', '/api/damper'])
    def test_a_control_request_gives_up_with_a_503(self, app, client, held, url):
        response = client.post(url, json={'enabled': True})
        assert response.status_code == 503
        assert 'control loop' in response.get_json()['error']
        assert app.smoker.blower.state == 0
        assert app.smoker.automatic is False

    def test_a_config_change_gives_up_with_a_503(self, app, client, held):
        response = client.post('/api/config', json={
            'set_temperature': 130, 'damper_minimum': 600, 'damper_maximum': 2400})
        assert response.status_code == 503
        assert app.smoker.config['set_temperature'] != 130

    def test_reading_the_state_does_not_wait_for_the_lock(self, client, held):
        assert client.get('/api/state').status_code == 200

    def test_reading_the_graph_does_not_wait_for_the_lock(self, client, held):
        assert client.get('/api/graph').status_code == 200


class TestShutdown:
    def test_cleanup_waits_for_a_step_in_progress(self, app):
        order = []
        app.smoker.blower.cleanup = lambda: order.append('cleanup')
        app.smoker.setAutomatic(True)
        gate = GatedController(app.smoker.pitController)
        gate.real = type('Last', (), {'set': lambda self, value: order.append('step')})()
        app.smoker.pitController = gate
        worker = threading.Thread(target=app.worker.step)
        worker.start()
        assert gate.entered.wait(5)

        cleanup = threading.Thread(target=app.smoker.cleanup)
        cleanup.start()
        cleanup.join(0.3)
        gate.release.set()
        worker.join(5)
        cleanup.join(5)

        assert order == ['step', 'cleanup']

    def test_no_step_moves_the_hardware_after_cleanup(self, app):
        app.smoker.cleanup()
        app.smoker.setAutomatic(True)
        app.smoker.pitController = Recorder()
        app.worker.step()
        assert app.smoker.pitController.calls == []

    def test_cleanup_still_happens_if_the_loop_never_lets_go(self, app):
        app.smoker.lockTimeout = 0.1
        cleaned = []
        app.smoker.blower.cleanup = lambda: cleaned.append(True)
        app.smoker.lock.acquire()
        try:
            finished = threading.Thread(target=app.smoker.cleanup)
            finished.start()
            finished.join(5)
            assert not finished.is_alive()
        finally:
            app.smoker.lock.release()
        assert cleaned == [True]
