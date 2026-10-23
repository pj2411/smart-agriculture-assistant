import React, { useState } from 'react'
import { Sprout, Loader2, Sparkles, RefreshCw, AlertCircle } from 'lucide-react'
import { predictCrop } from '../api'
import ResultCard from './ResultCard'

const FIELD_CONFIGS = {
  nitrogen: {
    label: 'Nitrogen (N)',
    unit: 'kg/ha',
    min: 0,
    max: 500,
    step: 1,
    desc: '0 – 500 kg/ha'
  },
  phosphorus: {
    label: 'Phosphorus (P)',
    unit: 'kg/ha',
    min: 0,
    max: 500,
    step: 1,
    desc: '0 – 500 kg/ha'
  },
  potassium: {
    label: 'Potassium (K)',
    unit: 'kg/ha',
    min: 0,
    max: 500,
    step: 1,
    desc: '0 – 500 kg/ha'
  },
  ph: {
    label: 'Soil pH',
    unit: 'scale',
    min: 1.0,
    max: 14.0,
    step: 0.1,
    desc: '1.0 – 14.0 pH'
  },
  temperature: {
    label: 'Temperature',
    unit: '°C',
    min: -20,
    max: 65,
    step: 0.1,
    desc: '-20°C – 65°C'
  },
  humidity: {
    label: 'Relative Humidity',
    unit: '%',
    min: 0,
    max: 100,
    step: 0.1,
    desc: '0 – 100%'
  },
  rainfall: {
    label: 'Annual Rainfall',
    unit: 'mm',
    min: 0,
    max: 3000,
    step: 1,
    desc: '0 – 3000 mm'
  }
}

const PRESETS = [
  {
    name: 'Rice (Wetland)',
    values: { nitrogen: 90, phosphorus: 42, potassium: 43, ph: 6.5, temperature: 20.8, humidity: 82.0, rainfall: 202.0 }
  },
  {
    name: 'Maize (Temperate)',
    values: { nitrogen: 75, phosphorus: 48, potassium: 20, ph: 6.2, temperature: 24.5, humidity: 65.0, rainfall: 85.0 }
  },
  {
    name: 'Coffee (Highland)',
    values: { nitrogen: 100, phosphorus: 30, potassium: 30, ph: 6.8, temperature: 25.0, humidity: 58.0, rainfall: 160.0 }
  }
]

