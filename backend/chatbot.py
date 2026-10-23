"""
Agriculture Chatbot Service
Powered by the Google GenAI SDK (google-genai).
Provides agriculture-only advisory with prediction context injection and session history.
"""

import os
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Fallback models in case of temporary 503 high-demand spikes
CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash"
]

BASE_SYSTEM_PROMPT = """You are an expert agriculture assistant dedicated to helping farmers and growers.

RULES & INSTRUCTIONS:
1. ONLY AGRICULTURE: Answer ONLY farming, agronomy, and crop-related questions (crops, soil health, irrigation, fertilizers, pests, plant diseases, and seasonal calendars).
2. OFF-TOPIC REJECTION: If asked anything outside of farming (general trivia, sports, coding, movies, politics), politely decline. State that you are an agriculture assistant and can only help with farming questions.
3. HONESTY & SAFETY: If unsure, admit you do not know rather than guessing. For serious crop infections or chemical pesticide dosages, always advise consulting a local agricultural extension officer.
4. SIMPLE LANGUAGE: Use clear, simple, practical language suitable for farmers.
5. CONCISE: Keep answers brief (2-4 short bullet points or paragraphs) unless the user asks for more detail."""


def build_system_prompt(context: Optional[Dict[str, Any]] = None) -> str:
    """Add active crop or disease prediction context to system instruction."""
    prompt = BASE_SYSTEM_PROMPT

    if not context:
        return prompt

    ctx_type = context.get("type")
    prompt += "\n\n--- ACTIVE PREDICTION CONTEXT ---"

    if ctx_type == "disease":
        plant = context.get("plant", "Crop")
        disease = context.get("disease", "Unknown Condition")
        conf = context.get("confidence", 0.0)
        prompt += f"""
The farmer recently ran leaf disease detection:
- Plant: {plant}
- Detected Condition: {disease}
- Confidence: {conf:.1f}%
Note: If the user asks follow-up questions like "how do I treat this?" or "what spray to use?", refer directly to {disease} on {plant}.
"""
    elif ctx_type == "crop":
        crop = context.get("crop", "Unknown Crop")
        conf = context.get("confidence", 0.0)
        inputs = context.get("inputs", {})
        prompt += f"""
The farmer recently ran crop recommendation:
- Recommended Crop: {crop} ({conf:.1f}% confidence)
- Soil/Weather Readings: {inputs}
Note: If the user asks about fertilizer, irrigation, or planting dates, give advice specifically for {crop}.
"""
    prompt += "---------------------------------\n"
    return prompt


def get_chat_response(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Send user question to Gemini API with conversation history and prediction context.
    """
    if not message or not message.strip():
        return "Please ask a farming-related question."

    if not GENAI_AVAILABLE:
        return "⚠️ Google GenAI library is not installed on the server."

    raw_key = os.getenv("GEMINI_API_KEY", "")
    api_key = "".join(raw_key.split()) if raw_key else ""
    if not api_key or api_key == "your_gemini_api_key_here":
        return "⚠️ Gemini API key is missing. Please configure GEMINI_API_KEY in your environment."

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"⚠️ Could not initialize Gemini client: {str(e)[:100]}"

    # Build system instruction with context
    system_instruction = build_system_prompt(context)

    # Convert past history into google-genai Content objects
    chat_history: List[types.Content] = []
    if history:
        for turn in history:
            role = "user" if turn.get("role") == "user" else "model"
            content = turn.get("content", "")
            if content:
                chat_history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=content)]
                    )
                )

    # Try models with fallback
    for model_name in CANDIDATE_MODELS:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
            chat = client.chats.create(
                model=model_name,
                config=config,
                history=chat_history
            )
            response = chat.send_message(message.strip())
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            err = str(e).lower()
            if "api_key" in err or "unauthenticated" in err:
                return "⚠️ Invalid Gemini API key. Please verify your GEMINI_API_KEY."
            continue

    return "⚠️ The AI service is currently busy. Please try your question again in a moment."
