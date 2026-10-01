"""Tests must not write into the real api/ directory (its config.json is a developer's
local, gitignored settings file, and log/ is the real app log)."""
import json
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent


def snapshot(name):
    path = API_DIR / name
    return path.read_bytes() if path.exists() else None


def test_the_working_directory_is_not_the_api_directory(client):
    assert Path.cwd().resolve() != API_DIR


def test_posting_config_does_not_touch_the_real_config_file(client):
    before = snapshot('config.json')
    current = json.loads(before)['set_temperature'] if before else 0

    response = client.post('/api/config', json={
        'set_temperature': current + 7,
        'damper_minimum': 500,
        'damper_maximum': 2500,
    })

    assert response.status_code == 200
    assert snapshot('config.json') == before