export default function CropTab({ onAskChatbot }) {
  const [formData, setFormData] = useState({
    nitrogen: 90,
    phosphorus: 42,
    potassium: 43,
    ph: 6.5,
    temperature: 20.8,
    humidity: 82.0,
    rainfall: 202.0
  })

  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [apiError, setApiError] = useState('')

  const validateField = (name, value) => {
    const cfg = FIELD_CONFIGS[name]
    if (!cfg) return ''
    if (value === '' || isNaN(value)) {
      return 'Field is required'
    }
    const num = parseFloat(value)
    if (num < cfg.min || num > cfg.max) {
      return `Must be between ${cfg.min} and ${cfg.max} ${cfg.unit}`
    }
    return ''
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    const numVal = value === '' ? '' : parseFloat(value)
    setFormData(prev => ({ ...prev, [name]: numVal }))

    const errorMsg = validateField(name, numVal)
    setErrors(prev => ({ ...prev, [name]: errorMsg }))
  }

  const handleApplyPreset = (preset) => {
    setFormData(preset.values)
    setErrors({})
    setApiError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    // Validate all fields
    const newErrors = {}
    let hasInvalid = false
    Object.keys(FIELD_CONFIGS).forEach(key => {
      const err = validateField(key, formData[key])
      if (err) {
        newErrors[key] = err
        hasInvalid = true
      }
    })

    setErrors(newErrors)
    if (hasInvalid) return

    setLoading(true)
    setApiError('')

    try {
      const data = await predictCrop({
        nitrogen: Number(formData.nitrogen),
        phosphorus: Number(formData.phosphorus),
        potassium: Number(formData.potassium),
        temperature: Number(formData.temperature),
        humidity: Number(formData.humidity),
        ph: Number(formData.ph),
        rainfall: Number(formData.rainfall)
      })
      setResult({ ...data, inputs: formData })
    } catch (err) {
      setApiError(err.message || 'Crop recommendation failed. Please verify backend connection.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card">
      {/* Header Info */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h2 style={{ fontSize: 'var(--fs-xl)', fontWeight: 700, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sprout size={22} color="var(--primary)" />
              Soil & Climate Crop Recommendation
            </h2>
            <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Input laboratory soil nutrient values and regional weather conditions to predict the most productive crop.
            </p>
          </div>

          {/* Quick Presets */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)', fontWeight: 600 }}>Presets:</span>
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(p)}
                style={{
                  padding: '0.3rem 0.65rem',
                  borderRadius: 'var(--radius-pill)',
                  border: '1px solid var(--border-light)',
                  background: 'var(--surface-raised)',
                  fontSize: 'var(--fs-xs)',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  cursor: 'pointer'
                }}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Global Error Banner */}
      {apiError && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-md)',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          color: 'var(--danger)',
          fontSize: 'var(--fs-sm)',
          marginBottom: '1.25rem'
        }}>
          <AlertCircle size={18} flexShrink={0} />
          <span>{apiError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* GROUP 1: Soil Nutrients */}
        <fieldset style={{ border: 'none', padding: 0, margin: '0 0 1.5rem 0' }}>
          <legend style={{
            fontSize: 'var(--fs-sm)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--primary)',
            marginBottom: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem'
          }}>
            <span>🌱</span> Soil Nutrients (N-P-K & pH)
          </legend>

          <div className="crop-form-grid">
            {['nitrogen', 'phosphorus', 'potassium', 'ph'].map(key => (
              <FormField
                key={key}
                name={key}
                cfg={FIELD_CONFIGS[key]}
                value={formData[key]}
                error={errors[key]}
                onChange={handleChange}
              />
            ))}
          </div>
        </fieldset>

        {/* GROUP 2: Climate Conditions */}
        <fieldset style={{ border: 'none', padding: 0, margin: '0 0 1.5rem 0' }}>
          <legend style={{
            fontSize: 'var(--fs-sm)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--accent)',
            marginBottom: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem'
          }}>
            <span>⛅</span> Climate & Environment
          </legend>

          <div className="crop-form-grid">
            {['temperature', 'humidity', 'rainfall'].map(key => (
              <FormField
                key={key}
                name={key}
                cfg={FIELD_CONFIGS[key]}
                value={formData[key]}
                error={errors[key]}
                onChange={handleChange}
              />
            ))}
          </div>
        </fieldset>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || Object.values(errors).some(Boolean)}
          className="btn-primary"
          style={{ width: '100%', minHeight: '48px' }}
        >
          {loading ? (
            <>
              <Loader2 size={20} className="spin-icon" />
              <span>Analyzing Soil & Climate Dynamics...</span>
            </>
          ) : (
            <>
              <Sparkles size={20} />
              <span>Recommend Optimal Crop</span>
            </>
          )}
        </button>
      </form>

      {/* Result Card */}
      {result && (
        <ResultCard
          type="crop"
          title={result.recommended_crop}
          subtitle={`Top recommendation matched based on CatBoost decision tree model`}
          confidence={result.confidence}
          actionLabel={`Ask the chatbot about growing ${result.recommended_crop}`}
          onAction={() => onAskChatbot(result)}
        />
      )}

      {/* Grid Layout Styles: 4 cols on desktop, 2 on tablet, 1 on mobile */}
      <style>{`
        .crop-form-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 1rem;
        }

        @media (min-width: 640px) {
          .crop-form-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (min-width: 1024px) {
          .crop-form-grid {
            grid-template-columns: repeat(4, 1fr);
          }
        }
      `}</style>
    </section>
  )
}

function FormField({ name, cfg, value, error, onChange }) {
  return (
    <div>
      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        justifyContent: 'space-between',
        marginBottom: '0.35rem'
      }}>
        <label htmlFor={name} style={{
          fontSize: 'var(--fs-sm)',
          fontWeight: 600,
          color: 'var(--text-secondary)'
        }}>
          {cfg.label}
        </label>
        <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>
          {cfg.desc}
        </span>
      </div>

      <input
        id={name}
        type="number"
        name={name}
        step={cfg.step}
        min={cfg.min}
        max={cfg.max}
        value={value}
        onChange={onChange}
        required
        className={`form-input ${error ? 'has-error' : ''}`}
        placeholder={cfg.desc}
      />

      {error && (
        <p style={{
          fontSize: 'var(--fs-xs)',
          color: 'var(--danger)',
          marginTop: '0.25rem',
          fontWeight: 500
        }}>
          {error}
        </p>
      )}
    </div>
  )
}
