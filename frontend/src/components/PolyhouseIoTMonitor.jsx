import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  CloudRain,
  Cpu,
  Droplet,
  Edit2,
  Info,
  Leaf,
  Radio,
  RefreshCw,
  Sliders,
  Sun,
  Wifi,
  WifiOff
} from 'lucide-react'

// DEFAULT TARGET IP & BACKEND API URL
const DEFAULT_ESP_IP = '10.222.101.169'
const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
const FETCH_INTERVAL_MS = 2000
const TIMEOUT_MS = 1800

// SITE HARMONIZED HARDWARE PROFILES (Matching JalSaathi Color System)
const HARDWARE_PROFILES = {
  wet: {
    stateKey: 'wet',
    ledColor: 'RED',
    pin: 'D5 (GPIO14)',
    title: 'High Moisture / Rain',
    badge: '🌧️ Rain / Saturated',
    description: 'Triggers Red LED (D5) & halts all irrigation pumps.',
    defaultRaw: 880,
    defaultStatus: 'High Moisture / Saturated',
    defaultAction: 'Rain or saturated soil detected. Halting all irrigation pumps.',
    colorHex: '#B94E3D',
    bgLight: '#FCECE8',
    borderGlow: '#E7BDB3',
    boxGlow: '0 0 20px rgba(185, 78, 61, 0.22)',
    badgeBg: '#FCECE8',
    badgeText: '#B94E3D',
    badgeBorder: '#E7BDB3',
    lampHex: '#B94E3D'
  },
  yellow: {
    stateKey: 'yellow',
    ledColor: 'YELLOW',
    pin: 'D6 (GPIO12)',
    title: 'Mild Moisture',
    badge: '⛅ Optimal / Mild',
    description: 'Triggers Yellow LED (D6) for light misting spray.',
    defaultRaw: 512,
    defaultStatus: 'Optimal Moisture Range',
    defaultAction: 'Moisture levels optimal. Light misting spray cycle on standby.',
    colorHex: '#C58A35',
    bgLight: '#FFF4DD',
    borderGlow: '#E9D09A',
    boxGlow: '0 0 20px rgba(197, 138, 53, 0.22)',
    badgeBg: '#FFF4DD',
    badgeText: '#C58A35',
    badgeBorder: '#E9D09A',
    lampHex: '#C58A35'
  },
  dry: {
    stateKey: 'dry',
    ledColor: 'GREEN',
    pin: 'D7 (GPIO13)',
    title: 'Dry Soil',
    badge: '☀️ Dry / Water Needed',
    description: 'Triggers Green LED (D7) to initiate full watering.',
    defaultRaw: 185,
    defaultStatus: 'Dry Soil / Water Needed',
    defaultAction: 'Soil is dry. Initiating full drip irrigation cycle.',
    colorHex: '#54815D',
    bgLight: '#EAF2E7',
    borderGlow: '#C6D9C2',
    boxGlow: '0 0 20px rgba(84, 129, 93, 0.22)',
    badgeBg: '#EAF2E7',
    badgeText: '#254B3D',
    badgeBorder: '#C6D9C2',
    lampHex: '#254B3D'
  }
}

export default function PolyhouseIoTMonitor() {
  const [espIp, setEspIp] = useState(DEFAULT_ESP_IP)
  const [isEditingIp, setIsEditingIp] = useState(false)
  const [tempIp, setTempIp] = useState(DEFAULT_ESP_IP)

  const [activeState, setActiveState] = useState('yellow')
  const [rawValue, setRawValue] = useState(512)
  const [status, setStatus] = useState('Optimal Moisture Range')
  const [action, setAction] = useState('Moisture levels optimal. Light misting spray cycle on standby.')
  const [isNodeOnline, setIsNodeOnline] = useState(false)
  const [isBusy, setIsBusy] = useState(false)
  const [lastSync, setLastSync] = useState(null)
  const [errorReason, setErrorReason] = useState('')

  const isMountedRef = useRef(true)

  // Map incoming ESP payload to UI state
  const handleIncomingData = useCallback((data) => {
    const raw = Number(data.rawValue ?? data.moisture ?? data.value ?? data.raw ?? 512)
    setRawValue(raw)

    if (data.status) setStatus(data.status)
    if (data.action) setAction(data.action)

    const led = String(data.ledColor || data.state || '').toUpperCase()
    if (led === 'RED' || led.includes('WET')) {
      setActiveState('wet')
    } else if (led === 'GREEN' || led.includes('DRY')) {
      setActiveState('dry')
    } else if (led === 'YELLOW' || led.includes('MILD')) {
      setActiveState('yellow')
    }

    setLastSync(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    setErrorReason('')
  }, [])

  // Robust Fetch with fallback: Direct -> Backend Proxy (Bypasses browser CORS & Private Network restrictions)
  const fetchLiveData = useCallback(async () => {
    const targetIp = espIp.trim()
    if (!targetIp) return

    // 1. Try Direct fetch first
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

      const response = await fetch(`http://${targetIp}/data`, {
        method: 'GET',
        signal: controller.signal,
        headers: { Accept: 'application/json, text/plain, */*' },
        mode: 'cors'
      })
      clearTimeout(timeoutId)

      if (response.ok) {
        const text = await response.text()
        let data
        try { data = JSON.parse(text) } catch { data = { rawValue: 512, ledColor: 'YELLOW' } }
        if (!isMountedRef.current) return
        handleIncomingData(data)
        setIsNodeOnline(true)
        return
      }
    } catch {
      // Direct fetch failed (often due to browser CORS or different subnet). Try Backend Proxy.
    }

    // 2. Try Backend Proxy fetch (Zero CORS issues)
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS + 200)

      const proxyResp = await fetch(`${API_BASE}/api/iot/polyhouse/data?ip=${encodeURIComponent(targetIp)}`, {
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (proxyResp.ok) {
        const data = await proxyResp.json()
        if (!isMountedRef.current) return
        handleIncomingData(data)
        setIsNodeOnline(true)
        return
      }
    } catch {
      // Both direct and proxy failed
    }

    if (!isMountedRef.current) return
    setIsNodeOnline(false)
    setErrorReason(`Cannot connect to ESP8266 at ${targetIp}. Check that both your computer and ESP8266 are on the same Wi-Fi.`)
  }, [espIp, handleIncomingData])

  // Polling lifecycle hook
  useEffect(() => {
    isMountedRef.current = true
    fetchLiveData()
    const interval = setInterval(fetchLiveData, FETCH_INTERVAL_MS)

    return () => {
      isMountedRef.current = false
      clearInterval(interval)
    }
  }, [fetchLiveData])

  // Command Function: Set State with optimistic UI + Proxy fallback
  const setHardwareState = async (stateKey) => {
    const profile = HARDWARE_PROFILES[stateKey]
    if (!profile) return

    setIsBusy(true)

    // Optimistic UI updates so demonstrations work instantly
    setActiveState(stateKey)
    setRawValue(profile.defaultRaw)
    setStatus(profile.defaultStatus)
    setAction(profile.defaultAction)
    setLastSync(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))

    const targetIp = espIp.trim()

    // 1. Try Direct
    let success = false
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)
      const resp = await fetch(`http://${targetIp}/set-state?state=${stateKey}`, {
        method: 'GET',
        signal: controller.signal,
        mode: 'cors'
      })
      clearTimeout(timeoutId)
      if (resp.ok) success = true
    } catch {
      // Try proxy
    }

    // 2. Try Proxy
    if (!success) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS + 200)
        const proxyResp = await fetch(
          `${API_BASE}/api/iot/polyhouse/set-state?state=${stateKey}&ip=${encodeURIComponent(targetIp)}`,
          { signal: controller.signal }
        )
        clearTimeout(timeoutId)
        if (proxyResp.ok) success = true
      } catch {
        success = false
      }
    }

    if (isMountedRef.current) {
      setIsNodeOnline(success)
      setIsBusy(false)
      if (success) {
        setTimeout(fetchLiveData, 250)
      }
    }
  }

  const handleSaveIp = (e) => {
    e.preventDefault()
    setEspIp(tempIp.trim())
    setIsEditingIp(false)
  }

  const currentProfile = HARDWARE_PROFILES[activeState] || HARDWARE_PROFILES.yellow
  const moisturePct = Math.min(Math.max(Math.round(((rawValue || 0) / 1024) * 100), 5), 100)

  return (
    <section
      style={{
        background: '#FFFFFF',
        color: '#28332D',
        borderRadius: '18px',
        border: '1px solid #DDE3D9',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 8px 24px rgba(37, 75, 61, 0.06)',
        fontFamily: "'DM Sans', 'Inter', system-ui, sans-serif"
      }}
    >
      {/* Top Header / Bar */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
          background: '#F1F4EE',
          padding: '16px 20px',
          borderRadius: '14px',
          border: '1px solid #E8ECE4'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '11px',
              background: '#254B3D',
              border: '1px solid #18372c',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF'
            }}
          >
            <Leaf size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#254B3D', letterSpacing: '-0.02em' }}>
                Polyhouse IoT Ecosystem
              </h2>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  background: '#E3EBDD',
                  color: '#254B3D',
                  border: '1px solid #DDE3D9'
                }}
              >
                v1.0 PoC
              </span>
            </div>
            <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#657167' }}>
              ESP8266 Real-Time Smart Irrigation Controller
            </p>
          </div>
        </div>

        {/* Connection Status & Configurable IP Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {isEditingIp ? (
            <form onSubmit={handleSaveIp} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="text"
                value={tempIp}
                onChange={(e) => setTempIp(e.target.value)}
                placeholder="ESP IP (e.g. 192.168.31.15)"
                style={{
                  padding: '6px 10px',
                  borderRadius: '6px',
                  border: '1px solid #DDE3D9',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  width: '170px'
                }}
              />
              <button
                type="submit"
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  background: '#254B3D',
                  color: '#FFFFFF',
                  border: 'none',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Set IP
              </button>
            </form>
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                background: '#FFFFFF',
                padding: '7px 14px',
                borderRadius: '999px',
                border: '1px solid #DDE3D9',
                boxShadow: '0 2px 6px rgba(37, 75, 61, 0.04)'
              }}
            >
              <span style={{ position: 'relative', display: 'flex', width: '9px', height: '9px' }}>
                <span
                  style={{
                    position: 'absolute',
                    width: '100%',
                    height: '100%',
                    borderRadius: '999px',
                    background: isNodeOnline ? '#54815D' : '#C58A35',
                    opacity: 0.75
                  }}
                />
                <span
                  style={{
                    position: 'relative',
                    display: 'inline-flex',
                    width: '9px',
                    height: '9px',
                    borderRadius: '999px',
                    background: isNodeOnline ? '#254B3D' : '#C58A35'
                  }}
                />
              </span>
              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: isNodeOnline ? '#254B3D' : '#C58A35' }}>
                  {isNodeOnline ? 'Node Online' : 'Presentation Mode'}
                </div>
                <div style={{ fontSize: '10px', color: '#657167', fontFamily: 'monospace' }}>
                  {espIp}
                </div>
              </div>
              <button
                type="button"
                onClick={() => { setTempIp(espIp); setIsEditingIp(true) }}
                title="Change ESP8266 IP address"
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#657167',
                  padding: '2px',
                  cursor: 'pointer',
                  display: 'flex'
                }}
              >
                <Edit2 size={12} />
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={fetchLiveData}
            title="Poll ESP8266 now"
            style={{
              background: '#FFFFFF',
              border: '1px solid #DDE3D9',
              borderRadius: '8px',
              color: '#254B3D',
              padding: '7px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            <RefreshCw size={12} className={isBusy ? 'animate-spin' : ''} />
            <span>Poll Node</span>
          </button>
        </div>
      </header>

      {/* Network Alert Helper (Shown when offline to guide Wi-Fi alignment) */}
      {!isNodeOnline && (
        <div
          style={{
            marginTop: '16px',
            background: '#FFF4DD',
            border: '1px solid #E9D09A',
            borderRadius: '12px',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
            fontSize: '12px',
            color: '#78350f'
          }}
        >
          <Info size={16} color="#C58A35" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Interactive Presentation Fallback Active:</strong>
            <div style={{ marginTop: '2px', color: '#92400e' }}>
              The dashboard cannot reach <code>http://{espIp}/data</code>. If your computer is connected to your home Wi-Fi (e.g. JioFiber) and your ESP8266 is on a phone hotspot, please connect <strong>both devices to the exact same Wi-Fi network</strong>. You can click the pencil icon above to update the IP address.
            </div>
          </div>
        </div>
      )}

      {/* 3 Main Live Telemetry Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '16px',
          marginTop: '18px'
        }}
      >
        {/* Card 1: Moisture Sensor Output */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '20px',
            border: '1px solid #DDE3D9',
            boxShadow: '0 4px 12px rgba(37, 75, 61, 0.04)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#657167' }}>
              Moisture Sensor Output
            </span>
            <div style={{ padding: '6px 8px', borderRadius: '8px', background: '#EAF2E7', color: '#54815D' }}>
              <Droplet size={16} />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
            <span style={{ fontSize: '38px', fontWeight: 800, color: '#254B3D', letterSpacing: '-0.03em', lineHeight: 1 }}>
              {rawValue ?? '--'}
            </span>
            <span style={{ fontSize: '12px', color: '#657167', fontWeight: 600 }}>/ 1024 ADC</span>
          </div>
          <div style={{ width: '100%', background: '#E8ECE4', height: '8px', borderRadius: '999px', marginTop: '16px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${moisturePct}%`,
                background: '#54815D',
                height: '100%',
                borderRadius: '999px',
                transition: 'width 0.5s ease'
              }}
            />
          </div>
          <p style={{ margin: '10px 0 0', fontSize: '11px', color: '#657167' }}>Capacitive probe reading stream</p>
        </div>

        {/* Card 2: Soil State Condition */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '20px',
            border: '1px solid #DDE3D9',
            boxShadow: '0 4px 12px rgba(37, 75, 61, 0.04)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#657167' }}>
              Soil State Condition
            </span>
            <div style={{ padding: '6px 8px', borderRadius: '8px', background: currentProfile.bgLight, color: currentProfile.colorHex }}>
              <Leaf size={16} />
            </div>
          </div>
          <div style={{ marginTop: '4px' }}>
            <span style={{ fontSize: '20px', fontWeight: 700, color: currentProfile.colorHex }}>
              {status}
            </span>
          </div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              background: currentProfile.badgeBg,
              color: currentProfile.badgeText,
              border: `1px solid ${currentProfile.badgeBorder}`,
              marginTop: '16px'
            }}
          >
            {currentProfile.badge}
          </div>
        </div>

        {/* Card 3: Hardware Traffic Light */}
        <div
          style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '20px',
            border: `1px solid ${currentProfile.borderGlow}`,
            boxShadow: currentProfile.boxGlow,
            transition: 'all 0.3s ease'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#657167' }}>
              Hardware Traffic Light
            </span>
            <div style={{ padding: '6px 8px', borderRadius: '8px', background: '#F1F4EE', color: '#254B3D' }}>
              <Radio size={16} />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
            <div
              style={{
                width: '22px',
                height: '22px',
                borderRadius: '999px',
                background: currentProfile.lampHex,
                boxShadow: `0 0 14px ${currentProfile.lampHex}`
              }}
            />
            <span style={{ fontSize: '22px', fontWeight: 800, color: currentProfile.colorHex }}>
              {currentProfile.ledColor}
            </span>
          </div>
          <p style={{ margin: '18px 0 0', fontSize: '11px', color: '#657167' }}>
            Active Pin: <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#28332D' }}>{currentProfile.pin}</span>
          </p>
        </div>
      </div>

      {/* Action Plan Box */}
      <div
        style={{
          marginTop: '16px',
          background: '#F1F4EE',
          padding: '18px 22px',
          borderRadius: '14px',
          border: '1px solid #DDE3D9',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: '#E3EBDD',
              border: '1px solid #DDE3D9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#254B3D',
              flexShrink: 0
            }}
          >
            <Bot size={20} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#657167' }}>
              Polyhouse System Action Plan
            </h3>
            <p style={{ margin: '3px 0 0', fontSize: '14px', fontWeight: 700, color: '#28332D' }}>
              {action}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#657167', fontWeight: 500 }}>Auto Irrigation:</span>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '3px 9px',
              borderRadius: '999px',
              background: '#EAF2E7',
              color: '#254B3D',
              border: '1px solid #C6D9C2'
            }}
          >
            ENABLED
          </span>
        </div>
      </div>

      {/* Hardware Threshold & Status Reference Cards (Read-only, no click-to-change) */}
      <div
        style={{
          marginTop: '20px',
          background: '#F7F5EE',
          padding: '22px',
          borderRadius: '16px',
          border: '1px solid #DDE3D9',
          boxShadow: '0 4px 14px rgba(37, 75, 61, 0.04)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '18px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#254B3D', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={17} color="#54815D" />
              Hardware Automation Thresholds & State Indicators
            </h3>
            <p style={{ margin: '3px 0 0', fontSize: '12px', color: '#657167' }}>
              Active state is managed autonomously by the ESP8266 sensor readings.
            </p>
          </div>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'monospace',
              fontWeight: 600,
              padding: '4px 9px',
              borderRadius: '6px',
              background: '#FFFFFF',
              color: '#254B3D',
              border: '1px solid #DDE3D9'
            }}
          >
            Telemetry Linked
          </span>
        </div>

        {/* 3 Read-Only Status Indicator Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
          {/* Card 1: High Moisture / Rain */}
          <div
            style={{
              background: activeState === 'wet' ? '#FCECE8' : '#FFFFFF',
              border: `2px solid ${activeState === 'wet' ? '#B94E3D' : '#DDE3D9'}`,
              borderRadius: '12px',
              padding: '16px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              cursor: 'default',
              userSelect: 'none',
              boxShadow: activeState === 'wet' ? '0 4px 12px rgba(185, 78, 61, 0.15)' : 'none',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '10px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#B94E3D' }}>
                High Moisture / Rain
              </span>
              <span style={{ width: '10px', height: '10px', borderRadius: '999px', background: '#B94E3D', opacity: activeState === 'wet' ? 1 : 0.4 }} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#28332D' }}>🌧️ Rain / Saturated</div>
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#657167', lineHeight: 1.4 }}>
                Triggers Red LED (D5) & halts all irrigation pumps.
              </p>
            </div>
            <div style={{ fontSize: '10px', color: activeState === 'wet' ? '#B94E3D' : '#657167', fontWeight: 600, marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '999px', background: activeState === 'wet' ? '#B94E3D' : '#DDE3D9' }} />
              <span>{activeState === 'wet' ? 'CURRENT ACTIVE STATE' : 'Hardware Pin D5 (GPIO14)'}</span>
            </div>
          </div>

          {/* Card 2: Mild Moisture */}
          <div
            style={{
              background: activeState === 'yellow' ? '#FFF4DD' : '#FFFFFF',
              border: `2px solid ${activeState === 'yellow' ? '#C58A35' : '#DDE3D9'}`,
              borderRadius: '12px',
              padding: '16px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              cursor: 'default',
              userSelect: 'none',
              boxShadow: activeState === 'yellow' ? '0 4px 12px rgba(197, 138, 53, 0.15)' : 'none',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '10px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#C58A35' }}>
                Mild Moisture
              </span>
              <span style={{ width: '10px', height: '10px', borderRadius: '999px', background: '#C58A35', opacity: activeState === 'yellow' ? 1 : 0.4 }} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#28332D' }}>⛅ Optimal / Mild</div>
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#657167', lineHeight: 1.4 }}>
                Triggers Yellow LED (D6) for light misting spray.
              </p>
            </div>
            <div style={{ fontSize: '10px', color: activeState === 'yellow' ? '#C58A35' : '#657167', fontWeight: 600, marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '999px', background: activeState === 'yellow' ? '#C58A35' : '#DDE3D9' }} />
              <span>{activeState === 'yellow' ? 'CURRENT ACTIVE STATE' : 'Hardware Pin D6 (GPIO12)'}</span>
            </div>
          </div>

          {/* Card 3: Dry Soil */}
          <div
            style={{
              background: activeState === 'dry' ? '#EAF2E7' : '#FFFFFF',
              border: `2px solid ${activeState === 'dry' ? '#54815D' : '#DDE3D9'}`,
              borderRadius: '12px',
              padding: '16px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              cursor: 'default',
              userSelect: 'none',
              boxShadow: activeState === 'dry' ? '0 4px 12px rgba(84, 129, 93, 0.15)' : 'none',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '10px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#54815D' }}>
                Dry Soil
              </span>
              <span style={{ width: '10px', height: '10px', borderRadius: '999px', background: '#54815D', opacity: activeState === 'dry' ? 1 : 0.4 }} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#28332D' }}>☀️ Dry / Water Needed</div>
              <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#657167', lineHeight: 1.4 }}>
                Triggers Green LED (D7) to initiate full watering.
              </p>
            </div>
            <div style={{ fontSize: '10px', color: activeState === 'dry' ? '#54815D' : '#657167', fontWeight: 600, marginTop: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '999px', background: activeState === 'dry' ? '#54815D' : '#DDE3D9' }} />
              <span>{activeState === 'dry' ? 'CURRENT ACTIVE STATE' : 'Hardware Pin D7 (GPIO13)'}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
