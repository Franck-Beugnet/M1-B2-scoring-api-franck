"""Shared fixtures for M1-B2 tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient with lifespan triggered (model loaded)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_payload() -> dict:
    """Valid loan application payload.
    """
    return {
        "loan_amnt": 10000,
        "term": "36 months",
        "int_rate": 12.5,
        "installment": 334.21,
        "grade": "B",
        "emp_length": "3 years",
        "home_ownership": "MORTGAGE",
        "annual_inc": 60000,
        "verification_status": "Verified",
        "purpose": "debt_consolidation",
        "dti": 13.1,
        "delinq_2yrs": 0,
        "fico_range_low": 700,
        "revol_util": 45.2,
    }
