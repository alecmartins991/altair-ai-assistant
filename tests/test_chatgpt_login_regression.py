"""Offline regression tests for the post-browser OAuth failure."""
import json
import time
from unittest.mock import Mock, patch
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from altair.core.chatgpt_plan import (
    AUTH, ChatGPTSession, PlanError, _validate_identity, _stage, safe_error
)


@pytest.fixture
def identity():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    public.update(kid="test", alg="RS256", use="sig")
    claims = dict(iss=AUTH, aud="oaiapp_test", sub="test-subject",
                  exp=int(time.time())+300, iat=int(time.time()), nonce="test-nonce")
    response = Mock(status_code=200)
    response.json.return_value = {"keys": [public]}
    def issue(**changes):
        return jwt.encode(dict(claims, **changes), private, algorithm="RS256", headers={"kid":"test"})
    return issue, response


def test_valid_identity_from_official_jwks(identity):
    issue, response = identity
    with patch("altair.core.chatgpt_plan.requests.get", return_value=response) as get:
        claims = _validate_identity(issue(), "oaiapp_test", "test-nonce")
        assert claims["sub"] == "test-subject"
        assert get.call_args.args[0] == AUTH + "/.well-known/jwks.json"
        assert get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("changes", [{"aud":"different"}, {"iss":"https://example.invalid"},
    {"nonce":"different"}, {"exp":1}])
def test_reject_wrong_identity(identity, changes):
    issue, response = identity
    with patch("altair.core.chatgpt_plan.requests.get", return_value=response):
        with pytest.raises(PlanError):
            _validate_identity(issue(**changes), "oaiapp_test", "test-nonce")


def test_stage_never_displays_raw_exception():
    def fail():
        raise RuntimeError("SECRET_BEARER_TOKEN")
    with pytest.raises(PlanError) as error:
        _stage("Validação da identidade", fail)
    assert "Validação da identidade" in str(error.value)
    assert "SECRET_BEARER_TOKEN" not in str(error.value)


def test_session_readback_failure(tmp_path):
    session = ChatGPTSession(tmp_path)
    with patch.object(session, "load", return_value={}):
        with pytest.raises(PlanError, match="reler"):
            session.save({"client_id":"test"})


def test_catalog_bad_format(tmp_path):
    session = ChatGPTSession(tmp_path)
    response = Mock(status_code=200)
    response.json.return_value = {"data":[]}
    with patch.object(session, "access_token", return_value="fake"), patch(
        "altair.core.chatgpt_plan.requests.get", return_value=response):
        with pytest.raises(PlanError, match="Catálogo"):
            session.models()
