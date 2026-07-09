# Kaaval Assurance — Inference Flight Deck

A real-time inference monitoring dashboard for AI governance and compliance.  
Inspired by mission-control NOC interfaces — designed for teams running AI inference at scale.

## Features

- **Pipeline Visualization** — Real-time inference request flow through model gates
- **Provider Switchboard** — AI provider health, routing, and failover status
- **Contract Gate** — Policy enforcement (compliance, security, cost rules)
- **Model Comparison** — Side-by-side model latency, quality, and cost
- **Telemetry Truth** — Ground-truth metrics with sparkline toggle
- **Trajectory Replay** — Full audit trail of every request
- **AMD Proof** — Cryptographic attestation measurements
- **Summary Dashboard** — At-a-glance KPIs with collapsible mission briefing

## Prerequisites

- **Node.js** v18 or later (recommended: v20+)
- **npm** v9 or later

## Local Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd kaaval-assurance

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev
```

The dev server starts on **http://localhost:5173** by default (Vite's default port).

## Build for Production

```bash
npm run build
```

Output goes to the `dist/` folder. You can serve it with any static file server:

```bash
# Using Vite's built-in preview server
npm run preview

# Or using any static server (e.g. serve, nginx, python, caddy)
npx serve dist
```

## Running Locally Without Node.js (Static HTML)

After building (`npm run build`), the entire app is a set of static files in `dist/`.  
You can serve them with Python, an HTTP server, or even open the `index.html` directly (though some features may require an HTTP server):

```bash
# Python 3
python -m http.server 8080 --directory dist

# Or with npx serve
npx serve dist
```

Then open **http://localhost:8080** in your browser.

## Tech Stack

- **React 18** + **TypeScript**
- **Vite 7** (build tool)
- **Tailwind CSS v4** (styling)
- **Lucide React** (icons)
- **Fira Code / Fira Sans** (typography)

## Project Structure

```
├── public/
│   └── nativelyai.svg
├── src/
│   ├── components/
│   │   ├── AMDProof.tsx
│   │   ├── ContractGate.tsx
│   │   ├── Header.tsx
│   │   ├── ModelComparison.tsx
│   │   ├── PipelinePanel.tsx
│   │   ├── ProviderSwitchboard.tsx
│   │   ├── StatusBar.tsx
│   │   ├── SummaryDashboard.tsx
│   │   ├── TelemetryTruth.tsx
│   │   └── TrajectoryReplay.tsx
│   ├── mock/
│   │   └── data.ts
│   ├── App.tsx
│   ├── index.css
│   ├── main.tsx
│   └── types.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```