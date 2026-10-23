import React from 'react'
import { Sprout, Stethoscope, MessageSquare } from 'lucide-react'

export default function BottomNav({ activeTab, setActiveTab, hasPredictionContext }) {
  const tabs = [
    { id: 'crop', label: 'Crop', icon: Sprout },
    { id: 'disease', label: 'Disease', icon: Stethoscope },
    { id: 'chat', label: 'Chat', icon: MessageSquare, hasBadge: hasPredictionContext }
  ]

  return (
    <>
      <nav className="mobile-bottom-nav">
        <div className="mobile-bottom-nav-inner">
          {tabs.map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`mobile-tab-btn ${isActive ? 'active' : ''}`}
                aria-label={tab.label}
              >
                <div style={{ position: 'relative', display: 'inline-flex' }}>
                  <Icon size={20} strokeWidth={isActive ? 2.4 : 1.8} />
                  {tab.hasBadge && (
                    <span style={{
                      position: 'absolute',
                      top: '-2px',
                      right: '-3px',
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: 'var(--primary)',
                      boxShadow: '0 0 0 2px var(--surface)'
                    }} />
                  )}
                </div>
                <span className="mobile-tab-label">{tab.label}</span>
              </button>
            )
          })}
        </div>
      </nav>

      <style>{`
        .mobile-bottom-nav {
          display: none;
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          z-index: 1000;
          background: var(--surface);
          border-top: 1px solid var(--border-light);
          box-shadow: 0 -4px 12px rgba(15, 23, 42, 0.06);
          padding-bottom: env(safe-area-inset-bottom, 0px);
        }

        .mobile-bottom-nav-inner {
          display: flex;
          align-items: center;
          justify-content: space-around;
          height: var(--bottom-nav-height);
          max-width: 600px;
          margin: 0 auto;
          padding: 0 0.5rem;
        }

        .mobile-tab-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3px;
          flex: 1;
          height: 100%;
          min-height: var(--touch-target);
          color: var(--text-muted);
          background: transparent;
          border-radius: var(--radius-sm);
          transition: color 0.15s ease, transform 0.1s ease;
        }

        .mobile-tab-btn.active {
          color: var(--primary);
          font-weight: 700;
        }

        .mobile-tab-label {
          font-size: var(--fs-xs);
          letter-spacing: -0.01em;
        }

        @media (max-width: 767px) {
          .mobile-bottom-nav {
            display: block;
          }
        }
      `}</style>
    </>
  )
}
