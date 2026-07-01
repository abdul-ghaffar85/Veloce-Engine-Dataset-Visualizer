<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/2345aadf-6a0f-4de1-8d0f-96b3ee2c729a" />

#  Veloce Engine

> **AI-Powered Self-Service Business Intelligence (BI) & Analytics Platform**

Veloce Engine is a modern Business Intelligence (BI) platform inspired by **Power BI**, **Tableau**, **XLBooster**, **Looker Studio**, and **PyGWalker**. It enables users to upload CSV or Excel datasets, analyze them using an intelligent semantic engine, create interactive visualizations through drag-and-drop, and build customizable dashboards—all without writing SQL or code.

> **Project Status:** Active Development 

---

#  Features

##  Data Import

- Upload CSV files
- Upload Excel (.xlsx) files
- Automatic dataset preview
- Multi-sheet Excel support
- File validation

---

##  Data Profiling

Automatically analyzes uploaded datasets and detects:

- Column data types
- Missing values
- Unique values
- Cardinality
- Basic statistics
- Dataset metadata

---

##  Semantic Intelligence

Automatically classifies fields into semantic categories:

- Dimensions
- Metrics
- Temporal fields
- Geographic fields
- Identifiers
- Currency
- Percentage
- Boolean

This semantic layer powers intelligent visualization and prevents invalid chart configurations.

---

##  Drag & Drop Chart Builder

Create charts using an intuitive drag-and-drop interface.

Current capabilities include:

- Drag Dimensions to X-Axis
- Drag Metrics to Y-Axis
- Aggregation selection
- Interactive chart rendering
- Chart configuration editor

Supported chart types include:

- Bar Chart
- Line Chart

Additional chart types are planned.

---

##  Dashboard Builder

Build interactive analytics dashboards.

Features:

- Multiple dashboards
- Import saved charts
- Dashboard canvas
- Widget system
- Responsive layout
- Dashboard management

---

##  Modern UI

- Glassmorphism Design
- Responsive Layout
- Dark Theme
- Smooth animations
- Professional BI-inspired interface

Primary Color

```
#98A5D4
```

---

#  Architecture

```
Frontend (React)

        │

        ▼

FastAPI Backend

        │

        ▼

Upload Service

        │

        ▼

Pandas DataFrame Manager

        │

        ▼

Profiling Engine

        │

        ▼

Semantic Classification Engine

        │

        ▼

Relationship Engine

        │

        ▼

Aggregation Engine

        │

        ▼

Visualization Engine

        │

        ▼

Dashboard Engine

        │

        ▼

JSON Response

        │

        ▼

Interactive Dashboard
```

---

#  Project Structure

```text
Veloce-Engine/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── utils/
│   ├── config/
│   ├── core/
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── dashboard/
│   │   ├── charts/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── utils/
│   │   └── types/
│   │
│   ├── public/
│   └── package.json
│
├── data/
├── docs/
├── screenshots/
├── README.md
└── LICENSE
```

---

#  Technology Stack

## Backend

- FastAPI
- Python
- Pandas
- NumPy
- Pydantic
- OpenPyXL

---

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Chart.js
- Zustand
- React Grid Layout
- React DnD / dnd-kit

---

## Development Tools

- Git
- GitHub
- VS Code
- Postman

---

#  Getting Started

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/veloce-engine.git

cd veloce-engine
```

---

# Backend Setup

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run FastAPI

```bash
fastapi dev backend/main.py
```

Backend

```
http://127.0.0.1:8000
```

Swagger Docs

```
http://127.0.0.1:8000/docs
```

---

# Frontend Setup

Go to frontend

```bash
cd frontend
```

Install packages

```bash
npm install
```

Run Vite

```bash
npm run dev
```

Frontend

```
http://localhost:5173
```

---

# Current Workflow

```
Upload Dataset

↓

Automatic Profiling

↓

Semantic Classification

↓

Drag & Drop Fields

↓

Create Charts

↓

Save Charts

↓

Create Dashboard

↓

Import Charts

↓

Interactive Analytics Dashboard
```

---

# Screenshots

> Add screenshots inside the `screenshots/` folder.

Example:

```
screenshots/

dashboard.png

chart-builder.png

dataset-upload.png

dashboard-builder.png
```

---

# Roadmap

## Completed

- CSV Upload
- Excel Upload
- Dataset Preview
- Data Profiling
- Semantic Detection
- Drag & Drop Chart Builder
- Dashboard Builder
- Saved Charts
- Multiple Dashboards

---

## In Progress

- Dashboard Widget Management
- Drag & Resize Widgets
- Snap-to-Grid Layout
- Dashboard Persistence
- Responsive Dashboard Canvas

---

## Planned

- Multi-file Relationships
- Automatic Join Detection
- Pivot Tables
- KPI Cards
- Advanced Charts
- AI Insights
- Dashboard Templates
- Report Export
- Dashboard Sharing
- Authentication
- Role-Based Access Control
- Real-time Dashboards
- Predictive Analytics
- Embedded Analytics
- REST API for Integrations

---

# Design Principles

- Modular Architecture
- Enterprise Ready
- Production Quality
- Responsive UI
- Reusable Components
- Semantic Data Modeling
- Separation of Concerns

---

# Why Veloce Engine?

Unlike traditional BI tools, Veloce Engine is designed with an **AI-first architecture**. Instead of relying solely on manual configuration, it uses semantic understanding of datasets to enable intelligent analytics while keeping users in control through a drag-and-drop workflow.

The long-term vision is to evolve Veloce Engine into a comprehensive self-service analytics platform with AI-assisted insights, reusable dashboard components, collaboration features, and enterprise-grade scalability.

---

#  Contributing

Contributions, feature requests, and bug reports are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/new-feature
```

3. Commit changes

```bash
git commit -m "Add new feature"
```

4. Push branch

```bash
git push origin feature/new-feature
```

5. Open a Pull Request

---

#  License

This project is licensed under the **MIT License**.

---

#  Author

**Ghaffar Buzdar**

Machine Learning • Data Science • AI • Business Intelligence • Full Stack Development

---

#  Support

If you found this project useful, consider giving it a  on GitHub to support its development.

## Quick Links
- [Installation Guide](INSTALL.md)
- [Run Guide](RUN.md)
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/33571ccc-08bc-45d5-835d-6652587f007d" />
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/9a417fed-c4e5-461a-8d31-f69e447e0651" />
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/8a4cba1b-6907-41b0-85e3-4e724aa2f38c" />
