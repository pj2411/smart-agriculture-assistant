"""
JalSaathi - FastAPI Backend Entrypoint
Provides endpoints for:
- Health checks: GET /health
- Crop Recommendation: POST /api/crop/predict
- Disease Detection: POST /api/disease/predict
- JalSaathi scenario lab and voice-first assistant endpoints
"""

import os
from typing import List, Dict, Optional, Any
from fastapi import Depends, FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load local environment variables from backend directory and current directory
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
load_dotenv()

from crop import predict_crop
from disease import predict_disease, get_supported_crops, get_disease_health
from jalsaathi_domain import ScenarioNotFound, evaluate_scenario, load_scenarios
from jalsaathi_providers import ProviderError, get_llm_response, provider_status, synthesize_speech, transcribe_audio
from auth import auth_status, require_user
from languages import SUPPORTED_LANGUAGE_CODES, SUPPORTED_LANGUAGES

app = FastAPI(
    title="JalSaathi API",
    description="Voice-first, crop-aware climate assistant for small and medium-sized farmers.",
    version="2.0.0"
)

# -------------------------------------------------------------
# CORS Configuration (Defaults to allowing all origins)
# -------------------------------------------------------------
raw_cors = os.getenv("CORS_ORIGINS", "*")
origins = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

if "*" in origins or not origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# -------------------------------------------------------------
# Pydantic Request Schemas
# -------------------------------------------------------------
class CropRequest(BaseModel):
    nitrogen: float = Field(..., ge=0, le=500, description="Nitrogen content (kg/ha)")
    phosphorus: float = Field(..., ge=0, le=500, description="Phosphorus content (kg/ha)")
    potassium: float = Field(..., ge=0, le=500, description="Potassium content (kg/ha)")
    temperature: float = Field(..., ge=-20, le=65, description="Temperature (°C)")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity (%)")
    ph: float = Field(..., ge=1, le=14, description="Soil pH value")
    rainfall: float = Field(..., ge=0, le=3000, description="Rainfall (mm)")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Farmer user message")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Session chat history")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Active crop or disease context")
    language_code: str = Field(default="hi-IN", pattern=r"^(hi-IN|pa-IN|en-IN|bn-IN|mr-IN)$")


