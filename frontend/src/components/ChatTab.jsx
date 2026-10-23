import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Trash2, X, Sparkles, AlertCircle, Bookmark } from 'lucide-react'
import { sendChatMessage } from '../api'

export default function ChatTab({ predictionContext, onClearContext }) {
  const [messages, setMessages] = useState([
    {
      id: 'greeting',
      role: 'assistant',
      content: 'Hello! I am your AI Agriculture Assistant. Ask me anything about crop cultivation, soil health, irrigation schedules, fertilizers, or plant disease treatments.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatBottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Scroll to bottom when messages update
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (textToSend) => {
    const query = (textToSend || input).trim()
    if (!query || loading) return

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: now
    }

    const updated = [...messages, userMsg]
    setMessages(updated)
    setInput('')
    setLoading(true)

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    try {
      // Build history payload omitting initial greeting
      const historyPayload = messages.slice(1).map(m => ({ role: m.role, content: m.content }))
      const reply = await sendChatMessage(query, historyPayload, predictionContext)

      setMessages([...updated, {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } catch (err) {
      setMessages([...updated, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error contacting agriculture AI: ${err.message || 'Please check your connection and try again.'}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClearChat = () => {
    setMessages([messages[0]])
  }

  // Dynamic suggestions based on context
  const suggestions = predictionContext?.type === 'disease'
    ? [
        `How do I treat ${predictionContext.disease} on ${predictionContext.plant}?`,
        'Are there organic or biological fungicide alternatives?',
        'How can I sanitize my tools to prevent infection spread?'
      ]
    : (predictionContext?.type === 'crop'
      ? [
          `What is the best sowing window for ${predictionContext.crop}?`,
          `Recommended fertilizer dosage (NPK) for ${predictionContext.crop}?`,
          `How much irrigation does ${predictionContext.crop} require per week?`
        ]
      : [
          'What is the optimal soil pH for growing wheat?',
          'How do I naturally improve soil organic matter?',
          'What are common early signs of nitrogen deficiency?',
          'How often should drip irrigation be scheduled for tomatoes?'
        ])

  const isInitialState = messages.length <= 1

  return (
    <section className="card chat-tab-card" style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'clamp(520px, calc(100dvh - 190px), 760px)',
      padding: '1rem',
      position: 'relative'
    }}>
      {/* Top Chat Bar: Title + Context Badge + Clear Button */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-light)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--primary-subtle)',
            color: 'var(--primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Bot size={18} />
          </div>
          <div>
            <h2 style={{ fontSize: 'var(--fs-base)', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>
              Agriculture Advisory Chat
            </h2>
            <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>
              Powered by Google Gemini agronomy knowledge
            </p>
          </div>
        </div>

        {messages.length > 1 && (
          <button
            type="button"
            onClick={handleClearChat}
            className="btn-secondary"
            style={{ padding: '0.35rem 0.65rem', minHeight: '34px', fontSize: 'var(--fs-xs)' }}
          >
            <Trash2 size={14} />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* Active Prediction Context Badge */}
      {predictionContext && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          padding: '0.45rem 0.75rem',
          marginTop: '0.5rem',
          borderRadius: 'var(--radius-md)',
          background: 'var(--primary-light)',
          border: '1px solid var(--primary-subtle-border)',
          fontSize: 'var(--fs-xs)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--primary)' }}>
            <Bookmark size={14} />
            <span style={{ fontWeight: 600 }}>Active Context:</span>
            <span style={{ color: 'var(--text-main)' }}>
              {predictionContext.type === 'disease'
                ? `${predictionContext.plant} • ${predictionContext.disease} (${predictionContext.confidence}%)`
                : `${predictionContext.crop} (${predictionContext.confidence}%)`}
            </span>
          </div>

          <button
            type="button"
            onClick={onClearContext}
            style={{
              color: 'var(--text-muted)',
              display: 'inline-flex',
              alignItems: 'center',
              padding: '2px',
              borderRadius: 'var(--radius-sm)'
            }}
            title="Detach context"
            aria-label="Clear active context"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Scrollable Messages Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '0.75rem 0.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem'
      }}>
        {messages.map((m) => {
          const isUser = m.role === 'user'
          return (
            <div
              key={m.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
                maxWidth: '100%'
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.5rem',
                flexDirection: isUser ? 'row-reverse' : 'row',
                maxWidth: '85%'
              }}>
                {/* Avatar Icon */}
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: isUser ? 'var(--primary)' : 'var(--surface-raised)',
                  color: isUser ? '#ffffff' : 'var(--primary)',
                  border: isUser ? 'none' : '1px solid var(--border-light)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  marginTop: '2px'
                }}>
                  {isUser ? <User size={15} /> : <Bot size={15} />}
                </div>

                {/* Bubble */}
                <div style={{
                  padding: '0.75rem 0.95rem',
                  borderRadius: 'var(--radius-lg)',
                  background: isUser
                    ? 'var(--primary)'
                    : (m.isError ? 'var(--danger-bg)' : 'var(--surface-raised)'),
                  color: isUser
                    ? '#ffffff'
                    : (m.isError ? 'var(--danger)' : 'var(--text-main)'),
                  border: isUser ? 'none' : `1px solid ${m.isError ? 'var(--danger-border)' : 'var(--border-light)'}`,
                  fontSize: 'var(--fs-sm)',
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap',
                  boxShadow: 'var(--shadow-sm)',
                  borderBottomRightRadius: isUser ? '2px' : 'var(--radius-lg)',
                  borderBottomLeftRadius: isUser ? 'var(--radius-lg)' : '2px'
                }}>
                  {m.content}
                </div>
              </div>

              {/* Timestamp */}
              {m.timestamp && (
                <span style={{
                  fontSize: '10px',
                  color: 'var(--text-muted)',
                  marginTop: '2px',
                  paddingLeft: isUser ? '0' : '36px',
                  paddingRight: isUser ? '36px' : '0'
                }}>
                  {m.timestamp}
                </span>
              )}
            </div>
          )
        })}

        {/* Typing indicator */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: 'var(--surface-raised)',
              color: 'var(--primary)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Bot size={15} />
            </div>
            <div style={{
              padding: '0.6rem 0.9rem',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--surface-raised)',
              border: '1px solid var(--border-light)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Suggested question chips (Shown only when chat is at initial greeting) */}
      {isInitialState && (
        <div style={{
          padding: '0.5rem 0',
          borderTop: '1px dashed var(--border-light)',
          marginTop: 'auto'
        }}>
          <p style={{
            fontSize: 'var(--fs-xs)',
            fontWeight: 600,
            color: 'var(--text-muted)',
            marginBottom: '0.4rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem'
          }}>
            <Sparkles size={13} color="var(--primary)" /> Suggested questions:
          </p>
          <div className="suggestion-chips-container">
            {suggestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(q)}
                className="chip-btn"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Pinned Input Form at Bottom */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSend()
        }}
        style={{
          display: 'flex',
          gap: '0.5rem',
          paddingTop: '0.6rem',
          borderTop: '1px solid var(--border-light)'
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question... (Enter to send, Shift+Enter for new line)"
          disabled={loading}
          rows={1}
          style={{
            flex: 1,
            minHeight: 'var(--touch-target)',
            maxHeight: '120px',
            resize: 'none',
            padding: '0.65rem 0.85rem',
            fontSize: 'var(--fs-sm)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-light)',
            background: 'var(--surface)',
            color: 'var(--text-main)',
            outline: 'none',
            lineHeight: 1.4
          }}
        />

        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="btn-primary"
          style={{
            minWidth: '48px',
            minHeight: 'var(--touch-target)',
            padding: '0.65rem 1rem',
            borderRadius: 'var(--radius-md)'
          }}
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </form>

      {/* Scoped CSS for responsive suggestions */}
      <style>{`
        .suggestion-chips-container {
          display: flex;
          gap: 0.5rem;
          overflow-x: auto;
          white-space: nowrap;
          padding-bottom: 4px;
          -webkit-overflow-scrolling: touch;
        }

        .chip-btn {
          flex-shrink: 0;
          padding: 0.4rem 0.75rem;
          border-radius: var(--radius-pill);
          background: var(--surface-raised);
          border: 1px solid var(--border-light);
          color: var(--text-secondary);
          font-size: var(--fs-xs);
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s ease;
          min-height: 32px;
        }

        .chip-btn:hover {
          background: var(--primary-light);
          color: var(--primary);
          border-color: var(--primary-subtle-border);
        }
      `}</style>
    </section>
  )
}
