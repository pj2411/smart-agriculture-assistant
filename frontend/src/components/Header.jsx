import React, { useState } from 'react'
import { Sprout, Stethoscope, MessageSquare, Info, AlertCircle, CheckCircle2, Clock } from 'lucide-react'

export default function Header({
  activeTab,
  setActiveTab,
  backendStatus,
  backendDetails,
  onRetryBackend,
  hasPredictionContext
}) {
  const [showTooltip, setShowTooltip] = useState(false)

  const getStatusConfig = () => {
    switch (backendStatus) {
      case 'online':
        return {
          label: 'Connected',
          color: 'var(--success)',
          bg: 'var(--success-bg)',
          border: 'var(--success-border)',
          icon: CheckCircle2,
          pulse: false
        }
      case 'checking':
        return {
          label: 'Connecting...',
          color: 'var(--warning)',
          bg: 'var(--warning-bg)',
          border: 'var(--warning-border)',
          icon: Clock,
          pulse: true
        }
      default:
        return {
          label: 'Offline',
          color: 'var(--danger)',
          bg: 'var(--danger-bg)',
          border: 'var(--danger-border)',
          icon: AlertCircle,
          pulse: false
        }
    }
  }

  const status = getStatusConfig()
  const StatusIcon = status.icon

  return (
    <header style={{ marginBottom: '1.25rem' }}>
      {/* Top Bar: Brand + Backend Status */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        paddingBottom: '1rem'
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, var(--primary) 0%, #16a34a 100%)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 10px var(--primary-glow)',
            flexShrink: 0
          }}>
            <Sprout size={24} strokeWidth={2.2} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h1 style={{
                fontSize: 'var(--fs-xl)',
                fontWeight: 700,
                color: 'var(--text-main)',
                letterSpacing: '-0.02em',
                lineHeight: 1.2
              }}>
                JalSaathi
              </h1>
            </div>
            <p style={{
              fontSize: 'var(--fs-xs)',
              color: 'var(--text-muted)',
              fontWeight: 500
            }}>
              Farmer climate companion • Crop advisory & plant tools
            </p>
          </div>
        </div>

        {/* Backend Status Badge with Popover Warning */}
        <div
          style={{ position: 'relative' }}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          <button
            type="button"
            onClick={() => setShowTooltip(!showTooltip)}
            aria-label="Server connection status details"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.4rem 0.85rem',
              borderRadius: 'var(--radius-pill)',
              background: status.bg,
              border: `1px solid ${status.border}`,
              color: status.color,
              fontSize: 'var(--fs-xs)',
              fontWeight: 600,
              minHeight: '34px',
              cursor: 'pointer',
              transition: 'transform 0.15s ease'
            }}
          >
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: status.color,
              display: 'inline-block'
            }} className={status.pulse ? 'pulse-dot' : ''} />

            <span>Backend: {status.label}</span>
            <Info size={13} style={{ opacity: 0.7 }} />
          </button>

          {/* Wakeup advisory tooltip / popover */}
          {showTooltip && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 6px)',
              right: 0,
              zIndex: 100,
              width: '280px',
              padding: '0.85rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface-card)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-medium)',
              boxShadow: 'var(--shadow-lg)',
              fontSize: 'var(--fs-xs)',
              lineHeight: 1.45,
              animation: 'fadeIn 0.2s ease'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <p style={{ fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
                  Server Status: {status.label}
                </p>
                {onRetryBackend && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onRetryBackend()
                    }}
                    style={{
                      border: '1px solid var(--border-medium)',
                      background: 'var(--surface-subtle)',
                      color: 'var(--primary)',
                      cursor: 'pointer',
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    🔄 Retry
                  </button>
                )}
              </div>

              {backendDetails?.endpoint && (
                <p style={{ margin: '0 0 6px 0', wordBreak: 'break-all' }}>
                  <strong style={{ color: 'var(--text-main)' }}>API Target:</strong>{' '}
                  <code style={{ fontSize: '11px', background: 'var(--surface-subtle)', padding: '2px 4px', borderRadius: '4px' }}>
                    {backendDetails.endpoint}
                  </code>
                </p>
              )}

              <p style={{ margin: 0 }}>
                {backendStatus === 'online'
                  ? 'FastAPI neural backend is active and responding.'
                  : backendStatus === 'checking'
                  ? 'Connecting to server / waking up container...'
                  : 'Free tier instances sleep after 15 min of inactivity and take ~45–60s to wake up.'}
              </p>

              {typeof window !== 'undefined' && window.location.protocol === 'https:' && backendDetails?.endpoint?.startsWith('http://localhost') && (
                <div style={{
                  marginTop: '8px',
                  padding: '6px 8px',
                  background: 'var(--danger-bg)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--danger-border)',
                  color: 'var(--danger)',
                  fontSize: '11px',
                  lineHeight: 1.35
                }}>
                  ⚠️ <strong>Action needed:</strong> App is on HTTPS but API is pointing to localhost. Add <code>VITE_API_URL</code> in Vercel settings and redeploy.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Desktop Horizontal Tabs (Hidden on mobile <768px via media query) */}
      <nav
        className="desktop-tabs-nav"
        style={{
          borderBottom: '1px solid var(--border-light)',
          marginTop: '0.5rem'
        }}
      >
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          overflowX: 'auto'
        }}>
          <TabButton
            active={activeTab === 'crop'}
            onClick={() => setActiveTab('crop')}
            icon={Sprout}
            label="Crop Recommendation"
          />
          <TabButton
            active={activeTab === 'disease'}
            onClick={() => setActiveTab('disease')}
            icon={Stethoscope}
            label="Disease Diagnosis"
          />
          <TabButton
            active={activeTab === 'chat'}
            onClick={() => setActiveTab('chat')}
            icon={MessageSquare}
            label="Agriculture Chatbot"
            hasBadge={hasPredictionContext}
          />
        </div>
      </nav>

      {/* Scoped CSS for responsive tab visibility */}
      <style>{`
        @media (max-width: 767px) {
          .desktop-tabs-nav {
            display: none !important;
          }
        }
        @media (min-width: 768px) {
          .desktop-tabs-nav {
            display: block !important;
          }
        }
      `}</style>
    </header>
  )
}

function TabButton({ active, onClick, icon: Icon, label, hasBadge }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.75rem 1.25rem',
        minHeight: 'var(--touch-target)',
        fontWeight: active ? 600 : 500,
        fontSize: 'var(--fs-sm)',
        color: active ? 'var(--primary)' : 'var(--text-muted)',
        background: active ? 'var(--primary-light)' : 'transparent',
        borderBottom: active ? '2px solid var(--primary)' : '2px solid transparent',
        borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
        transition: 'all 0.2s ease',
        position: 'relative'
      }}
    >
      <Icon size={18} strokeWidth={active ? 2.3 : 1.8} />
      <span>{label}</span>
      {hasBadge && (
        <span style={{
          width: '7px',
          height: '7px',
          borderRadius: '50%',
          backgroundColor: 'var(--primary)',
          boxShadow: '0 0 0 2px var(--surface)'
        }} />
      )}
    </button>
  )
}
