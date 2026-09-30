import json

import pytest

from smokerpi.config import Config


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """Every test in this file reads/writes config.json relative to cwd,
    so run each one in a throwaway directory rather than touching the
    real (gitignored) api/config.json."""
    monkeypatch.chdir(tmp_path)


class TestDefaultConfig:
    def test_defaults_are_not_mutated_by_test_scaling(self):
        config = Config(test=False)
        defaults = config.defaultConfig()
        assert defaults['worker_interval'] == 10
        assert defaults['graph_interval'] == 10


class TestApplyTestConfig:
    def test_scales_intervals_down_in_test_mode(self):
        config = Config(test=True)
        data = config.defaultConfig()
        config.applyTestConfig(data)
        assert data['worker_interval'] == 1.0
        assert data['graph_interval'] == 1.0

    def test_leaves_intervals_unchanged_outside_test_mode(self):
        config = Config(test=False)
        data = config.defaultConfig()
        config.applyTestConfig(data)
        assert data['worker_interval'] == 10
        assert data['graph_interval'] == 10


class TestLoadConfig:
    def test_returns_defaults_when_no_file_exists(self):
        config = Config(test=False)
        data = config.loadConfig()
        assert data == config.defaultConfig()

    def test_creates_config_file_on_first_load(self, tmp_path):
        config = Config(test=False)
        config.loadConfig()
        assert (tmp_path / 'config.json').exists()

    def test_merges_saved_overrides_onto_current_defaults(self, tmp_path):
        (tmp_path / 'config.json').write_text(json.dumps({'set_temperature': 225}))
        config = Config(test=False)
        data = config.loadConfig()
        assert data['set_temperature'] == 225
        # keys added to defaultConfig() since the file was last written are
        # still backfilled
        assert data['blower_minimum'] == config.defaultConfig()['blower_minimum']

    def test_applies_test_scaling_when_loading_in_test_mode(self):
        config = Config(test=True)
        data = config.loadConfig()
        assert data['worker_interval'] == 1.0


class TestSaveConfig:
    def test_round_trips_through_disk(self, tmp_path):
        config = Config(test=False)
        config.saveConfig({'set_temperature': 110, 'worker_interval': 10, 'graph_interval': 10})
        reloaded = json.loads((tmp_path / 'config.json').read_text())
        assert reloaded['set_temperature'] == 110

    def test_always_saves_the_real_intervals_not_test_scaled_ones(self, tmp_path):
        config = Config(test=False)
        config.saveConfig({'set_temperature': 110, 'worker_interval': 1, 'graph_interval': 1})
        reloaded = json.loads((tmp_path / 'config.json').read_text())
        assert reloaded['worker_interval'] == config.defaultConfig()['worker_interval']
        assert reloaded['graph_interval'] == config.defaultConfig()['graph_interval']

    def test_does_not_mutate_the_dict_it_is_given(self):
        # The API passes the live config, which must not change as a side effect of saving.
        config = Config(test=False)
        live = {'set_temperature': 110, 'worker_interval': 1, 'graph_interval': 2}
        config.saveConfig(live)
        assert live == {'set_temperature': 110, 'worker_interval': 1, 'graph_interval': 2}

    def test_keeps_intervals_that_were_hand_edited_in_the_file(self, tmp_path):
        (tmp_path / 'config.json').write_text(json.dumps({'worker_interval': 30, 'graph_interval': 20}))
        config = Config(test=True)
        # in test mode the live values are scaled down; saving must not write those back
        config.saveConfig({'set_temperature': 110, 'worker_interval': 3.0, 'graph_interval': 2.0})
        saved = json.loads((tmp_path / 'config.json').read_text())
        assert saved['worker_interval'] == 30
        assert saved['graph_interval'] == 20
        assert saved['set_temperature'] == 110
