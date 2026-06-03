"""Pyrenex Risk API — entry point.
"""
from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.middleware import LoggingMiddleware
from app.schemas import HealthResponse, LoanApplication, Prediction

# --- Loguru configuration ---------------------------------------------------

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="INFO", colorize=True)
logger.add(
    LOGS_DIR / "api.log",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
    serialize=True,
    enqueue=True,
    level="INFO",
)


# --- Lifespan ---------------------------------------------------------------

MODELS_DIR = Path(__file__).parent.parent / "models"
MODEL_PATH = MODELS_DIR / "pyrenex_risk_v2.joblib"
META_PATH = MODELS_DIR / "pyrenex_risk_v2.json"

# CORS must use explicit origins when credentials are enabled.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Pre-wired for M5: visible as Bearer auth in Swagger UI.
bearer_scheme = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model + metadata at startup, release at shutdown."""
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model file not found at {MODEL_PATH}")
    if not META_PATH.exists():
        raise RuntimeError(f"Metadata file not found at {META_PATH}")

    app.state.model = joblib.load(MODEL_PATH)
    app.state.metadata = json.loads(META_PATH.read_text(encoding="utf-8"))
    logger.info(
        "Model loaded: {name} {version}",
        name=app.state.metadata["model_name"],
        version=app.state.metadata["model_version"],
    )
    yield
    app.state.model = None
    logger.info("Model released")


app = FastAPI(
    title="Pyrenex Risk API",
    version="0.1.0",
    description="API serving the Pyrenex Crédit credit-risk scoring model.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(LoggingMiddleware)


# --- Routes -----------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check."""
    if not hasattr(app.state, "model") or app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return HealthResponse(status="ok")


@app.get("/info")
async def info() -> dict:
    """Return loaded model metadata.
    Return at least: api_version, model_name, model_version, model_created_at, metrics_holdout.
    """
    if not hasattr(app.state, "metadata") or app.state.metadata is None:
        raise HTTPException(status_code=503, detail="Metadata not loaded")

    metadata = app.state.metadata
    return {
        "api_version": app.version,
        "model_name": metadata.get("model_name"),
        "model_version": metadata.get("model_version"),
        "created_at": metadata.get("created_at"),
        "sklearn_version": metadata.get("sklearn_version"),
        "dataset_sha256": metadata.get("dataset_sha256"),
        "metrics_holdout": metadata.get("metrics_holdout"),
    }


@app.post("/predict", response_model=Prediction, status_code=status.HTTP_200_OK)
async def predict(
    application: LoanApplication,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> Prediction:
    """Predict default risk for one loan application.
    """
    if not hasattr(app.state, "model") or app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Kept optional for now; M5 will enforce token validation.
    _ = credentials

    # Validate payload features against metadata
    metadata = getattr(app.state, "metadata", {})
    feature_columns = metadata.get("feature_columns", {})
    numeric_features = feature_columns.get("numeric", [])
    categorical_features = feature_columns.get("categorical", [])
    ordered_features = [*numeric_features, *categorical_features]

    # Ensure payload is a JSON object
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Payload must be a JSON object")

    # Check for missing features, prioritizing LoanApplication fields over raw payload
    application_data = application.model_dump()
    missing_features = [
        col for col in ordered_features if col not in payload and col not in application_data
    ]
    if missing_features:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Missing required model features",
                "missing_features": missing_features,
            },
        )

    # Build model input from payload, prioritizing LoanApplication fields
    model_input = {
        col: payload.get(col, application_data.get(col))
        for col in ordered_features
    }
    x_input = pd.DataFrame([model_input], columns=ordered_features)

    try:
        # get prediction and probability
        prediction = int(app.state.model.predict(x_input)[0])
        probability = float(app.state.model.predict_proba(x_input)[0, 1])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Prediction(
        prediction=prediction,
        probability=probability,
        model_version=str(metadata.get("model_version", "unknown")),
        request_id=str(getattr(request.state, "request_id", "unknown")),
    )
