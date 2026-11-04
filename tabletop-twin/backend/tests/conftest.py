"""Two things every test run needs: an import path, and an emptied environment.

The path lets a test import the fake gateways beside it however pytest was invoked.
An in-process test that inherits a real credential from the developer's environment
would make live requests to whoever issued it and assert on whatever came back — so
the credential variables are cleared around every test, and a test that wants an
endpoint has to say which one and stand it up itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CREDENTIAL_VARS = (
    "META_MODEL_BASE_URL", "META_MODEL_API_KEY", "META_MODEL_NAME", "MODEL_API_KEY",
    "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
    "OPENAI_COMPAT_BASE_URL", "OPENAI_COMPAT_API_KEY", "OPENAI_COMPAT_MODEL",
    "PAYPAL_CLIENT_ID", "PAYPAL_SECRET", "PAYPAL_ENVIRONMENT",
)


@pytest.fixture(autouse=True)
def no_live_credentials(monkeypatch):
    for name in CREDENTIAL_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch
