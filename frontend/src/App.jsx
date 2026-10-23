import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle, BarChart3, Bell, CheckCircle2, ChevronRight, CircleHelp, CloudOff,
  Droplets, FlaskConical, History, Leaf, Languages, LockKeyhole, Mic, Pause, Radio,
  RefreshCw, Send, Settings2, ShieldCheck, Sprout, Thermometer, UserCircle2, Volume2
} from 'lucide-react'
import {
  checkHealth, evaluateScenario, getScenarios, sendAssistantMessage,
  synthesizeVoice, transcribeVoice
} from './api'
import { authConfigured, signOut, subscribeAuth } from './auth'
import CropTab from './components/CropTab'
import DiseaseTab from './components/DiseaseTab'
import AuthPanel from './components/AuthPanel'
import PolyhouseIoTMonitor from './components/PolyhouseIoTMonitor'

const LANGUAGES = [
  { code: 'hi-IN', label: 'हिन्दी', short: 'Hindi' },
  { code: 'en-IN', label: 'English', short: 'English' },
  { code: 'pa-IN', label: 'ਪੰਜਾਬੀ', short: 'Punjabi' },
  { code: 'bn-IN', label: 'বাংলা', short: 'Bengali' },
  { code: 'mr-IN', label: 'मराठी', short: 'Marathi' }
]

const NAV = [
  { id: 'dashboard', label: 'Farm dashboard', icon: Sprout },
  { id: 'climate', label: 'Climate & moisture', icon: BarChart3 },
  { id: 'assistant', label: 'Ask JalSaathi', icon: Mic },
  { id: 'profile', label: 'Crop profile', icon: Leaf },
  { id: 'alerts', label: 'Alerts & recommendations', icon: Bell },
  { id: 'history', label: 'History & insights', icon: History },
  { id: 'scenarios', label: 'Scenario lab', icon: FlaskConical },
  { id: 'tools', label: 'Plant tools', icon: ShieldCheck },
  { id: 'settings', label: 'Settings & integrations', icon: Settings2 }
]

const MOBILE_NAV = ['dashboard', 'climate', 'assistant', 'alerts', 'profile']

const STATUS_COPY = {
  normal: { label: 'Normal', tone: 'good' },
  low_temperature: { label: 'Low temperature', tone: 'warn' },
  high_temperature: { label: 'High temperature', tone: 'danger' },
  low_moisture: { label: 'Low moisture', tone: 'warn' },
  high_moisture: { label: 'High moisture', tone: 'warn' }
}

function StatusPill({ status }) {
  const copy = STATUS_COPY[status] || { label: status || 'Unavailable', tone: 'neutral' }
  return <span className={`status-pill ${copy.tone}`}><span className="status-dot" />{copy.label}</span>
}

function SourceBadge({ simulated = false }) {
  return simulated
    ? <span className="source-badge simulated"><FlaskConical size={13} /> Simulated test fixture</span>
    : <span className="source-badge unavailable"><CloudOff size={13} /> No live source</span>
}

function EmptyState({ icon: Icon = CircleHelp, title, children, action }) {
  return <div className="empty-state"><Icon size={25} /><div><strong>{title}</strong><p>{children}</p>{action}</div></div>
}

function PageHeader({ eyebrow, title, description, action }) {
  return <div className="page-header"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>
}

function MetricCard({ icon: Icon, label, value, meta, status, unavailable = false }) {
  return <article className={`metric-card ${unavailable ? 'is-unavailable' : ''}`}><div className="metric-top"><span>{label}</span><Icon size={19} /></div><strong>{value}</strong>{status ? <StatusPill status={status} /> : <span className="metric-meta">{meta}</span>}<small>{unavailable ? 'Unavailable until a verified source is connected' : meta}</small></article>
}

