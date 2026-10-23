/** JalSaathi API client. Provider credentials never enter this browser bundle. */

import { getAccessToken } from './auth'

export const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

async function requestJson(path, options = {}) {
  const token = await getAccessToken()
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...(options.headers || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof body.detail === 'object' ? body.detail.message : body.detail
    const error = new Error(detail || `Request failed (${response.status})`)
    error.category = typeof body.detail === 'object' ? body.detail.category : 'http_error'
    error.status = response.status
    throw error
  }
  return body
}

export async function checkHealth() {
  try {
    const data = await requestJson('/health')
    return { ...data, endpoint: API_BASE }
  } catch (error) {
    return { status: 'error', message: error.message, endpoint: API_BASE }
  }
}

export async function getScenarios() {
  return requestJson('/api/scenarios')
}

export async function evaluateScenario(scenarioId, temperatureC, moisturePercent) {
  const body = { scenario_id: scenarioId }
  if (temperatureC !== undefined) body.temperature_c = Number(temperatureC)
  if (moisturePercent !== undefined) body.moisture_percent = Number(moisturePercent)
  const result = await requestJson('/api/scenarios/evaluate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  })
  return result.data
}

export async function sendAssistantMessage(message, history = [], context = null, languageCode = 'hi-IN') {
  const result = await requestJson('/api/assistant/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, context, language_code: languageCode })
  })
  return result
}

export async function transcribeVoice(audioBlob, languageCode = 'hi-IN') {
  const form = new FormData()
  form.append('file', audioBlob, audioBlob.name || 'recording.webm')
  form.append('language_code', languageCode)
  const result = await requestJson('/api/voice/transcribe', { method: 'POST', body: form })
  return result.data
}

export async function synthesizeVoice(text, languageCode = 'hi-IN') {
  const token = await getAccessToken()
  const result = await fetch(`${API_BASE}/api/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ text, language_code: languageCode })
  })
  if (!result.ok) {
    const body = await result.json().catch(() => ({}))
    const detail = typeof body.detail === 'object' ? body.detail.message : body.detail
    const error = new Error(detail || `Speech generation failed (${result.status})`)
    error.category = typeof body.detail === 'object' ? body.detail.category : 'http_error'
    throw error
  }
  return URL.createObjectURL(await result.blob())
}

// Existing crop and disease tools remain available from the original product.
export async function predictCrop(data) {
  const result = await requestJson('/api/crop/predict', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
  })
  return result.data
}

export async function getSupportedCrops() {
  const result = await requestJson('/api/disease/crops')
  return result.crops || []
}

export async function predictDisease(imageFile, cropName) {
  const form = new FormData()
  form.append('file', imageFile)
  form.append('crop_name', cropName)
  const result = await requestJson('/api/disease/predict', { method: 'POST', body: form })
  return result.data
}

// Backward-compatible alias for the former chatbot component.
export async function sendChatMessage(message, history = [], context = null) {
  const result = await sendAssistantMessage(message, history, context, 'en-IN')
  return result.reply
}
