import logging

from smokerpi import create_app, readVersion
from smokerpi.config import Config


def test_reads_the_release_tag_update_sh_wrote(tmp_path):
    version = tmp_path / 'VERSION'
    version.write_text('v1.2.3\n')
    assert readVersion(str(version)) == 'v1.2.3'


def test_a_checkout_without_a_version_file_is_unknown(tmp_path):
    assert readVersion(str(tmp_path / 'VERSION')) == 'unknown'


def test_an_empty_version_file_is_unknown(tmp_path):
    (tmp_path / 'VERSION').write_text('\n')
    assert readVersion(str(tmp_path / 'VERSION')) == 'unknown'


def test_the_startup_log_line_names_the_version(caplog):
    with caplog.at_level(logging.INFO):
        create_app(test_config={'config': Config(test=True).defaultConfig(), 'start_worker': False})
    assert any(r.getMessage().startswith('### NEW STARTUP Version ') and '0.1' not in r.getMessage()
               for r in caplog.records)
