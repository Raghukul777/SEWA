# SEWA - Sepsis Early Warning System

SEWA is a real-time clinical monitoring application designed to assist healthcare professionals in the early detection and management of sepsis in ICU settings. The system continuously monitors simulated patient vital signs, applies clinical risk algorithms, and generates timely alerts to improve patient outcomes.

## 🚀 Key Features

### 🏥 Live Patient Dashboard
- **Real-time Monitoring**: View multiple patients simultaneously with dynamic vital sign updates (Heart Rate, BP, SpO2, Temp, RR).
- **Patient Status**: Instant visual indicators of patient stability and sepsis risk levels.
- **Simulation Engine**: Built-in vital sign simulator to demonstrate various clinical trajectories (Stable, Early Sepsis, Septic Shock).

### ⚡ Sepsis Risk Engine
- **Automated Analysis**: Continuously evaluates patient data against sepsis criteria.
- **Risk Stratification**: Categorizes patients into risk levels to prioritize care.
- **Clinical Alerts**: Generates actionable alerts with clinical context, triggered criteria, and recommended actions.

### 📊 Detailed Analytics
- **Vital Trend Charts**: Interactive visualization of patient history to spot deterioration trends over time.
- **Comprehensive Patient View**: Deeply detailed view of current parameters and risk assessment.

### 📝 Audit & Compliance
- **Audit Logging**: Immutable record of all system events, including alert generation, user feedback, and risk level changes.
- **Search & Filter**: Powerful tools to filter logs by event type, severity, date, and patient.
- **Data Export**: Export audit trails to CSV for external reporting and clinical review.

## 🛠️ Technology Stack

- **Frontend Core**: React 18+, Vite
- **Styling**: Tailwind CSS, Shadcn UI patterns
- **State & Data Fetching**: TanStack Query (React Query)
- **Routing**: React Router DOM
- **Visualization**: Recharts
- **Icons**: Lucide React
- **Utilities**: Date-fns, clsx, tailwind-merge

## 📦 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SEWA
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open the application**
   Navigate to `http://localhost:5173` in your browser.

## 🧪 Simulation
The application runs in a simulated mode by default, generating mock data for a set of ICU patients. You can pause/resume the simulation directly from the dashboard to inspect specific states.

## � Screenshots

### Landing Page
![Landing Page](./screenshots/landing-page.png)

### Sepsis Monitoring Dashboard
![Dashboard](./screenshots/dashboard.png)

### Audit & Compliance Log
![Audit Log](./screenshots/audit-log.png)

## �📋 License
Private - For Internal Use Only.