class ScenarioRequest(BaseModel):
    scenario_id: str = Field(..., min_length=1)
    temperature_c: Optional[float] = Field(default=None, ge=-50, le=80)
    moisture_percent: Optional[float] = Field(default=None, ge=0, le=100)


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------
@app.get("/")
def root():
    """Root endpoint for Render default health checks and quick status."""
    return {
        "status": "ok",
        "service": "JalSaathi API",
        "health": "/health",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Service readiness without exposing provider credentials."""
    return {
        "status": "ok",
        "service": "JalSaathi API",
        "providers": provider_status(),
        "auth": auth_status(),
        "scenario_lab": {"available": load_scenarios().get("available", False), "case_count": len(load_scenarios().get("scenarios", []))},
        "disease_module": get_disease_health(),
        "device": {"status": "planned_not_connected", "ingest_enabled": False, "control_enabled": False},
    }


@app.get("/api/jalsaathi/health")
def jalsaathi_health_endpoint():
    return health_check()


@app.get("/api/auth/status")
def auth_status_endpoint():
    return auth_status()


@app.get("/api/languages")
def languages_endpoint():
    """Return the locales enabled for the full STT -> LLM -> TTS path."""
    return {"languages": [{"code": code, **details} for code, details in SUPPORTED_LANGUAGES.items()]}


@app.get("/api/scenarios")
def scenarios_endpoint():
    """Return the exact test-only climate fixtures, never live device data."""
    return load_scenarios()


@app.post("/api/scenarios/evaluate")
def evaluate_scenario_endpoint(payload: ScenarioRequest):
    try:
        return {"success": True, "data": evaluate_scenario(payload.scenario_id, payload.temperature_c, payload.moisture_percent)}
    except ScenarioNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/iot/polyhouse/data")
def iot_polyhouse_data(ip: str = "10.222.101.169"):
    """Proxy live telemetry from the local ESP8266 node, bypassing browser CORS & Private Network restrictions."""
    import urllib.request
    import json
    target_url = f"http://{ip.strip()}/data"
    req = urllib.request.Request(target_url, headers={"Accept": "application/json, text/plain, */*"})
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            content = resp.read().decode("utf-8")
            try:
                return json.loads(content)
            except Exception:
                return {"raw_text": content}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach ESP8266 at {ip}: {str(e)}")


@app.get("/api/iot/polyhouse/set-state")
def iot_polyhouse_set_state(state: str, ip: str = "10.222.101.169"):
    """Proxy state override to the local ESP8266 node."""
    import urllib.request
    target_url = f"http://{ip.strip()}/set-state?state={state.strip()}"
    req = urllib.request.Request(target_url)
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return {"success": True, "status": resp.status}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach ESP8266 at {ip}: {str(e)}")


def _provider_error_response(exc: ProviderError) -> HTTPException:
    status = 503 if exc.category in {"not_configured", "provider_network_error", "provider_timeout"} else 502
    return HTTPException(status_code=status, detail={"category": exc.category, "message": str(exc)})


@app.get("/api/disease/health")
def disease_health_endpoint():
    """Dedicated diagnostic health check for plant disease detection subsystem."""
    return {"status": "ok", "data": get_disease_health()}


@app.post("/api/crop/predict")
def predict_crop_endpoint(payload: CropRequest):
    """
    Predict optimal crop based on soil and weather parameters.
    """
    try:
        result = predict_crop(
            nitrogen=payload.nitrogen,
            phosphorus=payload.phosphorus,
            potassium=payload.potassium,
            temperature=payload.temperature,
            humidity=payload.humidity,
            ph=payload.ph,
            rainfall=payload.rainfall
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop prediction failed: {str(e)}")


@app.get("/api/disease/crops")
def get_supported_crops_endpoint():
    """List of 13 supported plants for leaf disease diagnosis."""
    return {"crops": get_supported_crops()}


@app.post("/api/disease/predict")
async def predict_disease_endpoint(
    file: UploadFile = File(..., description="Leaf image file"),
    crop_name: str = Form(..., description="Crop identifier, e.g. 'apple'")
):
    """
    Predict plant disease from uploaded leaf image and crop name.
    Includes upload validation, top-3 candidates, and treatment advice.
    """
    # 1. Validate content type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type and file.content_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format '{file.content_type}'. Please upload a JPG, PNG, or WEBP photo."
        )

    try:
        image_bytes = await file.read()
        if not image_bytes or len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded image is empty (0 bytes). Please select a valid photo.")

        result = predict_disease(image_bytes=image_bytes, crop_key=crop_name)
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except ValueError as ve:
        # User input or validation error
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fe:
        # Model file not found on disk or failed download
        raise HTTPException(
            status_code=503,
            detail=f"The deep learning model weights for '{crop_name}' are currently unavailable. Please try again shortly."
        )
    except Exception as e:
        # Log internal error and return sanitized message
        import logging
        logging.getLogger("uvicorn.error").error(f"Disease prediction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while analyzing the leaf image. Please ensure the image is clear and try again."
        )


def _chat_response(payload: ChatRequest):
    """
    Send a real farming question to the configured OpenRouter model.
    """
    try:
        formatted_history = [
            {"role": msg.role, "content": msg.content} for msg in payload.history
        ]
        result = get_llm_response(
            message=payload.message,
            history=formatted_history,
            context=payload.context,
            language_code=payload.language_code,
        )
        return {"success": True, **result}
    except ProviderError as exc:
        raise _provider_error_response(exc)


@app.post("/api/chat")
def chat_endpoint(payload: ChatRequest, current_user: Dict[str, Any] = Depends(require_user)):
    return _chat_response(payload)


@app.post("/api/assistant/chat")
def assistant_chat_endpoint(payload: ChatRequest, current_user: Dict[str, Any] = Depends(require_user)):
    return _chat_response(payload)


@app.post("/api/voice/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(..., description="Short microphone recording"),
    language_code: str = Form("hi-IN"),
    current_user: Dict[str, Any] = Depends(require_user),
):
    if language_code not in SUPPORTED_LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Supported languages are en-IN, hi-IN, pa-IN, bn-IN and mr-IN.")
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Please upload an audio recording.")
    audio_bytes = await file.read()
    max_bytes = int(os.getenv("MAX_AUDIO_UPLOAD_MB", "10")) * 1024 * 1024
    if not audio_bytes or len(audio_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail="Audio is empty or exceeds the configured upload limit.")
    try:
        return {"success": True, "data": transcribe_audio(audio_bytes, file.filename or "recording.webm", file.content_type, language_code)}
    except ProviderError as exc:
        raise _provider_error_response(exc)


@app.post("/api/voice/speak")
def speak_endpoint(payload: Dict[str, Any], current_user: Dict[str, Any] = Depends(require_user)):
    text = str(payload.get("text", "")).strip()
    language_code = str(payload.get("language_code", "hi-IN"))
    if not text or len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text is required and must be at most 5,000 characters.")
    if language_code not in SUPPORTED_LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Supported languages are en-IN, hi-IN, pa-IN, bn-IN and mr-IN.")
    try:
        audio_bytes, mime_type = synthesize_speech(text, language_code)
        from fastapi.responses import Response
        return Response(content=audio_bytes, media_type=mime_type, headers={"X-JalSaathi-Provider": "gnani"})
    except ProviderError as exc:
        raise _provider_error_response(exc)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
