"""Runs the real update.sh against a fake release, with a fake curl, in a scratch install.

update.sh runs on a live Pi and replaces itself while bash is still reading it, so these
tests cover the failure modes that matter: the swap itself, the Python version guard, and
being replaced by a script of a different length."""
import os
import shutil
import stat
import subprocess
import sys
import tarfile

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UPDATE_SH = os.path.join(REPO, 'update.sh')

# On Windows these need Git Bash; set SMOKERPI_SCRIPT_TESTS=1 to run them there.
pytestmark = pytest.mark.skipif(
    (sys.platform.startswith('win') and not os.environ.get('SMOKERPI_SCRIPT_TESTS'))
    or shutil.which('bash') is None,
    reason='needs bash and POSIX tools (runs in CI on Linux)')

FAKE_CURL = """#!/bin/bash
# stand-in for the two curl calls update.sh makes
for a in "$@"; do case "$a" in *url_effective*) echo "https://github.com/Phazeshift/smokerpi/releases/tag/v9.9.9"; exit 0;; esac; done
while [ $# -gt 0 ]; do if [ "$1" = "-o" ]; then cp "$FAKE_BUNDLE" "$2"; exit 0; fi; shift; done
exit 1
"""


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='\n') as f:
        f.write(text)
    if mode:
        os.chmod(path, mode)


def make_bundle(tmp_path, update_sh_text=None, requirements='Flask==3.1.3\n'):
    root = tmp_path / 'rel' / 'smokerpi'
    write(str(root / 'VERSION'), 'v9.9.9\n')
    write(str(root / 'build' / 'index.html'), 'NEW BUILD')
    write(str(root / 'api' / 'smokerpi' / '__init__.py'), 'new code')
    write(str(root / 'api' / 'runserver.py'), 'new runserver')
    write(str(root / 'api' / 'requirements.txt'), requirements)
    write(str(root / 'api' / '.flaskenv'), 'FLASK_APP=smokerpi\n')
    for name in ('runserver.sh', 'install.sh', 'smokerpiboot'):
        write(str(root / name), '#!/bin/sh\n')
    with open(UPDATE_SH, newline='') as f:
        text = f.read()
    write(str(root / 'update.sh'), update_sh_text if update_sh_text is not None else text)
    bundle = tmp_path / 'bundle.tgz'
    with tarfile.open(str(bundle), 'w:gz') as tf:
        tf.add(str(root), arcname='smokerpi')
    return str(bundle)


def make_install(tmp_path, python_ok=True, requirements='Flask==3.1.3\n', script=UPDATE_SH):
    inst = tmp_path / 'install'
    write(str(inst / 'VERSION'), 'v0.3.0\n')
    write(str(inst / 'build' / 'index.html'), 'OLD BUILD')
    write(str(inst / 'api' / 'smokerpi' / '__init__.py'), 'old code')
    write(str(inst / 'api' / 'runserver.py'), 'old runserver')
    write(str(inst / 'api' / 'requirements.txt'), requirements)
    write(str(inst / 'api' / '.flaskenv'), 'FLASK_APP=smokerpi\nFLASK_ENV=development\n')
    write(str(inst / 'api' / 'config.json'), '{"damper_maximum": 1500}')
    for name in ('runserver.sh', 'install.sh', 'smokerpiboot'):
        write(str(inst / name), '#!/bin/sh\n')
    shutil.copy(script, str(inst / 'update.sh'))
    exe = stat.S_IRWXU
    write(str(inst / 'api' / 'venv' / 'bin' / 'pip'), '#!/bin/bash\necho "[fake pip] $*"\n', exe)
    write(str(inst / 'api' / 'venv' / 'bin' / 'python'),
          '#!/bin/bash\nif [ "$1" = "-c" ]; then exit %d; fi\necho "Python %s"\n'
          % (0 if python_ok else 1, '3.11.2' if python_ok else '3.7.3'), exe)
    os.chmod(str(inst / 'update.sh'), exe)
    return inst


def run_update(tmp_path, inst, bundle, *args):
    bin_dir = tmp_path / 'bin'
    write(str(bin_dir / 'curl'), FAKE_CURL, stat.S_IRWXU)
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'], FAKE_BUNDLE=bundle)
    return subprocess.run(['bash', './update.sh'] + list(args), cwd=str(inst), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)


def read(path):
    with open(str(path)) as f:
        return f.read()


class TestNormalUpdate:
    def test_installs_the_release_and_keeps_local_state(self, tmp_path):
        inst = make_install(tmp_path)
        result = run_update(tmp_path, inst, make_bundle(tmp_path))

        assert result.returncode == 0, result.stdout
        assert read(inst / 'VERSION').strip() == 'v9.9.9'
        assert read(inst / 'build' / 'index.html') == 'NEW BUILD'
        assert read(inst / 'api' / 'smokerpi' / '__init__.py') == 'new code'
        assert read(inst / 'api' / 'config.json') == '{"damper_maximum": 1500}'
        assert 'FLASK_ENV' not in read(inst / 'api' / '.flaskenv')

    def test_keeps_the_session_history_and_the_log(self, tmp_path):
        # api/data/history.csv is the graph history (smokerpi/history.py): an update that
        # replaced only build/ and api/smokerpi must leave it, and the log, alone.
        inst = make_install(tmp_path)
        write(str(inst / 'api' / 'data' / 'history.csv'), 'time,temperature,blower,damper,target')
        write(str(inst / 'api' / 'log' / 'app.log'), 'a log line')

        result = run_update(tmp_path, inst, make_bundle(tmp_path))

        assert result.returncode == 0, result.stdout
        assert read(inst / 'api' / 'data' / 'history.csv') == 'time,temperature,blower,damper,target'
        assert read(inst / 'api' / 'log' / 'app.log') == 'a log line'

    def test_does_nothing_when_already_up_to_date(self, tmp_path):
        inst = make_install(tmp_path)
        write(str(inst / 'VERSION'), 'v9.9.9\n')
        result = run_update(tmp_path, inst, make_bundle(tmp_path))
        assert result.returncode == 0
        assert 'Already up to date' in result.stdout
        assert read(inst / 'build' / 'index.html') == 'OLD BUILD'

    def test_leaves_no_temporary_files_behind(self, tmp_path):
        inst = make_install(tmp_path)
        run_update(tmp_path, inst, make_bundle(tmp_path))
        assert not (inst / 'update.sh.new').exists()


