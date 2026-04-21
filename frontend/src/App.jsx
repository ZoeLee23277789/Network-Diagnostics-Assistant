import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, AlertTriangle, Gauge, ShieldCheck } from 'lucide-react'
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

export default function App() {
  const [records, setRecords] = useState([])
  const [summary, setSummary] = useState(null)
  const [locations, setLocations] = useState([])
  const [locationFilter, setLocationFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    loadData()

    // Auto-refresh every 5 minutes
    const refreshInterval = setInterval(() => {
      console.log('[AutoRefresh] Fetching latest data...')
      loadData()
    }, 300000)

    return () => clearInterval(refreshInterval)
  }, [])

  async function loadData() {
    const [recordsRes, summaryRes, locationsRes] = await Promise.all([
      axios.get('/api/records?limit=30'),
      axios.get('/api/summary'),
      axios.get('/api/locations'),
    ])

    setRecords(recordsRes.data)
    setSummary(summaryRes.data)
    setLocations(locationsRes.data)
  }

  const filtered = useMemo(() => {
    const now = Date.now()
    const cutoff = now - 24 * 60 * 60 * 1000 // 最近24小時

    return records.filter((r) => {
      const recordTime = new Date(r.timestamp).getTime()
      const recentOk = !Number.isNaN(recordTime) && recordTime >= cutoff

      const locationOk = locationFilter === 'all' || r.location === locationFilter
      const severityOk = severityFilter === 'all' || r.rule_diagnosis?.severity === severityFilter

      const q = query.trim().toLowerCase()
      const queryOk =
        !q ||
        [
          r.location,
          r.environment,
          r.wifi?.ssid,
          r.root_cause?.root_cause_category,
        ]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(q))

      return recentOk && locationOk && severityOk && queryOk
    })
  }, [records, locationFilter, severityFilter, query])

  useEffect(() => {
    if (!filtered.length) {
      setSelected(null)
      return
    }

    const stillExists = selected && filtered.find((r) => r.timestamp === selected.timestamp)
    if (!stillExists) {
      setSelected(filtered[0])
    }
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
      avgLatency: avg(filtered, (r) => r.speedtest?.latency_ms).toFixed(1),
      avgSignal: avg(filtered, (r) => r.wifi?.signal_percent).toFixed(0),
      avgHealth: avg(filtered, (r) => r.rule_diagnosis?.health_score).toFixed(0),
    }),
    [filtered]
  )

  return (
    <div className="container">
      <aside className="sidebar panel">
        <h1 className="title">Wireless Diagnostics Assistant</h1>
        <p className="subtitle">Wireless troubleshooting assistant for field diagnostics</p>

        <div className="controls">
          <select
            className="control"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
          >
            <option value="all">All locations</option>
            {locations.map((location) => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>

          <select
            className="control"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="all">All severity</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="normal">Normal</option>
          </select>
        </div>

        <input
          className="search"
          placeholder="Search location / SSID / root cause"
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
                  SSID: {record.wifi?.ssid || '-'} · Root cause:{' '}
                  {record.root_cause?.root_cause_category || '-'}
                </div>
              </div>
            ))}

            {!filtered.length && <div className="empty">No recent records found.</div>}
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="header-row">
          <div>
            <h2 className="title" style={{ fontSize: 28, marginBottom: 4 }}>
              Field Diagnostics Dashboard
            </h2>
            <p className="subtitle">
              From raw measurements to anomaly detection, root cause, and AI explanation
            </p>
          </div>
        </div>

        <div className="card-grid">
          <div className="card">
            <div className="metric-label">Avg Download</div>
            <div className="metric-value">{stats.avgDownload} Mbps</div>
          </div>
          <div className="card">
            <div className="metric-label">Avg Latency</div>
            <div className="metric-value">{stats.avgLatency} ms</div>
          </div>
          <div className="card">
            <div className="metric-label">Avg Signal</div>
            <div className="metric-value">{stats.avgSignal}%</div>
          </div>
          <div className="card">
            <div className="metric-label">Avg Health Score</div>
            <div className="metric-value">{stats.avgHealth}</div>
          </div>
        </div>

        {selected ? (
          <>
            <div className="grid-two">
              <div className="card">
                <div className="header-row">
                  <h3 className="section-title">Selected Measurement</h3>
                  <span className={`badge ${severityClass(selected.rule_diagnosis?.severity)}`}>
                    {selected.rule_diagnosis?.severity}
                  </span>
                </div>

                <div className="detail-grid">
                  <div className="detail-item">
                    <div className="kv-label">Download</div>
                    <div className="kv-value">{selected.speedtest?.download_mbps} Mbps</div>
                  </div>
                  <div className="detail-item">
                    <div className="kv-label">Upload</div>
                    <div className="kv-value">{selected.speedtest?.upload_mbps} Mbps</div>
                  </div>
                  <div className="detail-item">
                    <div className="kv-label">Latency</div>
                    <div className="kv-value">{selected.speedtest?.latency_ms} ms</div>
                  </div>
                  <div className="detail-item">
                    <div className="kv-label">Jitter</div>
                    <div className="kv-value">{selected.speedtest?.jitter_ms} ms</div>
                  </div>
                  <div className="detail-item">
                    <div className="kv-label">Signal</div>
                    <div className="kv-value">{selected.wifi?.signal_percent ?? '-'}%</div>
                  </div>
                  <div className="detail-item">
                    <div className="kv-label">RSSI</div>
                    <div className="kv-value">{selected.wifi?.rssi_dbm ?? '-'} dBm</div>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="header-row">
                  <h3 className="section-title">FAE Decision Output</h3>
                  <ShieldCheck size={18} />
                </div>

                <div className="detail-item" style={{ marginBottom: 12 }}>
                  <div className="kv-label">Root Cause</div>
                  <div className="kv-value" style={{ fontSize: 22 }}>
                    {selected.root_cause?.root_cause_category || '-'}
                  </div>
                  <div className="small" style={{ marginTop: 8 }}>
                    Confidence: {selected.root_cause?.confidence ?? '-'}
                  </div>
                </div>

                <div className="detail-item">
                  <div className="kv-label">Health Score</div>
                  <div className="kv-value">{selected.rule_diagnosis?.health_score}</div>
                </div>
              </div>
            </div>

            <div className="grid-two" style={{ marginTop: 16 }}>
              <div className="card">
                <div className="header-row">
                  <h3 className="section-title">Trend: Download / Latency</h3>
                  <Gauge size={18} />
                </div>

                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="time" hide />
                      <YAxis yAxisId="left" stroke="#8ca5c8" />
                      <YAxis yAxisId="right" orientation="right" stroke="#8ca5c8" />
                      <Tooltip />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="download"
                        stroke="#6fb6ff"
                        strokeWidth={3}
                        dot={false}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="latency"
                        stroke="#ffc857"
                        strokeWidth={3}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card">
                <div className="header-row">
                  <h3 className="section-title">Signal vs Latency</h3>
                  <Activity size={18} />
                </div>

                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="signal" name="Signal" unit="%" stroke="#8ca5c8" />
                      <YAxis dataKey="latency" name="Latency" unit="ms" stroke="#8ca5c8" />
                      <ZAxis dataKey="z" range={[80, 400]} />
                      <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                      <Scatter data={scatterData}>
                      {scatterData.map((entry, index) => {
                        let color = '#8bafff'

                        if (entry.severity === 'high') color = '#ff6b6b'
                        else if (entry.severity === 'medium') color = '#ffc857'
                        else if (entry.severity === 'normal') color = '#6fb6ff'

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
      </main>

      <aside className="rightbar panel">
        <div className="header-row">
          <h2 className="section-title">AI & Engineering Notes</h2>
          <AlertTriangle size={18} />
        </div>

        {selected ? (
          <div className="list" style={{ gap: 16 }}>
            <div className="card">
              <div className="metric-label">AI Summary</div>
              <div style={{ lineHeight: 1.5 }}>{selected.llm_diagnosis?.summary || '-'}</div>
            </div>

            <div className="card">
              <div className="metric-label">Engineer Note</div>
              <div style={{ lineHeight: 1.5 }}>
                {selected.llm_diagnosis?.engineer_note || '-'}
              </div>
            </div>

            <div className="card">
              <div className="metric-label">Customer Explanation</div>
              <div style={{ lineHeight: 1.5 }}>
                {selected.llm_diagnosis?.customer_friendly_explanation || '-'}
              </div>
            </div>

            <div className="card">
              <div className="metric-label">Detected Issues</div>
              <ul className="bullet-list">
                {(selected.rule_diagnosis?.issues || []).map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="card">
              <div className="metric-label">Anomalies vs Baseline</div>
              <ul className="bullet-list">
                {(selected.baseline_analysis?.anomalies || []).length ? (
                  selected.baseline_analysis.anomalies.map((item, idx) => (
                    <li key={idx}>{item.message}</li>
                  ))
                ) : (
                  <li>No anomaly detected.</li>
                )}
              </ul>
            </div>

            <div className="card">
              <div className="metric-label">Recommended Actions</div>
              <ul className="bullet-list">
                {(selected.recommendation_plan?.actions || []).map((item, idx) => (
                  <li key={idx}>
                    <strong>{item.action}</strong>
                    <br />
                    <span className="small">{item.reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div className="empty">Select a recent record to view diagnosis details.</div>
        )}
      </aside>
    </div>
  )
}