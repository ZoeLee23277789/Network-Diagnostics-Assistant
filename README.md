# Wireless Troubleshooting System

A full-stack demo project designed to align with a Field Application Engineer workflow:
- collect real-world wireless/network diagnostics
- compare against baseline behavior
- detect anomalies
- classify likely root causes
- generate LLM-powered engineer notes and customer-friendly explanations

## Why this is relevant to FAE
This project is built to match common FAE responsibilities:
- field testing and validation
- issue diagnosis and performance analysis
- customer-facing troubleshooting summaries
- system integration across data collection, backend logic, and UI

## Stack
### Backend
- Flask
- MongoDB
- OpenAI API
- Python collector script with Speedtest CLI / ping / netsh

### Frontend
- React + Vite
- Recharts

## Project structure
```text
wnc_fae_ai_system/
  backend/
    app.py
    baseline.py
    collector_agent.py
    diagnosis.py
    llm_diagnosis.py
    parsers.py
    requirements.txt
    seed_data.py
    .env.example
  frontend/
    src/
    package.json
    vite.config.js
  sample_data/
    network_logs.jsonl
  README.md
```

## 1. Backend setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and fill in your API key:
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=wireless_troubleshooting
COLLECTION_NAME=records
USE_LLM=true
```

## 2. Start MongoDB
Make sure MongoDB is running locally.

## 3. Seed sample data
```bash
python seed_data.py
```

## 4. Run backend
```bash
python app.py
```
Backend runs at:
```text
http://127.0.0.1:5000
```

## 5. Run frontend
Open a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at:
```text
http://127.0.0.1:5173
```

## 6. Collect new real data
Make sure these are available on your Windows machine:
- `speedtest`
- `netsh`
- `ping`
- `tracert`
- `nslookup`

Then run:
```bash
cd backend
python collector_agent.py
```
The script will:
1. collect live network diagnostics
2. send the measurement to Flask
3. enrich it with anomaly detection, diagnosis, root cause, recommendations, and LLM output

## API endpoints
### GET `/api/health`
Health check

### GET `/api/records`
Returns enriched records

### POST `/api/records`
Accepts a measurement record and enriches it

### GET `/api/summary`
Returns dashboard-level summary metrics

### GET `/api/locations`
Returns available locations

### GET `/api/baseline/<location>`
Returns computed baseline for one location

### POST `/api/reanalyze`
Rebuilds analysis for all stored records

## Suggested resume bullet
- Built an AI-driven wireless troubleshooting system using Python, Flask, MongoDB, React, and the OpenAI API to collect real-world network diagnostics, detect anomalies, classify root causes, and generate actionable field-support recommendations.

## Suggested interview summary
> I built a wireless troubleshooting system that simulates a field application engineer workflow. It collects real-world Wi-Fi and network diagnostics data, compares current results against historical baselines, identifies anomalies, classifies likely causes such as weak signal or congestion, and generates both technical and customer-friendly troubleshooting notes using an LLM.
