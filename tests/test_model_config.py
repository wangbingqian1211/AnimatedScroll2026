from backend import config


def test_dashscope_uses_user_supplied_endpoint_for_text_and_vision(monkeypatch):
    monkeypatch.delenv('MODEL_PROVIDER',raising=False)
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake-dashscope-key')
    for key in ('DASHSCOPE_BASE_URL','DASHSCOPE_MODEL','DASHSCOPE_VISION_MODEL'):
        monkeypatch.delenv(key,raising=False)
    for kind in ('text','vision'):
        settings=config.model_settings(kind)
        assert settings.provider=='dashscope'
        assert settings.api_key=='fake-dashscope-key'
        assert settings.base_url=='https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1'
        assert settings.model=='deepseek-v4.1-flash'
        assert settings.api_key not in repr(settings)


def test_dashscope_supports_separate_vision_model(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER','dashscope')
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake')
    monkeypatch.setenv('DASHSCOPE_MODEL','text-model')
    monkeypatch.setenv('DASHSCOPE_VISION_MODEL','vision-model')
    assert config.model_settings().model=='text-model'
    assert config.model_settings('vision').model=='vision-model'


def test_explicit_provider_never_silently_uses_another_key(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER','dashscope')
    monkeypatch.delenv('DASHSCOPE_API_KEY',raising=False)
    import pytest
    with pytest.raises(ValueError,match='DASHSCOPE_API_KEY'):
        config.model_settings()
    assert not config.model_settings(require_key=False).api_key


def test_model_status_contains_no_key(client,monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER','dashscope')
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake-private-key-never-echo')
    r=client.get('/api/status')
    assert r.status_code==200
    assert r.json()['provider']=='dashscope'
    assert r.json()['apiConfigured']
    assert 'fake-private-key-never-echo' not in r.text


def test_legacy_provider_remains_explicitly_available(monkeypatch):
    monkeypatch.setenv('MODEL_PROVIDER','aihubmix')
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake-dashscope-key')
    monkeypatch.setenv('AIHUBMIX_API_KEY','fake-legacy-key')
    assert config.model_settings().api_key=='fake-legacy-key'
