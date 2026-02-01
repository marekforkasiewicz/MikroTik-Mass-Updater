# MikroTik Mass Updater

A web-based application for managing and mass-updating MikroTik routers.

## Features

- **Dashboard**: Overview of all routers with status indicators
- **Router Management**: Add, edit, delete, and import routers from `list.txt`
- **Network Scanning**:
  - Quick Scan: Ping, port check (API/SSH), basic info
  - Full Scan: Complete router information via API
- **Mass Updates**:
  - Update RouterOS to latest version
  - Upgrade firmware
  - Auto-change update tree via SSH
  - Cloud backup before update
  - Dry-run mode
- **Real-time Progress**: WebSocket-based live updates
- **Task History**: Track all operations

## Quick Start

### Option 1: Python (Development)

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install

# Build frontend
npm run build

# Run application
cd ..
python run.py
```

Open http://localhost:8000

### Option 2: Docker

```bash
cd docker
docker-compose up -d
```

Open http://localhost:8080

## Project Structure

```
MikroTik-Mass-Updater/
├── backend/
│   ├── app/
│   │   ├── api/          # REST API endpoints
│   │   ├── core/         # Enums, constants
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── config.py     # Configuration
│   │   ├── database.py   # Database setup
│   │   └── main.py       # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Vue components
│   │   ├── services/     # API client
│   │   └── stores/       # Pinia store
│   ├── package.json
│   └── vite.config.js
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── data/                 # SQLite database
├── list.txt              # Router list
└── run.py               # Startup script
```

## Configuration

### Router List Format (list.txt)

```
# Format: IP[:PORT][|USERNAME|PASSWORD]

# Default port (8728) with custom credentials
192.168.1.1|admin|password

# Custom port
192.168.1.2:8729|admin|password

# Comments are supported
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/mikrotik.db` | Database connection URL |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEFAULT_USERNAME` | - | Default API username |
| `DEFAULT_PASSWORD` | - | Default API password |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/routers` | GET | List all routers |
| `/api/routers` | POST | Add a router |
| `/api/routers/{id}` | GET/PUT/DELETE | Router CRUD |
| `/api/routers/import` | POST | Import from list.txt format |
| `/api/routers/import-file` | POST | Import from list.txt file |
| `/api/scan/quick` | POST | Start quick scan |
| `/api/scan/full` | POST | Start full scan |
| `/api/tasks` | GET/POST | Task management |
| `/api/tasks/{id}` | GET | Task status |
| `/api/tasks/{id}/cancel` | POST | Cancel task |
| `/api/tasks/update` | POST | Start update task |
| `/ws/tasks/{task_id}` | WebSocket | Real-time task progress |

API documentation: http://localhost:8000/api/docs

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies API requests to the backend.

## Legacy CLI

The original CLI scripts are preserved:
- `mikrotik_menu_v3.0.py` - ncurses menu interface
- `mikrotik_mass_updater_v5.3.0_REPORT.py` - command-line updater

## License

MIT License
