import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, AlertTriangle, BookOpen, Brain, Cloud, FileText, Gauge, Network, ShieldCheck, TerminalSquare } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell,
} from 'recharts'

function severityClass(value) {
  if (value === 'high') return 'high'
  if (value === 'medium') return 'medium'
  return 'normal'
}

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').slice(0, 16)
}

function avg(items, path) {
  const values = items.map((item) => path(item)).filter((v) => typeof v === 'number')
  if (!values.length) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
}

function fmt(value, suffix = '', digits = 2) {
  if (value === undefined || value === null || value === '') return '-'
  if (typeof value === 'number') {
    const shown = Number.isInteger(value) ? value.toFixed(0) : value.toFixed(digits)
    return `${shown}${suffix}`
  }
  return `${value}${suffix}`
}

function MetricItem({ label, value }) {
  return (
    <div className="detail-item">
      <div className="kv-label">{label}</div>
      <div className="kv-value">{value}</div>
    </div>
  )
}

function DetailSection({ title, children }) {
  return (
    <div className="card compact-card">
      <h3 className="section-title">{title}</h3>
      <div className="detail-grid">{children}</div>
    </div>
  )
}

function renderCustomerExplanation(explanation) {
  if (!explanation) return <div>-</div>
  if (typeof explanation === 'string') return <div className="small-text">{explanation}</div>

  return (
    <div className="note-block">
      <div className="note-line">
        <strong>Status:</strong> {explanation.status || '-'}
      </div>

      {explanation.key_findings && explanation.key_findings.length > 0 && (
        <>
          <div className="metric-label note-heading">Key Findings</div>
          <ul className="bullet-list">
            {explanation.key_findings.map((finding, idx) => (
              <li key={idx}>{finding}</li>
            ))}
          </ul>
        </>
      )}

      <p className="small-text">{explanation.message || '-'}</p>

      {explanation.next_steps && explanation.next_steps.length > 0 && (
        <>
          <div className="metric-label note-heading">Recommended Next Steps</div>
          <ul className="bullet-list">
            {explanation.next_steps.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function renderEngineerNote(note) {
  if (!note) return <div>-</div>
  if (typeof note === 'string') return <div className="small-text">{note}</div>

  return (
    <div className="note-block">
      <div className="note-line">
        <strong>Status:</strong> {note.status || '-'}
      </div>
      <div className="note-line">
        <strong>Severity:</strong> {note.severity || '-'}
      </div>
      <div className="note-line">
        <strong>Root Cause Analysis:</strong>
      </div>
      <div className="small-text" style={{ marginBottom: 12 }}>{note.root_cause || '-'}</div>

      <div className="metric-label note-heading">Key Technical Observations</div>
      <ul className="bullet-list">
        {(note.key_observations || []).length ? (
          note.key_observations.map((item, idx) => <li key={idx}>{item}</li>)
        ) : (
          <li>No observations provided.</li>
        )}
      </ul>

      <div className="metric-label note-heading">Detailed Diagnosis</div>
      <div className="small-text">{note.diagnosis || '-'}</div>

      <div className="metric-label note-heading">Recommended Technical Actions</div>
      <ul className="bullet-list">
        {(note.recommended_next_steps || []).length ? (
          note.recommended_next_steps.map((item, idx) => <li key={idx}>{item}</li>)
        ) : (
          <li>No next steps provided.</li>
        )}
      </ul>

      <div className="metric-label note-heading">Data Collection for Future Issues</div>
      <ul className="bullet-list">
        {(note.data_to_collect_if_issue_repeats || []).length ? (
          note.data_to_collect_if_issue_repeats.map((item, idx) => <li key={idx}>{item}</li>)
        ) : (
          <li>AP/router logs, nearby AP scan, channel utilization, and repeat measurements.</li>
        )}
      </ul>
    </div>
  )
}

function RawLogs({ selected }) {
  const raw = selected?.raw_outputs || {}
  const keys = [
    ['speedtest_raw', 'Speedtest Raw Output'],
    ['wifi_raw', 'Wi-Fi Raw Output'],
    ['ping_raw', 'Ping Raw Output'],
    ['tracert_raw', 'Traceroute Raw Output'],
    ['nslookup_raw', 'DNS Raw Output'],
  ]

  return (
    <div className="card">
      <div className="metric-label">Raw Diagnostics</div>
      <div className="small-text" style={{ marginBottom: 8 }}>
        Hidden by default for a clean FAE dashboard. Open only when engineering traceability is needed.
      </div>
      {keys.map(([key, label]) => (
        <details key={key} className="raw-details">
          <summary>{label}</summary>
          <pre className="raw-pre">{raw[key] || 'No raw output available.'}</pre>
        </details>
      ))}
    </div>
  )
}

const automationSkills = [
  {
    title: 'Network diagnostics automation',
    copy: 'Automate IP, gateway, DNS, internet reachability, traceroute, Wi-Fi signal, and throughput checks.',
    icon: Network,
  },
  {
    title: 'API / cloud endpoint testing',
    copy: 'Validate device registration, telemetry upload, health endpoints, token access, and response latency.',
    icon: Cloud,
  },
  {
    title: 'Reporting and execution',
    copy: 'Record the environment, produce PASS / FAIL reports, and prepare runs for schedules or CI/CD.',
    icon: FileText,
  },
]

const learningPath = [
  'Introduction to Network Automation',
  'Using APIs for Network Automation',
  'Google IT Automation with Python',
  'Apply API Testing & Automation with Postman',
]

const commandCatalog = [
  'ipconfig /all',
  'ping 8.8.8.8',
  'ping google.com',
  'tracert google.com',
  'nslookup google.com',
  'Test-NetConnection cloud.example.com -Port 443',
  'Test-NetConnection mqtt.example.com -Port 8883',
  'netsh wlan show interfaces',
]

function numberValue(value) {
  if (value === undefined || value === null || value === '') return null
  const parsed = Number(String(value).replace('%', ''))
  return Number.isFinite(parsed) ? parsed : null
}

function buildValidationChecks(selected) {
  if (!selected) return []

  const signal = numberValue(selected.wifi?.signal_percent ?? selected.wifi?.signal)
  const pingLoss = numberValue(selected.ping?.packet_loss_percent)
  const pingLatency = numberValue(selected.ping?.avg_ms)
  const dnsSuccess = selected.dns?.status === 'success' || (selected.dns?.resolved_ips || []).length > 0
  const download = numberValue(selected.speedtest?.download_mbps)

  return [
    {
      name: 'Wi-Fi link and signal',
      status: signal === null ? 'pending' : signal >= 70 ? 'pass' : 'fail',
      result: signal === null ? 'Signal not available in record' : `${signal}% signal strength`,
      source: 'netsh wlan show interfaces',
    },
    {
      name: 'Public internet reachability',
      status: pingLoss === null ? 'pending' : pingLoss === 0 ? 'pass' : 'fail',
      result: pingLoss === null ? 'Ping result not available' : `${pingLoss}% loss${pingLatency === null ? '' : `, ${pingLatency} ms avg`}`,
      source: 'ping 8.8.8.8',
    },
    {
      name: 'DNS resolution',
      status: selected.dns ? (dnsSuccess ? 'pass' : 'fail') : 'pending',
      result: selected.dns
        ? dnsSuccess
          ? (selected.dns.resolved_ips || []).slice(0, 2).join(', ')
          : 'No resolved IP'
        : 'Not collected in this record',
      source: 'nslookup google.com',
    },
    {
      name: 'Internet throughput',
      status: download === null ? 'pending' : download >= 100 ? 'pass' : 'fail',
      result: download === null ? 'Speedtest not available' : `${download} Mbps download`,
      source: 'speedtest --format=json',
    },
    {
      name: 'Cloud HTTPS endpoint',
      status: 'planned',
      result: 'Add configurable /health endpoint check',
      source: 'requests.get() / TCP 443',
    },
    {
      name: 'MQTT broker connectivity',
      status: 'planned',
      result: 'Add broker TLS reachability for device telemetry',
      source: 'TCP 8883',
    },
  ]
}

function TestStatus({ status }) {
  const labels = { pass: 'PASS', fail: 'FAIL', pending: 'PENDING', planned: 'PLANNED' }
  return <span className={`test-status ${status}`}>{labels[status] || status}</span>
}

function AutomationLab({ selected }) {
  const checks = buildValidationChecks(selected)
  const passCount = checks.filter((check) => check.status === 'pass').length
  const completedCount = checks.filter((check) => check.status === 'pass' || check.status === 'fail').length

  return (
    <div className="automation-layout">
      <div className="card automation-hero">
        <div>
          <div className="automation-kicker">Portfolio Project</div>
          <h3 className="automation-title">Automotive IoT Connectivity Test Automation Tool</h3>
          <p className="small-text">
            Automated network connectivity validation for an FAE workflow: collect evidence, verify device-to-cloud
            connectivity, isolate failure points, and produce repeatable reports.
          </p>
        </div>
        <div className="automation-summary">
          <div className="summary-value">{passCount}/{completedCount || '-'}</div>
          <div className="metric-label">Available checks passing</div>
          <div className="small">{selected ? formatTime(selected.timestamp) : 'Select a measurement to evaluate'}</div>
        </div>
      </div>

      <div className="automation-skill-grid">
        {automationSkills.map(({ title, copy, icon: Icon }) => (
          <div className="card skill-card" key={title}>
            <Icon size={20} />
            <h3 className="section-title">{title}</h3>
            <p className="small-text">{copy}</p>
          </div>
        ))}
      </div>

      <div className="grid-two">
        <div className="card">
          <div className="header-row">
            <div>
              <h3 className="section-title">Automated Validation Suite</h3>
              <p className="subtitle automation-caption">Current measurement plus IoT/cloud expansion coverage</p>
            </div>
            <ShieldCheck size={18} />
          </div>

          {selected ? (
            <div className="test-list">
              {checks.map((check) => (
                <div className="test-row" key={check.name}>
                  <div>
                    <div className="test-name">{check.name}</div>
                    <div className="small">{check.result}</div>
                    <code className="inline-command">{check.source}</code>
                  </div>
                  <TestStatus status={check.status} />
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">Select a measurement from the sidebar to build its validation report.</div>
          )}
        </div>

        <div className="stack">
          <div className="card">
            <div className="header-row">
              <h3 className="section-title">Windows Collection Commands</h3>
              <TerminalSquare size={18} />
            </div>
            <div className="command-grid">
              {commandCatalog.map((command) => <code className="command-item" key={command}>{command}</code>)}
            </div>
          </div>

          <div className="card">
            <div className="metric-label">Automotive IoT Extensions</div>
            <div className="tag-row">
              {['SIM / APN status', 'RSSI / RSRP / SINR', 'GPS fix', 'Device ID / IMEI / ICCID', 'Firmware version', 'Telemetry API'].map((item) => (
                <span className="scope-tag" key={item}>{item}</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid-two">
        <div className="card">
          <div className="header-row">
            <h3 className="section-title">Learning Roadmap</h3>
            <BookOpen size={18} />
          </div>
          <p className="small-text automation-caption">
            Build Python fundamentals first, then add network programmability and cloud/API automation.
          </p>
          <ol className="roadmap-list">
            {learningPath.map((course) => <li key={course}>{course}</li>)}
          </ol>
        </div>

        <div className="card">
          <div className="header-row">
            <h3 className="section-title">Report Output</h3>
            <FileText size={18} />
          </div>
          <div className="report-schema">
            {['PASS / FAIL status', 'Latency and packet loss', 'DNS and TCP port results', 'API response and latency', 'Probable root cause', 'Recommended next step'].map((field) => (
              <div className="report-field" key={field}>{field}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [records, setRecords] = useState([])
  const [locations, setLocations] = useState([])
  const [locationFilter, setLocationFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(null)
  const [mainView, setMainView] = useState('overview')
  const [rightbarTab, setRightbarTab] = useState('ai')
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')

  useEffect(() => {
    loadData()
    const refreshInterval = setInterval(loadData, 300000)
    return () => clearInterval(refreshInterval)
  }, [])

  async function loadData() {
    const [recordsRes, locationsRes] = await Promise.all([
      axios.get('/api/records?limit=50'),
      axios.get('/api/locations'),
    ])
    setRecords(recordsRes.data)
    setLocations(locationsRes.data)
  }

  const filtered = useMemo(() => {
    return records.filter((r) => {
      const locationOk = locationFilter === 'all' || r.location === locationFilter
      const severityOk = severityFilter === 'all' || r.rule_diagnosis?.severity === severityFilter

      const q = query.trim().toLowerCase()
      const queryOk =
        !q ||
        [
          r.location,
          r.environment,
          r.wifi?.ssid,
          r.wifi?.band,
          r.wifi?.radio_type,
          r.root_cause?.root_cause_category,
        ]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(q))

      return locationOk && severityOk && queryOk
    })
  }, [records, locationFilter, severityFilter, query])

  useEffect(() => {
    if (!filtered.length) {
      setSelected(null)
      return
    }
    const stillExists = selected && filtered.find((r) => r.timestamp === selected.timestamp)
    if (!stillExists) setSelected(filtered[0])
  }, [filtered, selected])

  const chartData = useMemo(
    () =>
      [...filtered].reverse().map((r, idx) => ({
        idx,
        time: formatTime(r.timestamp),
        download: r.speedtest?.download_mbps,
        latency: r.speedtest?.latency_ms,
        signal: r.wifi?.signal_percent,
        health: r.rule_diagnosis?.health_score,
      })),
    [filtered]
  )

  const scatterData = useMemo(
    () =>
      filtered.map((r) => ({
        signal: r.wifi?.signal_percent,
        latency: r.speedtest?.latency_ms,
        z: r.speedtest?.download_mbps,
        location: r.location,
        severity: r.rule_diagnosis?.severity || 'normal',
      })),
    [filtered]
  )

  const stats = useMemo(
    () => ({
      avgDownload: avg(filtered, (r) => r.speedtest?.download_mbps).toFixed(1),
      avgUpload: avg(filtered, (r) => r.speedtest?.upload_mbps).toFixed(1),
      avgLatency: avg(filtered, (r) => r.speedtest?.latency_ms).toFixed(1),
      avgJitter: avg(filtered, (r) => r.speedtest?.jitter_ms).toFixed(1),
      avgPacketLoss: avg(filtered, (r) => r.speedtest?.packet_loss).toFixed(1),
      avgSignal: avg(filtered, (r) => r.wifi?.signal_percent).toFixed(0),
      avgRssi: avg(filtered, (r) => r.wifi?.rssi_dbm).toFixed(0),
      avgHealth: avg(filtered, (r) => r.rule_diagnosis?.health_score).toFixed(0),
    }),
    [filtered]
  )

  const evidence = useMemo(() => {
    if (!selected) return []
    return [
      ...(selected.rule_diagnosis?.evidence || []),
      ...(selected.root_cause?.evidence || []),
    ].slice(0, 8)
  }, [selected])

  useEffect(() => {
    if (!selected) return
    setRightbarTab('ai')
    setChatMessages([])
    setChatInput('')
    setChatError('')
  }, [selected])

  async function sendChatQuestion() {
    const question = chatInput.trim()
    if (!selected || !question) return

    const nextMessages = [...chatMessages, { role: 'user', content: question }]
    setChatMessages(nextMessages)
    setChatInput('')
    setChatError('')
    setChatLoading(true)

    try {
      const response = await axios.post('/api/ask', {
        record_id: selected._id,
        question,
      })

      setChatMessages([
        ...nextMessages,
        { role: 'assistant', content: response.data.answer || 'The AI did not return an answer.' },
      ])
    } catch (error) {
      setChatError(error?.response?.data?.error || 'Failed to reach the AI service.')
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="container">
      <aside className="sidebar panel">
        <h1 className="title">Wireless Diagnostics Assistant</h1>
        <p className="subtitle">FAE-style wireless troubleshooting dashboard</p>

        <div className="controls">
          <select className="control" value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)}>
            <option value="all">All locations</option>
            {locations.map((location) => (
              <option key={location} value={location}>{location}</option>
            ))}
          </select>

          <select className="control" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
            <option value="all">All severity</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="normal">Normal</option>
          </select>
        </div>

        <input
          className="search"
          placeholder="Search location / SSID / band / root cause"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <div style={{ marginTop: 18 }}>
          <div className="header-row">
            <h2 className="section-title">Measurements</h2>
            <span className="small">{filtered.length} records</span>
          </div>

          <div className="list">
            {filtered.map((record) => (
              <div
                key={record.timestamp}
                className={`list-item ${selected?.timestamp === record.timestamp ? 'active' : ''}`}
                onClick={() => setSelected(record)}
              >
                <div className="header-row" style={{ marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{record.location || 'unknown'}</div>
                    <div className="small">{formatTime(record.timestamp)}</div>
                  </div>
                  <span className={`badge ${severityClass(record.rule_diagnosis?.severity)}`}>
                    {record.rule_diagnosis?.severity || 'normal'}
                  </span>
                </div>
                <div className="small">
                  SSID: {record.wifi?.ssid || '-'} · {record.wifi?.band || '-'} · Root cause:{' '}
                  {record.root_cause?.root_cause_category || '-'}
                </div>
              </div>
            ))}
            {!filtered.length && <div className="empty">No recent records found.</div>}
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="header-row page-header">
          <div>
            <h2 className="title" style={{ fontSize: 28, marginBottom: 4 }}>Field Diagnostics Dashboard</h2>
            <p className="subtitle">FAE view: performance, Wi-Fi link, connectivity, evidence, and AI explanation</p>
          </div>

          <div className="view-tabs">
            <button
              type="button"
              className={`tab-button ${mainView === 'overview' ? 'active' : ''}`}
              onClick={() => setMainView('overview')}
            >
              Overview
            </button>
            <button
              type="button"
              className={`tab-button ${mainView === 'notes' ? 'active' : ''}`}
              onClick={() => setMainView('notes')}
            >
              AI & Engineering Notes
            </button>
            <button
              type="button"
              className={`tab-button ${mainView === 'automation' ? 'active' : ''}`}
              onClick={() => setMainView('automation')}
            >
              Automation Lab
            </button>
          </div>
        </div>

        {mainView === 'overview' ? (
          <>
            <div className="card-grid">
              <div className="card"><div className="metric-label">Avg Download</div><div className="metric-value">{stats.avgDownload} Mbps</div></div>
              <div className="card"><div className="metric-label">Avg Upload</div><div className="metric-value">{stats.avgUpload} Mbps</div></div>
              <div className="card"><div className="metric-label">Avg Latency</div><div className="metric-value">{stats.avgLatency} ms</div></div>
              <div className="card"><div className="metric-label">Avg Jitter</div><div className="metric-value">{stats.avgJitter} ms</div></div>
              <div className="card"><div className="metric-label">Packet Loss</div><div className="metric-value">{stats.avgPacketLoss}%</div></div>
              <div className="card"><div className="metric-label">Avg Signal</div><div className="metric-value">{stats.avgSignal}%</div></div>
              <div className="card"><div className="metric-label">Avg RSSI</div><div className="metric-value">{stats.avgRssi} dBm</div></div>
              <div className="card"><div className="metric-label">Avg Health</div><div className="metric-value">{stats.avgHealth}</div></div>
            </div>

            {selected ? (
              <>
                <div className="grid-two">
                  <div className="stack">
                    <div className="card">
                      <div className="header-row">
                        <h3 className="section-title">Selected Measurement</h3>
                        <span className={`badge ${severityClass(selected.rule_diagnosis?.severity)}`}>
                          {selected.rule_diagnosis?.severity || 'normal'}
                        </span>
                      </div>
                      <div className="small">{formatTime(selected.timestamp)} · {selected.location || '-'} · {selected.environment || '-'}</div>
                    </div>

                    <DetailSection title="Performance">
                      <MetricItem label="Download" value={fmt(selected.speedtest?.download_mbps, ' Mbps')} />
                      <MetricItem label="Upload" value={fmt(selected.speedtest?.upload_mbps, ' Mbps')} />
                      <MetricItem label="Idle Latency" value={fmt(selected.speedtest?.latency_ms, ' ms')} />
                      <MetricItem label="Jitter" value={fmt(selected.speedtest?.jitter_ms, ' ms')} />
                      <MetricItem label="Packet Loss" value={fmt(selected.speedtest?.packet_loss, '%')} />
                      <MetricItem label="Ping Avg / Loss" value={`${fmt(selected.ping?.avg_ms, ' ms')} / ${fmt(selected.ping?.packet_loss_percent, '% loss')}`} />
                    </DetailSection>

                    <DetailSection title="Wi-Fi Link">
                      <MetricItem label="SSID" value={selected.wifi?.ssid || '-'} />
                      <MetricItem label="Band" value={selected.wifi?.band || '-'} />
                      <MetricItem label="Channel" value={selected.wifi?.channel || '-'} />
                      <MetricItem label="Radio Type" value={selected.wifi?.radio_type || '-'} />
                      <MetricItem label="Signal" value={fmt(selected.wifi?.signal_percent, '%', 0)} />
                      <MetricItem label="RSSI" value={fmt(selected.wifi?.rssi_dbm, ' dBm', 0)} />
                      <MetricItem label="Rx Rate" value={fmt(selected.wifi?.receive_rate_mbps, ' Mbps', 0)} />
                      <MetricItem label="Tx Rate" value={fmt(selected.wifi?.transmit_rate_mbps, ' Mbps', 0)} />
                      <MetricItem label="AP BSSID" value={selected.wifi?.ap_bssid || '-'} />
                      <MetricItem label="Adapter" value={selected.wifi?.adapter || '-'} />
                    </DetailSection>

                    <DetailSection title="Connectivity">
                      <MetricItem label="Ping Target" value={selected.ping?.target || '8.8.8.8'} />
                      <MetricItem label="Ping Status" value={selected.ping?.status || '-'} />
                      <MetricItem label="DNS Status" value={selected.dns?.status || '-'} />
                      <MetricItem label="DNS Server" value={selected.dns?.dns_server_ip || selected.dns?.dns_server || '-'} />
                      <MetricItem label="Resolved IP" value={(selected.dns?.resolved_ips || []).slice(0, 2).join(', ') || '-'} />
                      <MetricItem label="Speedtest Server" value={selected.speedtest?.server_location || selected.speedtest?.server_name || '-'} />
                    </DetailSection>
                  </div>

                  <div className="stack">
                    <div className="card">
                      <div className="header-row">
                        <h3 className="section-title">FAE Decision Output</h3>
                        <ShieldCheck size={18} />
                      </div>

                      <div className="detail-item" style={{ marginBottom: 12 }}>
                        <div className="kv-label">Root Cause</div>
                        <div className="kv-value" style={{ fontSize: 22 }}>{selected.root_cause?.root_cause_category || '-'}</div>
                        <div className="small" style={{ marginTop: 8 }}>Confidence: {selected.root_cause?.confidence ?? '-'}</div>
                      </div>

                      <div className="detail-item" style={{ marginBottom: 12 }}>
                        <div className="kv-label">Health Score</div>
                        <div className="kv-value">{selected.rule_diagnosis?.health_score ?? '-'}</div>
                      </div>

                      <div className="metric-label">Evidence</div>
                      <ul className="bullet-list">
                        {evidence.length ? evidence.map((item, idx) => <li key={idx}>{item}</li>) : <li>No evidence available.</li>}
                      </ul>
                    </div>

                    <div className="card">
                      <div className="metric-label">Recommended Actions</div>
                      <ul className="bullet-list">
                        {(selected.recommendation_plan?.actions || []).map((item, idx) => (
                          <li key={idx}>
                            <strong>{item.action}</strong><br />
                            <span className="small">{item.reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="grid-two" style={{ marginTop: 16 }}>
                  <div className="card">
                    <div className="header-row"><h3 className="section-title">Trend: Download / Latency</h3><Gauge size={18} /></div>
                    <div className="chart-wrap">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                          <CartesianGrid stroke="rgba(16, 40, 70, 0.12)" />
                          <XAxis dataKey="time" hide />
                          <YAxis yAxisId="left" stroke="#486581" />
                          <YAxis yAxisId="right" orientation="right" stroke="#486581" />
                          <Tooltip />
                          <Line yAxisId="left" type="monotone" dataKey="download" stroke="#6fb6ff" strokeWidth={3} dot={false} />
                          <Line yAxisId="right" type="monotone" dataKey="latency" stroke="#1c7ed6" strokeWidth={3} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="card">
                    <div className="header-row"><h3 className="section-title">Signal vs Latency</h3><Activity size={18} /></div>
                    <div className="chart-wrap">
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart>
                          <CartesianGrid stroke="rgba(16, 40, 70, 0.12)" />
                          <XAxis dataKey="signal" name="Signal" unit="%" stroke="#486581" />
                          <YAxis dataKey="latency" name="Latency" unit="ms" stroke="#486581" />
                          <ZAxis dataKey="z" range={[80, 400]} />
                          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                          <Scatter data={scatterData}>
                            {scatterData.map((entry, index) => {
                              let color = '#6fb6ff'
                              if (entry.severity === 'high') color = '#ff6b6b'
                              else if (entry.severity === 'medium') color = '#ffc857'
                              return <Cell key={`cell-${index}`} fill={color} />
                            })}
                          </Scatter>
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="card">No recent data loaded.</div>
            )}
          </>
        ) : mainView === 'notes' ? (
          <div className="stack">
            <div className="card">
              <div className="header-row">
                <div>
                  <h3 className="section-title">AI & Engineering Notes</h3>
                  <p className="subtitle" style={{ marginTop: 6 }}>Focused view for the selected record.</p>
                </div>
                <AlertTriangle size={18} />
              </div>

              <div className="tabs">
                <button
                  type="button"
                  className={`tab-button ${rightbarTab === 'ai' ? 'active' : ''}`}
                  onClick={() => setRightbarTab('ai')}
                >
                  AI Notes
                </button>
                <button
                  type="button"
                  className={`tab-button ${rightbarTab === 'issues' ? 'active' : ''}`}
                  onClick={() => setRightbarTab('issues')}
                >
                  Issues
                </button>
                <button
                  type="button"
                  className={`tab-button ${rightbarTab === 'logs' ? 'active' : ''}`}
                  onClick={() => setRightbarTab('logs')}
                >
                  Logs
                </button>
                <button
                  type="button"
                  className={`tab-button ${rightbarTab === 'chat' ? 'active' : ''}`}
                  onClick={() => setRightbarTab('chat')}
                >
                  Ask AI
                </button>
              </div>

              {selected ? (
                <div className="list" style={{ gap: 16 }}>
                  {rightbarTab === 'ai' && (
                    <div className="card">
                      <div className="header-row">
                        <h3 className="section-title">AI Analysis Report</h3>
                        <Brain size={18} />
                      </div>

                      <div className="ai-section">
                        <div className="ai-section-header">
                          <h4 className="ai-section-title">Executive Summary</h4>
                        </div>
                        <div className="small-text">{selected.llm_diagnosis?.summary || 'No summary available.'}</div>
                      </div>

                      <div className="ai-section-divider"></div>

                      <div className="ai-section">
                        <div className="ai-section-header">
                          <h4 className="ai-section-title">Customer Communication</h4>
                        </div>
                        {renderCustomerExplanation(selected.llm_diagnosis?.customer_friendly_explanation)}
                      </div>

                      <div className="ai-section-divider"></div>

                      <div className="ai-section">
                        <div className="ai-section-header">
                          <h4 className="ai-section-title">Technical Analysis</h4>
                        </div>
                        {renderEngineerNote(selected.llm_diagnosis?.engineer_note)}
                      </div>
                    </div>
                  )}

                  {rightbarTab === 'issues' && (
                    <>
                      <div className="card">
                        <div className="metric-label">Detected Issues</div>
                        <ul className="bullet-list">
                          {(selected.rule_diagnosis?.issues || []).length ? (
                            selected.rule_diagnosis.issues.map((item, idx) => <li key={idx}>{item}</li>)
                          ) : (
                            <li>No issues detected.</li>
                          )}
                        </ul>
                      </div>

                      <div className="card">
                        <div className="metric-label">Anomalies vs Baseline</div>
                        <ul className="bullet-list">
                          {(selected.baseline_analysis?.anomalies || []).length ? (
                            selected.baseline_analysis.anomalies.map((item, idx) => <li key={idx}>{item.message}</li>)
                          ) : (
                            <li>No anomaly detected.</li>
                          )}
                        </ul>
                      </div>
                    </>
                  )}

                  {rightbarTab === 'logs' && <RawLogs selected={selected} />}

                  {rightbarTab === 'chat' && (
                    <div className="card chat-card">
                      <div className="metric-label">LLM Assistant</div>
                      <div className="chat-window">
                        {chatMessages.length ? (
                          chatMessages.map((msg, idx) => (
                            <div key={idx} className={`chat-message ${msg.role}`}>
                              <div className="chat-role">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                              <div>{msg.content}</div>
                            </div>
                          ))
                        ) : (
                          <div className="empty">Ask a question about the recent measurements to get help from the assistant.</div>
                        )}
                      </div>

                      <textarea
                        className="chat-input"
                        rows={4}
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="e.g. What trends do you see in the recent 10 measurements?"
                      />

                      <button
                        type="button"
                        className="primary-button"
                        onClick={sendChatQuestion}
                        disabled={chatLoading || !chatInput.trim()}
                      >
                        {chatLoading ? 'Asking AI...' : 'Ask AI'}
                      </button>

                      {chatError && <div className="error-text">{chatError}</div>}
                    </div>
                  )}
                </div>
              ) : (
                <div className="empty">Select a recent record to view AI and engineering notes.</div>
              )}
            </div>
          </div>
        ) : (
          <AutomationLab selected={selected} />
        )}
      </main>
    </div>
  )
}
