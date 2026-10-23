import React, { useState } from 'react'
import {
  Sprout,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  MessageSquare,
  ArrowRight,
  ShieldAlert,
  Leaf,
  FlaskConical,
  ChevronDown,
  ChevronUp
} from 'lucide-react'

/**
 * ResultCard Component
 * Displays prediction results for Crop Recommendation and Plant Disease Detection.
 * Supports:
 * - Top-1 result with healthy/disease/uncertain styling
 * - Top-3 prediction confidence distribution
 * - Comprehensive treatment recommendations (Organic, Chemical, Prevention)
 * - One-click transition to Agriculture Chatbot
 */
export default function ResultCard({
  type, // 'crop' | 'disease'
  title,
  subtitle,
  confidence,
  isHealthy,
  isUncertain = false,
  topPredictions = [],
  treatment = null,
  onAction,
  actionLabel
}) {
  const [showAllCandidates, setShowAllCandidates] = useState(false)
  const isDisease = type === 'disease'

  // Determine semantic color scheme
  let badgeColor = 'var(--primary)'
  let badgeBg = 'var(--primary-subtle)'
  let badgeBorder = 'var(--primary-subtle-border)'
  let statusText = 'Recommended Optimal Crop'

  if (isDisease) {
    if (isUncertain) {
      badgeColor = 'var(--warning)'
      badgeBg = 'var(--warning-bg)'
      badgeBorder = 'var(--warning-border)'
      statusText = 'Uncertain Diagnosis'
    } else if (isHealthy) {
      badgeColor = 'var(--success)'
      badgeBg = 'var(--success-bg)'
      badgeBorder = 'var(--success-border)'
      statusText = 'Healthy Specimen'
    } else {
      badgeColor = 'var(--danger)'
      badgeBg = 'var(--danger-bg)'
      badgeBorder = 'var(--danger-border)'
      statusText = 'Condition Detected'
    }
  }

  // Clamped confidence between 0 and 100
  const confValue = Math.min(Math.max(Number(confidence) || 0, 0), 100)

  return (
    <div style={{
      marginTop: '1.5rem',
      padding: '1.35rem',
      borderRadius: 'var(--radius-lg)',
      background: 'var(--surface-raised)',
      border: `1.5px solid ${badgeBorder}`,
      boxShadow: 'var(--shadow-md)',
      transition: 'all 0.25s ease'
    }}>
      {/* Top Header with Status/Type Badge */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        marginBottom: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: 'var(--radius-md)',
            background: badgeBg,
            color: badgeColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            {isDisease ? (
              isUncertain ? (
                <HelpCircle size={24} />
              ) : isHealthy ? (
                <CheckCircle2 size={24} />
              ) : (
                <AlertTriangle size={24} />
              )
            ) : (
              <Sprout size={24} />
            )}
          </div>

          <div>
            <span style={{
              fontSize: 'var(--fs-xs)',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: badgeColor
            }}>
              {statusText}
            </span>
            <h3 style={{
              fontSize: 'var(--fs-xl)',
              fontWeight: 800,
              color: 'var(--text-main)',
              lineHeight: 1.25,
              textTransform: 'capitalize',
              margin: '2px 0 0 0'
            }}>
              {title}
            </h3>
            {subtitle && (
              <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Confidence Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.4rem 0.85rem',
          borderRadius: 'var(--radius-pill)',
          background: 'var(--surface)',
          border: '1px solid var(--border-light)',
          fontSize: 'var(--fs-sm)',
          fontWeight: 700,
          color: 'var(--text-main)',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <span>Confidence:</span>
          <span style={{ color: badgeColor }}>{confValue.toFixed(1)}%</span>
        </div>
      </div>

      {/* Primary Confidence Progress Bar */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{
          height: '9px',
          width: '100%',
          backgroundColor: 'var(--border-light)',
          borderRadius: 'var(--radius-pill)',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${confValue}%`,
            backgroundColor: badgeColor,
            borderRadius: 'var(--radius-pill)',
            transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)'
          }} />
        </div>
      </div>

      {/* Top Candidates (Top-3 Predictions) */}
      {topPredictions && topPredictions.length > 1 && (
        <div style={{
          marginBottom: '1.25rem',
          padding: '0.9rem',
          borderRadius: 'var(--radius-md)',
          background: 'var(--surface)',
          border: '1px solid var(--border-light)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '0.65rem'
          }}>
            <span style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Top Candidate Predictions (ResNet50 Softmax Distribution)
            </span>
            {topPredictions.length > 2 && (
              <button
                type="button"
                onClick={() => setShowAllCandidates(!showAllCandidates)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: 'var(--fs-xs)',
                  color: 'var(--primary)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '2px',
                  padding: 0
                }}
              >
                {showAllCandidates ? <>Less <ChevronUp size={14} /></> : <>All ({topPredictions.length}) <ChevronDown size={14} /></>}
              </button>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {(showAllCandidates ? topPredictions : topPredictions.slice(0, 3)).map((item, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: 'var(--fs-xs)' }}>
                <span style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  background: idx === 0 ? badgeBg : 'var(--surface-raised)',
                  color: idx === 0 ? badgeColor : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '11px',
                  flexShrink: 0
                }}>
                  {idx + 1}
                </span>

                <span style={{ flex: 1, fontWeight: idx === 0 ? 600 : 500, color: 'var(--text-main)' }}>
                  {item.disease}
                </span>

                <div style={{ width: '80px', height: '6px', background: 'var(--surface-raised)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(item.confidence, 100)}%`,
                    height: '100%',
                    background: idx === 0 ? badgeColor : 'var(--text-muted)',
                    borderRadius: '3px'
                  }} />
                </div>

                <span style={{ width: '45px', textAlign: 'right', fontWeight: 600, color: idx === 0 ? badgeColor : 'var(--text-secondary)' }}>
                  {item.confidence.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Structured Treatment Advisory (Organic, Chemical, Prevention) */}
      {treatment && (
        <div style={{
          marginBottom: '1.25rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem'
        }}>
          {treatment.organic && (
            <div style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.65rem'
            }}>
              <Leaf size={18} color="var(--success)" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <strong style={{ fontSize: 'var(--fs-xs)', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--success)', display: 'block', marginBottom: '2px' }}>
                  Organic & Biological Remedy
                </strong>
                <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-secondary)', lineHeight: 1.45, margin: 0 }}>
                  {treatment.organic}
                </p>
              </div>
            </div>
          )}

          {treatment.chemical && (
            <div style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.65rem'
            }}>
              <FlaskConical size={18} color="var(--warning)" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <strong style={{ fontSize: 'var(--fs-xs)', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--warning)', display: 'block', marginBottom: '2px' }}>
                  Recommended Agronomic / Chemical Spray
                </strong>
                <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-secondary)', lineHeight: 1.45, margin: 0 }}>
                  {treatment.chemical}
                </p>
              </div>
            </div>
          )}

          {treatment.prevention && (
            <div style={{
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.65rem'
            }}>
              <ShieldAlert size={18} color="var(--primary)" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <strong style={{ fontSize: 'var(--fs-xs)', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--primary)', display: 'block', marginBottom: '2px' }}>
                  Cultural Prevention & Management
                </strong>
                <p style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-secondary)', lineHeight: 1.45, margin: 0 }}>
                  {treatment.prevention}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action button to switch to Chatbot with Context */}
      {onAction && (
        <button
          type="button"
          onClick={onAction}
          className="btn-primary"
          style={{
            width: '100%',
            justifyContent: 'space-between',
            background: 'var(--surface)',
            color: 'var(--primary)',
            border: '1.5px solid var(--primary)',
            boxShadow: 'none'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--primary-light)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--surface)'
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
            <MessageSquare size={18} />
            <span>{actionLabel || 'Ask the Agriculture Chatbot about this'}</span>
          </span>
          <ArrowRight size={18} />
        </button>
      )}
    </div>
  )
}