function App() {
  const [view, setView] = useState('dashboard')
  const [health, setHealth] = useState(null)
  const [user, setUser] = useState(null)
  const [authReady, setAuthReady] = useState(false)
  const [scenarioPack, setScenarioPack] = useState(null)
  const [selectedId, setSelectedId] = useState('')
  const [reading, setReading] = useState(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [scenarioError, setScenarioError] = useState('')
  const [scenarioFilter, setScenarioFilter] = useState('all')
  const [language, setLanguage] = useState('hi-IN')
  const [profile, setProfile] = useState({ crop: '', variety: '', growthStage: '', soil: '', environment: 'Open field' })
  const [profileSaved, setProfileSaved] = useState(false)
  const [messages, setMessages] = useState([])
  const [assistantInput, setAssistantInput] = useState('')
  const [transcript, setTranscript] = useState('')
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [voiceError, setVoiceError] = useState('')
  const [recording, setRecording] = useState(false)
  const [speechEnabled, setSpeechEnabled] = useState(true)
  const [audioUrl, setAudioUrl] = useState('')
  const mediaRecorder = useRef(null)
  const audioChunks = useRef([])

  const cropName = profile.crop
  const growthStage = profile.growthStage
  const activeNav = NAV.find(item => item.id === view) || NAV[0]
  const filteredScenarios = useMemo(() => {
    const scenarios = scenarioPack?.scenarios || []
    if (scenarioFilter === 'all') return scenarios
    return scenarios.filter(item => item.expected?.temperature === scenarioFilter || item.expected?.moisture === scenarioFilter)
  }, [scenarioPack, scenarioFilter])

  const navigate = (nextView) => {
    setView(nextView)
    window.scrollTo?.({ top: 0, behavior: 'smooth' })
  }

  const refresh = async () => {
    const [healthResult, scenariosResult] = await Promise.all([
      checkHealth(),
      getScenarios().catch(error => ({ available: false, scenarios: [], message: error.message }))
    ])
    setHealth(healthResult)
    setScenarioPack(scenariosResult)
    setScenarioError(scenariosResult.available ? '' : scenariosResult.message || 'Scenario lab unavailable.')
  }

  useEffect(() => { refresh() }, [])
  useEffect(() => subscribeAuth(session => { setUser(session?.user || null); setAuthReady(true) }), [])

  const chooseScenario = async (id) => {
    setSelectedId(id)
    setScenarioLoading(true)
    setScenarioError('')
    try { setReading(await evaluateScenario(id)) }
    catch (error) { setScenarioError(error.message); setReading(null) }
    finally { setScenarioLoading(false) }
  }

  const applyScenarioOverride = async (field, value) => {
    if (!reading || value === '') return
    const next = { temperature_c: reading.temperature_c, moisture_percent: reading.soil_moisture_percent }
    if (field === 'temperature') next.temperature_c = value
    if (field === 'moisture') next.moisture_percent = value
    setScenarioLoading(true)
    try { setReading(await evaluateScenario(reading.scenario_id, next.temperature_c, next.moisture_percent)) }
    catch (error) { setScenarioError(error.message) }
    finally { setScenarioLoading(false) }
  }

  const startRecording = async () => {
    setVoiceError('')
    setTranscript('')
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setVoiceError('Microphone recording is not available in this browser. You can type instead.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      audioChunks.current = []
      recorder.ondataavailable = event => event.data.size && audioChunks.current.push(event.data)
      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop())
        const blob = new Blob(audioChunks.current, { type: recorder.mimeType || 'audio/webm' })
        setAssistantLoading(true)
        try {
          const result = await transcribeVoice(blob, language)
          setTranscript(result.transcript)
          setAssistantInput(result.transcript)
        } catch (error) { setVoiceError(error.message) }
        finally { setAssistantLoading(false) }
      }
      mediaRecorder.current = recorder
      recorder.start()
      setRecording(true)
    } catch (error) { setVoiceError(`Microphone permission failed: ${error.message}`) }
  }

  const stopRecording = () => {
    if (mediaRecorder.current?.state === 'recording') {
      mediaRecorder.current.stop()
      setRecording(false)
    }
  }

  const submitAssistant = async (event) => {
    event?.preventDefault()
    const text = assistantInput.trim()
    if (!text || assistantLoading) return
    setVoiceError('')
    setAudioUrl('')
    const userMessage = { role: 'user', content: text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
    const nextMessages = [...messages, userMessage]
    setMessages(nextMessages)
    setAssistantInput('')
    setTranscript('')
    setAssistantLoading(true)
    const context = reading
      ? { scenario: { ...reading, disclosure: 'SIMULATED — NOT ESP32 DATA' }, crop: cropName || null, growth_stage: growthStage || null }
      : { sensor_state: 'unavailable — no scenario selected and no ESP32 connected', crop: cropName || null, growth_stage: growthStage || null }
    try {
      const result = await sendAssistantMessage(text, messages.map(({ role, content }) => ({ role, content })), context, language)
      const assistantMessage = { role: 'assistant', content: result.reply, provider: result.provider, language_code: result.language_code, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
      setMessages([...nextMessages, assistantMessage])
      if (speechEnabled) {
        try { setAudioUrl(await synthesizeVoice(result.reply, language)) }
        catch (error) { setVoiceError(`Text answer is available, but speech is unavailable: ${error.message}`) }
      }
    } catch (error) { setVoiceError(`${error.category || 'assistant_error'}: ${error.message}`) }
    finally { setAssistantLoading(false) }
  }

  const renderDashboard = () => (
    <>
      <section className="dashboard-hero"><div className="hero-copy"><span className="eyebrow">FIELD JOURNAL · JALSAATHI</span><h2>Make the next farm decision with confidence.</h2><p>Simple climate signals, source labels and a voice-first assistant for everyday crop care.</p><div className="hero-actions"><button className="primary-button light-button" onClick={() => navigate('assistant')}><Mic size={18} /> Ask by voice</button><button className="hero-link" onClick={() => navigate('profile')}>Set up crop profile <ChevronRight size={16} /></button></div></div><div className="hero-photo" role="img" aria-label="Healthy crop rows at dawn" /></section>
      <div className="trust-strip"><span className="connection-mark"><span className="live-dot" /> {health?.status === 'ok' ? 'Service reachable' : 'Checking service'}</span><span><strong>Advisory only.</strong> ESP32 ingestion and actuator control are planned, not connected.</span><button className="text-button" onClick={() => navigate('settings')}>View integrations <ChevronRight size={15} /></button></div>
      <section className="section-heading"><div><span className="eyebrow">TODAY AT A GLANCE</span><h3>{cropName || 'Your farm profile is not set up'}</h3><p>{cropName ? `${profile.variety || 'Variety not recorded'} · ${growthStage || 'Growth stage not recorded'} · ${profile.environment}` : 'Add crop and growing context before asking for crop-specific guidance.'}</p></div>{reading ? <SourceBadge simulated /> : <SourceBadge />}</section>
      <div className="metric-grid"><MetricCard icon={Thermometer} label="Temperature" value={reading ? `${reading.temperature_c.toFixed(1)}°C` : 'Unavailable'} status={reading?.temperature_status} meta="Test fixture reading" unavailable={!reading} /><MetricCard icon={Droplets} label="Soil moisture" value={reading ? `${reading.soil_moisture_percent.toFixed(0)}%` : 'Unavailable'} status={reading?.moisture_status} meta="Normalized test display" unavailable={!reading} /><article className="next-action-card"><span className="eyebrow">RECOMMENDED NEXT ACTION</span><strong>{reading?.alerts?.length ? 'Review the simulated alert' : 'Connect a verified data source'}</strong><p>{reading?.alerts?.length ? 'Open Climate & moisture to understand the deterministic test result. It is not a crop prescription.' : 'Choose a fixture in Scenario Lab for software testing, or connect a real ESP32 integration in a future release.'}</p><button className="text-button" onClick={() => navigate(reading?.alerts?.length ? 'alerts' : 'scenarios')}>{reading?.alerts?.length ? 'Review alerts' : 'Open Scenario Lab'} <ChevronRight size={15} /></button></article></div>
      {reading?.alerts?.length ? <div className="alert-banner critical"><AlertTriangle size={19} /><div><strong>Simulated fixture alerts</strong><p>{reading.alerts.map(item => STATUS_COPY[item]?.label).join(' · ')}. No live field action is being recommended.</p></div><button className="text-button" onClick={() => navigate('alerts')}>Details</button></div> : <div className="alert-banner neutral"><CloudOff size={19} /><div><strong>No live alerts</strong><p>Live alerts will appear only after a verified sensor source is connected.</p></div></div>}
      <PolyhouseIoTMonitor />
      <div className="dashboard-columns"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">ASSISTANT</span><h3>Have a question from the field?</h3></div><Mic size={20} /></div><p className="panel-copy">Speak naturally in Hindi, English, Punjabi, Bengali or Marathi. Review the real transcript before sending it to JalSaathi.</p><button className="primary-button" onClick={() => navigate('assistant')}>Open voice assistant <ChevronRight size={16} /></button></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">DATA DISCIPLINE</span><h3>What JalSaathi knows</h3></div><ShieldCheck size={20} /></div><ul className="trust-list"><li><CheckCircle2 size={16} /> Test values are always labelled simulated.</li><li><CheckCircle2 size={16} /> Crop targets need reviewed sources.</li><li><CheckCircle2 size={16} /> Hardware control is disabled.</li></ul></section></div>
    </>
  )

  const renderClimate = () => (
    <section className="page-section"><PageHeader eyebrow="MONITORING" title="Climate & moisture" description="Understand readings, thresholds and trends without confusing software tests for field measurements." action={reading && <SourceBadge simulated />} />
      {reading ? <><div className="disclosure"><FlaskConical size={16} /><span><strong>SIMULATED SCENARIO — NOT ESP32 DATA.</strong> Thresholds below are deterministic test rules, not optimal crop ranges.</span></div><div className="metric-grid compact-grid"><MetricCard icon={Thermometer} label="Air temperature" value={`${reading.temperature_c.toFixed(1)}°C`} status={reading.temperature_status} meta="Fixture value" /><MetricCard icon={Droplets} label="Soil moisture" value={`${reading.soil_moisture_percent.toFixed(0)}%`} status={reading.moisture_status} meta="Normalized fixture value" /></div><div className="two-column"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">RULE EXPLANATION</span><h3>{reading.label}</h3></div></div><div className="range-list"><div><span>Temperature test rule</span><strong>{reading.thresholds.temperature.lowC}–{reading.thresholds.temperature.highC}°C = normal</strong></div><div><span>Moisture test rule</span><strong>{reading.thresholds.moisture.lowPercent}–{reading.thresholds.moisture.highPercent}% = normal</strong></div></div><p className="fine-print">{reading.thresholds_label}. The values are not agronomic recommendations.</p></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">TARGET RANGE</span><h3>Not configured</h3></div><ShieldCheck size={20} /></div><EmptyState icon={ShieldCheck} title="Verified crop target unavailable">Add a source-backed crop profile, growth stage, units and calibration before displaying field guidance.</EmptyState></section></div></> : <div className="two-column"><section className="panel chart-empty"><div className="panel-heading"><div><span className="eyebrow">LIVE TREND</span><h3>No verified readings yet</h3></div><BarChart3 size={20} /></div><EmptyState icon={CloudOff} title="Trend chart is waiting for data">No real sensor history is connected. JalSaathi will not draw a synthetic trend.</EmptyState></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">SCENARIO COMPARISON</span><h3>Test the rule engine</h3></div><FlaskConical size={20} /></div><p className="panel-copy">Run one of the 20 labelled fixtures to compare expected and observed rule results.</p><button className="primary-button" onClick={() => navigate('scenarios')}>Open Scenario Lab <ChevronRight size={16} /></button></section></div>}
      <section className="panel scenario-comparison"><div className="panel-heading"><div><span className="eyebrow">COMPARISON</span><h3>{reading ? 'Fixture cases around this reading' : 'Scenario comparison'}</h3></div><button className="text-button" onClick={() => navigate('scenarios')}>View all 20 <ChevronRight size={15} /></button></div>{scenarioPack?.scenarios?.slice(0, 5).map(item => <button className="comparison-row" key={item.id} onClick={() => { chooseScenario(item.id); navigate('climate') }}><span><strong>{item.label}</strong><small>{item.cropLabel} · {item.temperatureC}°C · {item.soilMoisturePercent}%</small></span><span className="comparison-status">{item.expected.temperature} · {item.expected.moisture}</span><ChevronRight size={16} /></button>)}</section>
    </section>
  )

  const renderProfile = () => (
    <section className="page-section"><PageHeader eyebrow="FARM CONTEXT" title="Crop profile" description="Keep the farmer’s context visible. Saving here is local to this browser until database persistence is connected." />
      <form className="panel profile-form" onSubmit={event => { event.preventDefault(); setProfileSaved(true) }}><div className="form-intro"><Leaf size={22} /><div><strong>About this plot</strong><p>These details help frame future conversations; they do not create crop thresholds.</p></div></div><label>Crop name<input value={profile.crop} onChange={event => setProfile({ ...profile, crop: event.target.value })} placeholder="e.g. Tomato" /></label><label>Variety, if known<input value={profile.variety} onChange={event => setProfile({ ...profile, variety: event.target.value })} placeholder="Optional" /></label><label>Growth stage<select value={profile.growthStage} onChange={event => setProfile({ ...profile, growthStage: event.target.value })}><option value="">Select stage</option><option>Seedling</option><option>Vegetative</option><option>Flowering</option><option>Fruit development</option><option>Harvest</option></select></label><label>Soil type<select value={profile.soil} onChange={event => setProfile({ ...profile, soil: event.target.value })}><option value="">Not recorded</option><option>Loamy</option><option>Sandy</option><option>Clay</option><option>Silty</option><option>Other</option></select></label><label>Growing environment<select value={profile.environment} onChange={event => setProfile({ ...profile, environment: event.target.value })}><option>Open field</option><option>Polyhouse</option><option>Other protected cultivation</option></select></label><div className="source-panel"><ShieldCheck size={20} /><div><strong>Crop-specific thresholds are not configured</strong><p>Source, publication date, growth stage, units and reviewer approval will be required before any target range appears.</p></div></div><div className="form-footer"><button className="primary-button"><CheckCircle2 size={16} /> Save local profile</button>{profileSaved && <span className="saved-note"><CheckCircle2 size={15} /> Saved in this session</span>}</div></form>
    </section>
  )

  const renderAlerts = () => (
    <section className="page-section"><PageHeader eyebrow="DECISION SUPPORT" title="Alerts & recommendations" description="Review why a rule fired and what the source actually means. No actuator action is performed." action={reading && <SourceBadge simulated />} />
      {reading?.alerts?.length ? <div className="alert-list">{reading.alerts.map(status => <article className={`alert-item ${STATUS_COPY[status]?.tone}`} key={status}><div className="alert-icon"><AlertTriangle size={19} /></div><div className="alert-content"><div className="alert-item-heading"><div><span className="eyebrow">SIMULATED FIXTURE · {reading.scenario_id}</span><h3>{STATUS_COPY[status]?.label}</h3></div><StatusPill status={status} /></div><p>Observed test value: {status.includes('temperature') ? `${reading.temperature_c.toFixed(1)}°C` : `${reading.soil_moisture_percent.toFixed(0)}%`}. The deterministic test rule marked this outside its fixture boundary.</p><div className="alert-meta"><span>Timestamp: not provided by fixture</span><span>Suggested action: review the test case</span></div></div></article>)}</div> : <section className="panel"><EmptyState icon={Bell} title="No verified alerts">Select a simulated scenario to inspect test alerts, or connect a real data source before relying on alerts.</EmptyState></section>}
      <section className="panel recommendation-note"><div className="panel-heading"><div><span className="eyebrow">RECOMMENDATIONS</span><h3>Advice stays qualified</h3></div><ShieldCheck size={20} /></div><p>JalSaathi can explain a verified reading or a labelled test result. It will not claim watering, savings, weather or crop prescriptions without a configured source.</p></section>
    </section>
  )

  const renderHistory = () => (
    <section className="page-section"><PageHeader eyebrow="RECORDS" title="History & insights" description="Real trends, irrigation logs and qualified estimates will appear here after those integrations exist." /><div className="insight-grid"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">ENVIRONMENTAL TRENDS</span><h3>Waiting for real readings</h3></div><BarChart3 size={20} /></div><EmptyState icon={History} title="No historical sensor data">There is no connected ESP32 history to chart. Scenario fixtures are not stored as field history.</EmptyState></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">IRRIGATION LOG</span><h3>No events recorded</h3></div><Droplets size={20} /></div><EmptyState icon={Droplets} title="No verified irrigation events">JalSaathi cannot claim that sprinklers operated until a future actuator integration confirms it.</EmptyState></section><section className="panel full-width"><div className="panel-heading"><div><span className="eyebrow">ESTIMATES</span><h3>Cost and water savings unavailable</h3></div><ShieldCheck size={20} /></div><p className="panel-copy">Estimates require measured water volume, rates, crop context and a reviewed calculation method. No savings are fabricated in this release.</p></section></div></section>
  )

  const renderScenarioLab = () => (
    <section className="page-section"><PageHeader eyebrow="TEST ONLY" title="Scenario Lab" description="Exercise the shared climate rules with exactly 20 temperature/moisture fixtures. Nothing here is live field data." action={<span className="state-label demo"><FlaskConical size={13} /> Simulated only</span>} /><div className="disclosure large"><FlaskConical size={18} /><div><strong>SIMULATED SCENARIO — NOT ESP32 DATA</strong><span>Fixture values and thresholds are software tests, not optimal crop ranges or agronomic advice.</span></div></div>{scenarioError && <div className="error-panel"><AlertTriangle size={18} />{scenarioError}</div>}<div className="scenario-toolbar"><label>Show cases<select value={scenarioFilter} onChange={event => setScenarioFilter(event.target.value)}><option value="all">All 20 fixtures</option><option value="normal">Normal cases</option><option value="low_temperature">Low temperature cases</option><option value="high_temperature">High temperature cases</option><option value="low_moisture">Low moisture cases</option><option value="high_moisture">High moisture cases</option></select></label><span className="scenario-count">{filteredScenarios.length} of 20 cases</span></div><div className="scenario-layout"><div className="scenario-list">{filteredScenarios.map(item => <button key={item.id} className={`scenario-row ${selectedId === item.id ? 'selected' : ''}`} onClick={() => chooseScenario(item.id)}><span><strong>{item.label}</strong><small>{item.cropLabel} · {item.temperatureC}°C · {item.soilMoisturePercent}%</small></span><ChevronRight size={17} /></button>)}</div><div className="scenario-detail panel">{reading ? <><div className="detail-top"><div><span className="eyebrow">{reading.scenario_id} · OBSERVED RESULT</span><h3>{reading.crop_label} fixture</h3></div>{scenarioLoading && <span className="loading-label">Running…</span>}</div><SourceBadge simulated /><div className="metric-edit"><label>Simulated air temperature<input type="number" value={reading.temperature_c} onChange={event => applyScenarioOverride('temperature', event.target.value)} />°C</label><label>Normalized moisture display<input type="number" value={reading.soil_moisture_percent} onChange={event => applyScenarioOverride('moisture', event.target.value)} />%</label></div><div className="expected-observed"><div><span>Expected temperature</span><strong>{reading.expected.temperature}</strong></div><div><span>Observed temperature</span><StatusPill status={reading.temperature_status} /></div><div><span>Expected moisture</span><strong>{reading.expected.moisture}</strong></div><div><span>Observed moisture</span><StatusPill status={reading.moisture_status} /></div></div><p className="fine-print">Manual overrides change only simulated inputs and deterministic test statuses. They are never presented as live readings.</p></> : <EmptyState icon={FlaskConical} title="Choose a scenario">The lab does not auto-select a case. Use a fixture to exercise the shared rules engine.</EmptyState>}</div></div></section>
  )

  const renderAssistant = () => (
    <section className="page-section assistant-page">{!authReady ? <EmptyState icon={LockKeyhole} title="Checking sign-in status">Checking the Supabase session.</EmptyState> : (!authConfigured || !user) ? <AuthPanel onAuthenticated={session => setUser(session?.user || null)} /> : <><PageHeader eyebrow="LIVE PROVIDERS ONLY" title="Ask JalSaathi" description="Select a language, speak naturally, review the real transcript, then send it to the live assistant." action={<div className="language-control"><Languages size={17} /><select value={language} onChange={event => setLanguage(event.target.value)}>{LANGUAGES.map(item => <option key={item.code} value={item.code}>{item.label} · {item.short}</option>)}</select></div>} /><div className="provider-flow"><span className="flow-step active">1 · Microphone</span><ChevronRight size={14} /><span className="flow-step">2 · Gnani STT</span><ChevronRight size={14} /><span className="flow-step">3 · OpenRouter</span><ChevronRight size={14} /><span className="flow-step">4 · Gnani TTS</span></div><div className="assistant-context">{reading ? <><FlaskConical size={16} /> Context includes a simulated scenario. The assistant must identify it as simulated.</> : <><CloudOff size={16} /> No scenario selected. Current sensor readings are unavailable.</>}</div><div className="chat-panel panel"><div className="chat-messages">{messages.length === 0 && <EmptyState icon={Mic} title="Your conversation starts here">Ask a farming question, or record a short voice message. Responses and audio are returned only from configured providers.</EmptyState>}{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}><span className="chat-role">{message.role === 'user' ? 'You' : 'JalSaathi'}</span><p>{message.content}</p>{message.provider && <small>Live response · {message.provider} · {message.language_code || language}</small>}</div>)}{assistantLoading && <div className="chat-message assistant"><span className="chat-role">JalSaathi</span><p className="loading-dots">Contacting configured provider…</p></div>}</div>{voiceError && <div className="error-panel compact"><AlertTriangle size={17} />{voiceError}</div>}{transcript && <div className="transcript-review"><div><strong>Actual transcript — review before sending</strong><span>Gnani STT output · {language}</span></div><textarea value={transcript} onChange={event => { setTranscript(event.target.value); setAssistantInput(event.target.value) }} /></div>}{audioUrl && <div className="audio-result"><Volume2 size={17} /><span>Actual Gnani TTS response</span><audio controls autoPlay src={audioUrl} /></div>}<form className="assistant-composer" onSubmit={submitAssistant}><button type="button" className={`voice-button ${recording ? 'recording' : ''}`} onClick={recording ? stopRecording : startRecording} aria-label={recording ? 'Stop recording' : 'Start recording'}>{recording ? <Pause size={21} /> : <Mic size={21} />}</button><input value={assistantInput} onChange={event => setAssistantInput(event.target.value)} placeholder="Type a farming question…" /><label className="speech-toggle"><input type="checkbox" checked={speechEnabled} onChange={event => setSpeechEnabled(event.target.checked)} /><Volume2 size={16} /> Speak answer</label><button className="primary-button send-button" disabled={assistantLoading || !assistantInput.trim()}><Send size={17} /> Send</button></form></div></>}</section>
  )

  const renderSettings = () => (
    <section className="page-section"><PageHeader eyebrow="TRUST & CONNECTIONS" title="Settings & integrations" description="Provider status is visible without exposing keys. Configure languages and understand what is connected." action={<button className="icon-button" onClick={refresh} aria-label="Refresh status"><RefreshCw size={18} /></button>} /><div className="settings-grid"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">LANGUAGE</span><h3>Assistant language</h3></div><Languages size={20} /></div><label>Default conversation language<select value={language} onChange={event => setLanguage(event.target.value)}>{LANGUAGES.map(item => <option key={item.code} value={item.code}>{item.label} · {item.short}</option>)}</select></label><p className="fine-print">The same selected locale is passed through STT, the OpenRouter prompt and TTS.</p></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">PROVIDERS</span><h3>Connection status</h3></div><Radio size={20} /></div><div className="provider-list">{[['LLM · OpenRouter', health?.providers?.llm], ['STT · Gnani', health?.providers?.stt], ['TTS · Gnani', health?.providers?.tts], ['Auth · Supabase', health?.auth]].map(([label, item]) => <div className="provider-row" key={label}><span><strong>{label}</strong><small>{item?.provider || 'checking'}</small></span><span className={`state-label ${item?.configured ? 'good' : 'neutral'}`}>{item?.configured ? 'Configured' : 'Not configured'}</span></div>)}</div></section></div><div className="device-card panel"><Radio size={22} /><div><span className="eyebrow">HARDWARE</span><strong>ESP32 integration planned — not connected</strong><p>Live device ingestion and actuator controls are intentionally disabled. No sprinkler operation is claimed.</p></div></div><div className="integration-note"><strong>Server-side credentials</strong><code>OPENROUTER_API_KEY · OPENROUTER_MODEL · GNANI_STT_API_KEY_ID · GNANI_TTS_API_KEY</code><span>Keys remain on the backend. The browser only receives status.</span></div>{user && <button className="text-button signout-button" onClick={() => signOut()}>Sign out of {user.email}</button>}</section>
  )

  const renderTools = () => <section className="page-section"><PageHeader eyebrow="EXISTING AGRICULTURE TOOLS" title="Plant tools" description="The original crop recommendation and leaf diagnosis workflows remain available while JalSaathi grows around them." /><div className="legacy-tools"><CropTab onAskChatbot={() => navigate('assistant')} /><DiseaseTab onAskChatbot={() => navigate('assistant')} /></div></section>
  const renderView = () => ({ dashboard: renderDashboard, climate: renderClimate, assistant: renderAssistant, profile: renderProfile, alerts: renderAlerts, history: renderHistory, scenarios: renderScenarioLab, settings: renderSettings, tools: renderTools }[view] || renderDashboard)()

  return <div className="jalsaathi-app"><aside className="sidebar"><div className="brand-mark"><div className="brand-icon"><Sprout size={22} /></div><div><strong>JalSaathi</strong><span>Farm climate companion</span></div></div><nav aria-label="Primary navigation">{NAV.map(item => { const Icon = item.icon; return <button key={item.id} className={view === item.id ? 'active' : ''} onClick={() => navigate(item.id)}><Icon size={18} /><span>{item.label}</span></button> })}</nav><div className="sidebar-footer"><span className="live-dot" /> <span>{health?.status === 'ok' ? 'API reachable' : 'Checking API'}</span></div></aside><main className="main-content"><header className="topbar"><div><span className="mobile-kicker">JALSAATHI</span><h1>{activeNav.label}</h1></div><div className="topbar-actions"><span className="state-label neutral"><span className="live-dot" /> Advisory only</span>{user ? <button className="user-chip" onClick={() => signOut()} title="Sign out"><UserCircle2 size={15} /> {user.email || 'Signed in'}</button> : <button className="text-button topbar-signin" onClick={() => navigate('assistant')}>Sign in</button>}</div></header>{renderView()}<footer className="footer-note">JalSaathi · Farmer-first climate guidance · simulated values are always labelled · actuator control disabled</footer></main><nav className="mobile-bottom-nav" aria-label="Mobile navigation">{MOBILE_NAV.map(id => { const item = NAV.find(entry => entry.id === id); const Icon = item.icon; return <button key={id} className={view === id ? 'active' : ''} onClick={() => navigate(id)}><Icon size={20} /><span>{item.label.replace('Farm ', '').replace(' & recommendations', '')}</span></button> })}</nav></div>
}

export default App
