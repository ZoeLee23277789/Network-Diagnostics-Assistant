import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Activity, CheckCircle2, Play, XCircle } from 'lucide-react'

function statusClass(status) {
  if (status === 'pass') return 'normal'
  if (status === 'warning') return 'medium'
  return 'high'
}

function parseLines(value) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parsePorts(value) {
  return parseLines(value).map((line) => {
    const [namePart, targetPart] = line.includes('=') ? line.split('=') : ['', line]
    const [host, port] = targetPart.trim().split(':')
    return {
      name: namePart.trim() || `${host}:${port}`,
      host: host.trim(),
      port: Number(port),
    }
  }).filter((item) => item.host && item.port)
}

function ResultIcon({ passed }) {
  return passed ? <CheckCircle2 size={18} /> : <XCircle size={18} />
}

export default function ConnectivityTestPage() {
  const [config, setConfig] = useState(null)
  const [pingTargets, setPingTargets] = useState('')
  const [dnsTargets, setDnsTargets] = useState('')
  const [portTargets, setPortTargets] = useState('')
  const [runTraceroute, setRunTraceroute] = useState(true)
  const [runSpeedtest, setRunSpeedtest] = useState(false)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadConfig() {
      const res = await axios.get('/api/connectivity/config')
      setConfig(res.data)
      setPingTargets(res.data.ping_targets.join('\n'))
      setDnsTargets(res.data.dns_targets.join('\n'))
      setPortTargets(res.data.port_targets.map((item) => `${item.name}=${item.host}:${item.port}`).join('\n'))
      setRunTraceroute(Boolean(res.data.run_traceroute))
      setRunSpeedtest(Boolean(res.data.run_speedtest))
    }

    loadConfig().catch((err) => setError(err?.response?.data?.error || 'Failed to load connectivity config.'))
  }, [])

  async function runSuite() {
    setLoading(true)
    setError('')

    try {
      const res = await axios.post('/api/connectivity/run', {
        ...(config || {}),
        ping_targets: parseLines(pingTargets),
        dns_targets: parseLines(dnsTargets),
        port_targets: parsePorts(portTargets),
        run_traceroute: runTraceroute,
        run_speedtest: runSpeedtest,
      })
      setReport(res.data)
    } catch (err) {
      if (err.response?.data?.summary) {
        setReport(err.response.data)
      } else {
        setError(err?.response?.data?.error || 'Connectivity test failed.')
      }
    } finally {
      setLoading(false)
    }
  }

  const grouped = useMemo(() => {
    const output = {}
    for (const test of report?.tests || []) {
      output[test.category] = [...(output[test.category] || []), test]
    }
    return output
  }, [report])

  return (
    <div className="connectivity-page">
      <div className="header-row page-header">
        <div>
          <h2 className="title" style={{ fontSize: 28, marginBottom: 4 }}>Automated Connectivity Validation</h2>
          <p className="subtitle">Python automation for ping, DNS, TCP port, Wi-Fi, traceroute, and report generation.</p>
        </div>
        <button type="button" className="primary-button" onClick={runSuite} disabled={loading}>
          <Play size={16} />
          {loading ? 'Running Tests...' : 'Run Suite'}
        </button>
      </div>

      {error && <div className="error-text">{error}</div>}

      <div className="connectivity-layout">
        <section className="card test-plan-card">
          <div className="header-row">
            <h3 className="section-title">Test Plan</h3>
            <Activity size={18} />
          </div>

          <div className="test-form-grid">
            <label>
              <div className="metric-label">Ping Targets</div>
              <textarea className="test-textarea" rows={4} value={pingTargets} onChange={(e) => setPingTargets(e.target.value)} />
            </label>
            <label>
              <div className="metric-label">DNS Targets</div>
              <textarea className="test-textarea" rows={4} value={dnsTargets} onChange={(e) => setDnsTargets(e.target.value)} />
            </label>
            <label>
              <div className="metric-label">TCP Port Tests</div>
              <textarea className="test-textarea" rows={4} value={portTargets} onChange={(e) => setPortTargets(e.target.value)} />
            </label>
          </div>

          <div className="toggle-row">
            <label><input type="checkbox" checked={runTraceroute} onChange={(e) => setRunTraceroute(e.target.checked)} /> Traceroute</label>
            <label><input type="checkbox" checked={runSpeedtest} onChange={(e) => setRunSpeedtest(e.target.checked)} /> Speedtest</label>
          </div>
        </section>
      </div>

      {report && (
        <div className="stack" style={{ marginTop: 18 }}>
          <div className="card">
            <div className="header-row">
              <h3 className="section-title">Latest Report</h3>
              <span className={`badge ${statusClass(report.summary.overall_status)}`}>
                {report.summary.overall_status}
              </span>
            </div>
            <div className="card-grid report-metrics">
              <div className="detail-item"><div className="kv-label">Total</div><div className="kv-value">{report.summary.total_tests}</div></div>
              <div className="detail-item"><div className="kv-label">Passed</div><div className="kv-value">{report.summary.passed}</div></div>
              <div className="detail-item"><div className="kv-label">Failed</div><div className="kv-value">{report.summary.failed}</div></div>
            </div>
            <div className="report-path">JSON: {report.reports?.json_report}</div>
            <div className="report-path">HTML: {report.reports?.html_report}</div>
          </div>

          {Object.entries(grouped).map(([category, tests]) => (
            <div className="card" key={category}>
              <h3 className="section-title" style={{ marginBottom: 14 }}>{category}</h3>
              <div className="test-result-list">
                {tests.map((test) => (
                  <details className="test-result-item" key={test.name}>
                    <summary>
                      <span className={`result-icon ${test.passed ? 'pass' : 'fail'}`}><ResultIcon passed={test.passed} /></span>
                      <strong>{test.name}</strong>
                      <span className={`badge ${test.passed ? 'normal' : 'high'}`}>{test.status}</span>
                    </summary>
                    <div className="small-text" style={{ marginTop: 10 }}>{test.recommendation}</div>
                    <pre className="raw-pre">{JSON.stringify(test.details, null, 2)}</pre>
                  </details>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