class TestPythonGuard:
    def test_old_python_with_changed_requirements_aborts_and_changes_nothing(self, tmp_path):
        inst = make_install(tmp_path, python_ok=False, requirements='Flask==2.0.3\n')
        result = run_update(tmp_path, inst, make_bundle(tmp_path))

        assert result.returncode != 0
        assert 'Python 3.9' in result.stdout
        assert read(inst / 'VERSION').strip() == 'v0.3.0'
        assert read(inst / 'build' / 'index.html') == 'OLD BUILD'
        assert read(inst / 'api' / 'smokerpi' / '__init__.py') == 'old code'
        assert 'FLASK_ENV' in read(inst / 'api' / '.flaskenv')

    def test_new_python_with_changed_requirements_installs_them(self, tmp_path):
        inst = make_install(tmp_path, python_ok=True, requirements='Flask==2.0.3\n')
        result = run_update(tmp_path, inst, make_bundle(tmp_path))
        assert result.returncode == 0, result.stdout
        assert '[fake pip] install -r' in result.stdout

    def test_old_python_is_fine_when_requirements_are_unchanged(self, tmp_path):
        # e.g. a Pi still on Python 3.7 receiving a release that changes no packages
        inst = make_install(tmp_path, python_ok=False)
        result = run_update(tmp_path, inst, make_bundle(tmp_path))
        assert result.returncode == 0, result.stdout
        assert read(inst / 'VERSION').strip() == 'v9.9.9'


class TestReplacingItself:
    """update.sh overwrites itself with the new release's copy while bash is still running
    it. The running script is always the *previous* release's, so the new one can be any
    length; that used to make bash resume reading at a stale offset and fail with
    'syntax error near unexpected token' after the update had already been applied."""

    # Whether a stale read offset breaks bash depends on where it lands, so sweep many
    # replacement lengths rather than trusting one to hit a bad spot.
    @pytest.mark.parametrize('extra_lines', [1, 2, 3, 5, 7, 11, 13, 21, 34, 40, 63, 100, -1])
    def test_a_replacement_of_a_different_length_causes_no_error(self, tmp_path, extra_lines):
        with open(UPDATE_SH, newline='') as f:
            text = f.read()
        lines = text.split('\n')
        if extra_lines > 0:
            lines[1:1] = ['# padding line %d to move every offset in the file' % n for n in range(extra_lines)]
        else:  # shorter: drop the comments
            lines = [lines[0]] + [l for l in lines[1:] if not l.lstrip().startswith('#')]
        replacement = '\n'.join(lines)
        assert len(replacement) != len(text)

        inst = make_install(tmp_path)
        result = run_update(tmp_path, inst, make_bundle(tmp_path, update_sh_text=replacement))

        assert 'syntax error' not in result.stdout, result.stdout
        assert result.returncode == 0, result.stdout
        assert read(inst / 'VERSION').strip() == 'v9.9.9'
        assert read(inst / 'update.sh') == replacement


FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestUpdatingFromAnEarlierRelease:
    """The update.sh doing the work is always the *previous* release's copy, and v0.3.0 and
    v0.3.1 shipped one that re-reads itself at a stale offset after replacing itself in
    place. Frozen copies of those are kept in tests/fixtures. Updating from them may end
    with a cosmetic parse error, because bash resumes in the middle of the new script, but
    whatever fragment it executes there must not undo or damage the update. That depends
    on the exact bytes of the new script, so any edit to update.sh has to keep this true."""

    @pytest.mark.parametrize('old_script', ['update_v0.3.0.sh', 'update_v0.3.1.sh'])
    def test_the_update_is_intact_whatever_the_old_script_does_at_the_end(self, tmp_path, old_script):
        inst = make_install(tmp_path, script=os.path.join(FIXTURES, old_script))
        run_update(tmp_path, inst, make_bundle(tmp_path))

        # deliberately not asserting the exit status: it may be non-zero (see above)
        assert read(inst / 'VERSION').strip() == 'v9.9.9'
        assert read(inst / 'build' / 'index.html') == 'NEW BUILD'
        assert read(inst / 'api' / 'smokerpi' / '__init__.py') == 'new code'
        assert read(inst / 'api' / 'runserver.py') == 'new runserver'
        assert 'FLASK_ENV' not in read(inst / 'api' / '.flaskenv')
        assert read(inst / 'api' / 'config.json') == '{"damper_maximum": 1500}'
        assert read(inst / 'update.sh') == read(UPDATE_SH)
        assert not (inst / 'update.sh.new').exists()
