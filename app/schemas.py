"""Pydantic schemas for the Pyrenex Risk API.

TODO — Align LoanApplication with the feature_columns from your
pyrenex_risk_v2.json metadata (M1-B1 output).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoanApplication(BaseModel):
    """Input schema for /predict.

    TODO — Replace placeholder fields with the actual feature_columns
    from your pyrenex_risk_v2.json. Add Field(..., ge=…, le=…) bounds
    where your EDA showed reasonable ranges.
    """

    loan_amnt: float = Field(..., ge=500, le=40_000, description="Loan amount (USD)")
    term: str = Field(..., description="Loan term, e.g. '36 months' or '60 months'")
    int_rate: float = Field(..., ge=0, le=50, description="Interest rate (%)")
    installment: float = Field(..., ge=0, le=5_000, description="Monthly installment (USD)")
    grade: str = Field(..., description="Lending grade (A to G)")
    emp_length: str = Field(..., description="Employment length, e.g. '3 years'")
    home_ownership: str = Field(..., description="Housing status")
    annual_inc: float = Field(..., ge=0, le=10_000_000, description="Annual income (USD)")
    verification_status: str = Field(..., description="Income verification status")
    purpose: str = Field(..., description="Purpose of the loan")
    dti: float = Field(..., ge=0, le=100, description="Debt-to-income ratio")
    delinq_2yrs: int = Field(..., ge=0, le=50, description="Delinquencies in last 2 years")
    fico_range_low: int = Field(..., ge=300, le=850, description="Lower bound of FICO range")
    revol_util: float = Field(..., ge=0, le=150, description="Revolving utilization (%)")


class Prediction(BaseModel):
    """Output schema for /predict."""

    prediction: int = Field(..., description="0 = Fully Paid, 1 = Charged Off")
    probability: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    request_id: str


class HealthResponse(BaseModel):
    status: str
