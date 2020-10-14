import pytest
from .utils import reset_config
from fastapi_jwt_auth import AuthJWT
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseSettings, ValidationError
from typing import Sequence
from datetime import timedelta

@pytest.fixture(scope='function')
def client():
    app = FastAPI()

    @app.get('/protected')
    def protected(Authorize: AuthJWT = Depends()):
        Authorize.jwt_required()

    client = TestClient(app)
    return client

def test_default_config():
    reset_config()
    assert AuthJWT._token is None
    assert AuthJWT._secret_key is None
    assert AuthJWT._algorithm == 'HS256'
    assert AuthJWT._decode_leeway == 0
    assert AuthJWT._encode_issuer is None
    assert AuthJWT._decode_issuer is None
    assert AuthJWT._decode_audience is None
    assert AuthJWT._blacklist_enabled is None
    assert AuthJWT._blacklist_token_checks == []
    assert AuthJWT._token_in_blacklist_callback is None

    assert AuthJWT._access_token_expires.__class__ == timedelta
    assert int(AuthJWT._access_token_expires.total_seconds()) == 900

    assert AuthJWT._refresh_token_expires.__class__ == timedelta
    assert int(AuthJWT._refresh_token_expires.total_seconds()) == 2592000

def test_secret_key_not_exist(client,Authorize):
    reset_config()

    with pytest.raises(RuntimeError,match=r"AUTHJWT_SECRET_KEY"):
        Authorize.create_access_token(identity='test')

    with pytest.raises(RuntimeError,match=r"AUTHJWT_SECRET_KEY"):
        client.get('/protected',headers={"Authorization":"Bearer test"})

def test_blacklist_enabled_without_callback(client,Authorize):
    # set authjwt_secret_key for create token
    class SettingsOne(BaseSettings):
        authjwt_secret_key: str = "secret-key"
        # AuthJWT blacklist won't trigger if value not str 'true'
        authjwt_blacklist_enabled: str = "false"

    @AuthJWT.load_config
    def get_settings_one():
        return SettingsOne()

    token = Authorize.create_access_token(identity='test')

    response = client.get('/protected',headers={"Authorization": f"Bearer {token.decode('utf-8')}"})
    assert response.status_code == 200

    class SettingsTwo(BaseSettings):
        authjwt_secret_key: str = "secret-key"
        authjwt_blacklist_enabled: str = "true"
        authjwt_blacklist_token_checks: list = ["access"]

    @AuthJWT.load_config
    def get_settings_two():
        return SettingsTwo()

    with pytest.raises(RuntimeError,match=r"@AuthJWT.token_in_blacklist_loader"):
        response = client.get('/protected',headers={"Authorization": f"Bearer {token.decode('utf-8')}"})

def test_load_env_from_outside():
    # correct data
    class Settings(BaseSettings):
        authjwt_secret_key: str = "testing"
        authjwt_algorithm: str = "HS256"
        authjwt_decode_leeway: timedelta = timedelta(seconds=8)
        authjwt_encode_issuer: str = "urn:foo"
        authjwt_decode_issuer: str = "urn:foo"
        authjwt_decode_audience: str = 'urn:foo'
        authjwt_blacklist_token_checks: Sequence = ['access','refresh']
        authjwt_blacklist_enabled: str = "false"
        authjwt_access_token_expires: timedelta = timedelta(minutes=2)
        authjwt_refresh_token_expires: timedelta = timedelta(days=5)

    @AuthJWT.load_config
    def get_valid_settings():
        return Settings()

    assert AuthJWT._secret_key == "testing"
    assert AuthJWT._algorithm == "HS256"
    assert AuthJWT._decode_leeway == timedelta(seconds=8)
    assert AuthJWT._encode_issuer == "urn:foo"
    assert AuthJWT._decode_issuer == "urn:foo"
    assert AuthJWT._decode_audience == 'urn:foo'
    assert AuthJWT._blacklist_token_checks == ['access','refresh']
    assert AuthJWT._blacklist_enabled == "false"
    assert AuthJWT._access_token_expires == timedelta(minutes=2)
    assert AuthJWT._refresh_token_expires == timedelta(days=5)

    with pytest.raises(TypeError,match=r"Config"):
        @AuthJWT.load_config
        def invalid_data():
            return "test"

    with pytest.raises(ValidationError,match=r"AUTHJWT_SECRET_KEY"):
        @AuthJWT.load_config
        def get_invalid_secret_key():
            return [("authjwt_secret_key",123)]

    with pytest.raises(ValidationError,match=r"AUTHJWT_ALGORITHM"):
        @AuthJWT.load_config
        def get_invalid_algorithm():
            return [("authjwt_algorithm",123)]

    with pytest.raises(ValidationError,match=r"AUTHJWT_DECODE_LEEWAY"):
        @AuthJWT.load_config
        def get_invalid_decode_leeway():
            return [("authjwt_decode_leeway","test")]

    with pytest.raises(ValidationError,match=r"AUTHJWT_ENCODE_ISSUER"):
        @AuthJWT.load_config
        def get_invalid_encode_issuer():
            return [("authjwt_encode_issuer",1)]

    with pytest.raises(ValidationError,match=r"AUTHJWT_DECODE_ISSUER"):
        @AuthJWT.load_config
        def get_invalid_decode_issuer():
            return [("authjwt_decode_issuer",1)]

    with pytest.raises(ValidationError,match=r"AUTHJWT_DECODE_AUDIENCE"):
        @AuthJWT.load_config
        def get_invalid_decode_audience():
            return [("authjwt_decode_audience",1)]

    with pytest.raises(ValidationError,match=r"AUTHJWT_BLACKLIST_ENABLED"):
        @AuthJWT.load_config
        def get_invalid_blacklist():
            return [("authjwt_blacklist_enabled","test")]

    with pytest.raises(ValidationError,match=r"AUTHJWT_BLACKLIST_TOKEN_CHECKS"):
        @AuthJWT.load_config
        def get_invalid_blacklist_token_checks():
            return [("authjwt_blacklist_token_checks","string")]

    with pytest.raises(ValidationError,match=r"AUTHJWT_ACCESS_TOKEN_EXPIRES"):
        @AuthJWT.load_config
        def get_invalid_access_token():
            return [("authjwt_access_token_expires","lol")]

    with pytest.raises(ValidationError,match=r"AUTHJWT_REFRESH_TOKEN_EXPIRES"):
        @AuthJWT.load_config
        def get_invalid_refresh_token():
            return [("authjwt_refresh_token_expires","lol")]

    reset_config()
