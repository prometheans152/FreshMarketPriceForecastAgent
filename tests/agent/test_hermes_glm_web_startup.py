"""Local launch boundary and status contracts; no provider API calls."""
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aiot_price.agent.providers import resolve_active_profile


def test_coding_profile_is_only_enabled_in_explicit_hermes_local_demo(monkeypatch):
    monkeypatch.setenv('AIOT_AGENT_PROFILE', 'glm_zai_coding')
    monkeypatch.setenv('AIOT_GLM_API_KEY', 'offline-test-value')
    monkeypatch.setenv('AIOT_GLM_MODEL', 'glm-5.3-flash')
    monkeypatch.setenv('AIOT_AGENT_FRAMEWORK', 'hermes')
    monkeypatch.delenv('AIOT_LOCAL_HERMES_DEMO', raising=False)
    profile, reason = resolve_active_profile()
    assert reason == 'local_hermes_demo_required'
    monkeypatch.setenv('AIOT_LOCAL_HERMES_DEMO', '1')
    profile, reason = resolve_active_profile()
    assert reason == ''
    assert profile.base_url == 'https://api.z.ai/api/coding/paas/v4'
    assert profile.model == 'glm-5.3-flash'
    assert profile.max_retries == 0 and profile.cloud_fallback is False
    monkeypatch.setenv('AIOT_AGENT_FRAMEWORK', 'direct')
    assert resolve_active_profile()[1] == 'local_hermes_demo_required'


def test_general_glm_model_environment_does_not_change_qwen(monkeypatch):
    monkeypatch.setenv('AIOT_GLM_API_KEY', 'offline-test-value')
    monkeypatch.setenv('AIOT_GLM_MODEL', 'glm-5.3-flash')
    monkeypatch.setenv('AIOT_AGENT_PROFILE', 'glm_zai')
    profile, reason = resolve_active_profile()
    assert reason == '' and profile.model == 'glm-5.3-flash'
    assert profile.base_url == 'https://api.z.ai/api/paas/v4'
    monkeypatch.setenv('AIOT_AGENT_PROFILE', 'qwen_local')
    assert resolve_active_profile()[0].model == 'Qwen3.8-27B'


def test_status_is_safe_config_metadata_and_never_a_connection_claim(monkeypatch):
    api = importlib.import_module('aiot_price.api.app')
    monkeypatch.setenv('AIOT_AGENT_PROFILE', 'glm_zai_coding')
    monkeypatch.setenv('AIOT_LOCAL_HERMES_DEMO', '1')
    monkeypatch.setenv('AIOT_AGENT_FRAMEWORK', 'hermes')
    monkeypatch.setenv('AIOT_GLM_MODEL', 'glm-5.3-flash')
    monkeypatch.setenv('AIOT_GLM_API_KEY', 'unique-status-secret')
    api._rate_buckets.clear()
    with TestClient(api.app, client=('127.0.0.1', 50000), base_url='http://127.0.0.1:8765') as client:
        result = client.get('/agent/status')
    assert result.status_code == 200
    data = result.json()
    assert data['configured'] is True and data['local_demo'] is True
    assert data['runtime'] == 'hermes' and data['model'] == 'glm-5.3-flash'
    assert 'unique-status-secret' not in result.text
    assert 'connected' not in data


@pytest.mark.parametrize('client_host,origin', [('192.0.2.5', None), ('127.0.0.1', 'https://external.example'), ('127.0.0.1', 'http://localhost:9999'), ('127.0.0.1', 'http://[')])
def test_local_demo_rejects_remote_or_cross_origin_model_calls(monkeypatch, client_host, origin):
    api = importlib.import_module('aiot_price.api.app')
    monkeypatch.setenv('AIOT_LOCAL_HERMES_DEMO', '1')
    api._rate_buckets.clear()
    headers = {'Origin': origin} if origin else {}
    with TestClient(api.app, client=(client_host, 50000), base_url='http://127.0.0.1:8765') as client:
        result = client.post('/agent/query', json={'query': '查中義市場高麗菜行情'}, headers=headers)
    assert result.status_code == 403
    assert result.json()['error']['code'] == 'local_demo_only'


def test_isolated_runtime_cannot_reload_other_private_credentials(tmp_path, monkeypatch):
    api = importlib.import_module('aiot_price.api.app')
    envfile = tmp_path / '.env'
    envfile.write_text('AIOT_QWEN_BASE_URL=http://unwanted.example\nAIOT_OTHER_API_KEY=other-private-test-secret\n', encoding='utf-8')
    monkeypatch.setenv('AIOT_RUNTIME_ISOLATED', '1')
    monkeypatch.delenv('AIOT_OTHER_API_KEY', raising=False)
    assert api._load_private_env(envfile) == {}
    import os
    assert 'AIOT_OTHER_API_KEY' not in os.environ


def launch_module():
    return importlib.import_module('aiot_price.agent.local_web')


def test_launcher_uses_only_dedicated_key_and_isolates_other_credentials(tmp_path):
    key = tmp_path / 'project.env'
    key.write_text('AIOT_GLM_API_KEY=dedicated-test-key\nAIOT_GLM_MODEL=glm-5.3-flash\n', encoding='utf-8')
    env = launch_module().build_environment(key, tmp_path / 'home', {'PATH': 'existing-path', 'ANTHROPIC_API_KEY': 'borrowed-key', 'OPENAI_API_KEY': 'other-key', 'HTTPS_PROXY': 'http://proxy', 'GLM_BASE_URL': 'https://other.example', 'AIOT_QWEN_BASE_URL': 'http://other.example'})
    assert env['AIOT_GLM_API_KEY'] == 'dedicated-test-key'
    assert env['AIOT_AGENT_PROFILE'] == 'glm_zai_coding'
    assert env['AIOT_AGENT_FRAMEWORK'] == 'hermes'
    assert env['HOME'] == str(tmp_path / 'home')
    assert env['HERMES_HOME'] == env['AIOT_HERMES_HOME'] == env['HOME']
    assert all(name not in env for name in ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'HTTPS_PROXY', 'GLM_BASE_URL', 'AIOT_QWEN_BASE_URL'])


@pytest.mark.parametrize('extra', ['AIOT_GLM_API_KEY=duplicate\n', 'OPENAI_API_KEY=borrowed\n', 'not-an-assignment\n'])
def test_key_file_invalid_assignments_are_rejected_without_echo(tmp_path, extra):
    key = tmp_path / 'project.env'
    key.write_text('AIOT_GLM_API_KEY=secret-that-must-not-be-echoed\nAIOT_GLM_MODEL=glm-5.3-flash\n' + extra, encoding='utf-8')
    with pytest.raises(ValueError) as error:
        launch_module().build_environment(key, tmp_path / 'home', {})
    assert 'secret-that-must-not-be-echoed' not in str(error.value)


def test_general_api_launcher_selects_general_endpoint_profile(tmp_path):
    key = tmp_path / 'project.env'
    key.write_text('AIOT_GLM_API_KEY=offline-test-key\nAIOT_GLM_MODEL=glm-5.3-flash\n', encoding='utf-8')
    env = launch_module().build_environment(key, tmp_path / 'home', {}, local_demo=False)
    assert env['AIOT_AGENT_PROFILE'] == 'glm_zai'
    assert env['AIOT_LOCAL_HERMES_DEMO'] == '0'
