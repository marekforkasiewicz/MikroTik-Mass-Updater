# MikroTik Mass Updater - Dokumentacja Systemu

## Spis treści

1. [Przegląd systemu](#przegląd-systemu)
2. [Architektura](#architektura)
3. [API Endpoints](#api-endpoints)
4. [WebSocket](#websocket)
5. [Modele danych](#modele-danych)
6. [Autentykacja i uprawnienia](#autentykacja-i-uprawnienia)
7. [Frontend](#frontend)
8. [Konfiguracja](#konfiguracja)

---

## Przegląd systemu

MikroTik Mass Updater to aplikacja do masowego zarządzania routerami MikroTik. Umożliwia:

- **Zarządzanie routerami** - dodawanie, edycja, usuwanie, grupowanie
- **Skanowanie sieci** - wykrywanie routerów przez MNDP, sprawdzanie statusu
- **Aktualizacje** - RouterOS i firmware, zmiana kanału aktualizacji
- **Automatyzacja** - harmonogramy zadań, skrypty, kopie zapasowe
- **Monitoring** - alerty, health checks, dashboardy
- **Notyfikacje** - email, Slack, webhooki
- **Raporty** - eksport CSV, XLSX, PDF, JSON

### Stack technologiczny

| Warstwa | Technologia |
|---------|-------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| Frontend | Vue 3, Pinia, Bootstrap 5 |
| Baza danych | SQLite (default) / PostgreSQL |
| Komunikacja z routerami | librouteros (API), paramiko (SSH) |
| WebSocket | FastAPI WebSocket |

---

## Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Vue 3)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │
│  │  Dashboard  │ │ RouterList  │ │ BatchOps    │ │ Settings  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘  │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Pinia Stores (State Management)            │    │
│  │  main | auth | groups | schedules | monitoring | notif  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              ↓                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              API Client (Axios) + WebSocket             │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               ↓ HTTP/WS
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Routes (/api/*)                   │   │
│  │  routers | scan | tasks | auth | users | groups | ...    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Services                            │   │
│  │  RouterService | ScanService | UpdateService | SSHService│   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   SQLAlchemy ORM                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                     MikroTik Routers                            │
│              API (port 8728) | SSH (port 22)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

Wszystkie endpointy używają prefiksu `/api`. Dokumentacja interaktywna dostępna pod `/api/docs` (Swagger) i `/api/redoc`.

### System

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/api` | Informacje o API i dostępnych endpointach |
| GET | `/api/health` | Health check - `{"status": "healthy"}` |

### Autentykacja (`/api/auth`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/auth/login` | Logowanie (form data: username, password) |
| POST | `/auth/login/json` | Logowanie (JSON body) |
| POST | `/auth/refresh` | Odświeżenie tokena |
| POST | `/auth/logout` | Wylogowanie |
| GET | `/auth/me` | Informacje o zalogowanym użytkowniku |
| POST | `/auth/change-password` | Zmiana hasła |

**Odpowiedź logowania:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

### Użytkownicy (`/api/users`)

| Metoda | Endpoint | Opis | Uprawnienia |
|--------|----------|------|-------------|
| GET | `/users` | Lista użytkowników | Admin |
| POST | `/users` | Tworzenie użytkownika | Admin |
| GET | `/users/{id}` | Szczegóły użytkownika | Admin/Self |
| PUT | `/users/{id}` | Aktualizacja użytkownika | Admin/Self |
| DELETE | `/users/{id}` | Usunięcie użytkownika | Admin |
| GET | `/users/me/api-keys` | Lista kluczy API | Auth |
| POST | `/users/me/api-keys` | Tworzenie klucza API | Auth |
| DELETE | `/users/me/api-keys/{id}` | Usunięcie klucza API | Auth |

### Routery (`/api/routers`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/routers` | Lista routerów z statystykami |
| POST | `/routers` | Dodanie nowego routera |
| GET | `/routers/{id}` | Szczegóły routera |
| PUT | `/routers/{id}` | Aktualizacja routera |
| DELETE | `/routers/{id}` | Usunięcie routera |
| POST | `/routers/import` | Import z formatu list.txt |
| POST | `/routers/import-file` | Import z pliku list.txt |
| POST | `/routers/{id}/change-channel` | Zmiana kanału aktualizacji (SSH) |

**Odpowiedź listy routerów:**
```json
{
  "routers": [
    {
      "id": 1,
      "ip": "192.168.1.2",
      "port": 8728,
      "identity": "Router_Main",
      "model": "hAP ax^3",
      "ros_version": "7.22beta6 (testing)",
      "firmware": "7.22beta6",
      "upgrade_firmware": "7.22beta6",
      "update_channel": "development",
      "installed_version": "7.22beta6",
      "latest_version": "7.22beta6",
      "is_online": true,
      "has_updates": false,
      "has_firmware_update": false,
      "last_seen": "2026-02-01T15:30:00Z"
    }
  ],
  "total": 8,
  "online": 8,
  "offline": 0,
  "needs_update": 1
}
```

**Zmiana kanału aktualizacji:**
```
POST /api/routers/22/change-channel?channel=stable
```

Kanały: `stable`, `long-term`, `testing`, `development`

### Skanowanie (`/api/scan`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/scan/quick` | Szybki skan (ping, porty) |
| POST | `/scan/full` | Pełny skan (wszystkie informacje) |
| GET | `/scan/quick/single/{id}` | Szybki skan pojedynczego routera |
| GET | `/scan/firmware/{id}` | Sprawdzenie firmware |

**Quick scan sprawdza:**
- Ping (dostępność)
- Port API (8728)
- Port SSH (22)
- Podstawowe info RouterOS

**Full scan zbiera:**
- Identity, model, architektura
- Wersja RouterOS i firmware
- Kanał aktualizacji
- Dostępne aktualizacje
- Uptime, pamięć

### Discovery (`/api/discovery`)

Wykrywanie routerów przez protokół MNDP (MikroTik Neighbor Discovery Protocol).

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/discovery` | Skanowanie MNDP |
| GET | `/discovery/cached` | Wyniki z cache |
| POST | `/discovery/clear-cache` | Czyszczenie cache |
| POST | `/discovery/add/{mac}` | Dodanie znalezionego routera |

**Parametry discovery:**
- `timeout` (1-30 sekund, default: 5)
- `force` (bypass cache)

### Zadania (`/api/tasks`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/tasks` | Lista zadań |
| POST | `/tasks` | Tworzenie zadania |
| GET | `/tasks/{id}` | Status zadania |
| POST | `/tasks/{id}/cancel` | Anulowanie zadania |
| DELETE | `/tasks/{id}` | Usunięcie zadania |
| POST | `/tasks/update` | Start aktualizacji |

**Konfiguracja aktualizacji:**
```json
{
  "router_ids": [1, 2, 3],
  "update_tree": "stable",
  "auto_change_tree": false,
  "upgrade_firmware": true,
  "cloud_backup": false,
  "dry_run": false,
  "timeout": 300
}
```

**Logi zadań:**

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/tasks/logs/files` | Lista plików logów |
| GET | `/tasks/logs/files/{name}` | Zawartość logu |
| GET | `/tasks/logs/files/{name}/raw` | Surowy log |
| DELETE | `/tasks/logs/files/{name}` | Usunięcie logu |
| DELETE | `/tasks/logs/cleanup?days=30` | Czyszczenie starych logów |
| GET | `/tasks/logs/statistics` | Statystyki logów |

### Wersje (`/api/versions`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/versions` | Aktualne wersje RouterOS |
| GET | `/versions/refresh` | Odświeżenie cache (TTL: 5 min) |

**Odpowiedź:**
```json
{
  "stable": {
    "version": "7.21.2",
    "release_date": "2026-01-15"
  },
  "long-term": {
    "version": "6.49.17",
    "release_date": "2026-01-10"
  },
  "testing": {
    "version": "7.22rc1",
    "release_date": "2026-01-28"
  },
  "development": {
    "version": "7.22beta6",
    "release_date": "2026-01-30"
  }
}
```

### Grupy (`/api/groups`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/groups` | Lista grup |
| GET | `/groups/tree` | Drzewo hierarchiczne |
| POST | `/groups` | Tworzenie grupy |
| GET | `/groups/{id}` | Szczegóły grupy z routerami |
| PUT | `/groups/{id}` | Aktualizacja grupy |
| DELETE | `/groups/{id}` | Usunięcie grupy |
| POST | `/groups/{id}/routers` | Dodanie routerów do grupy |
| DELETE | `/groups/{id}/routers` | Usunięcie routerów z grupy |
| GET | `/groups/{id}/routers` | Lista routerów w grupie |
| GET | `/groups/search/{query}` | Wyszukiwanie grup |

### Dashboard (`/api/dashboard`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/dashboard` | Pełne dane dashboardu |
| GET | `/dashboard/stats` | Szybkie statystyki |
| GET | `/dashboard/charts/{type}` | Dane wykresu |
| GET | `/dashboard/time-series/{metric}` | Dane czasowe |
| GET | `/dashboard/uptime/{router_id}` | Historia uptime |
| GET | `/dashboard/activity` | Ostatnia aktywność |
| GET | `/dashboard/schedules` | Nadchodzące harmonogramy |
| GET | `/dashboard/system-status` | Status systemu |

**Typy wykresów:** `version_pie`, `model_bar`, `status_doughnut`, `health_pie`

**Metryki time-series:** `latency`, `cpu`, `memory`, `disk`

### Harmonogramy (`/api/schedules`)

Wymaga: `FEATURE_SCHEDULING=true`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/schedules` | Lista harmonogramów |
| POST | `/schedules` | Tworzenie harmonogramu |
| GET | `/schedules/cron-describe?cron=...` | Opis cron |
| GET | `/schedules/{id}` | Szczegóły harmonogramu |
| PUT | `/schedules/{id}` | Aktualizacja |
| DELETE | `/schedules/{id}` | Usunięcie |
| POST | `/schedules/{id}/enable` | Włączenie |
| POST | `/schedules/{id}/disable` | Wyłączenie |
| POST | `/schedules/{id}/run-now` | Natychmiastowe uruchomienie |
| GET | `/schedules/{id}/executions` | Historia wykonań |

**Tworzenie harmonogramu:**
```json
{
  "name": "Nightly Backup",
  "type": "backup",
  "description": "Codzienna kopia zapasowa",
  "cron_expression": "0 2 * * *",
  "enabled": true,
  "router_ids": [1, 2, 3],
  "config": {
    "backup_type": "full",
    "includes_passwords": false
  }
}
```

### Backup i Rollback (`/api/backups`)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/backups` | Lista kopii zapasowych |
| POST | `/backups` | Tworzenie kopii |
| POST | `/backups/bulk` | Masowe tworzenie |
| GET | `/backups/{id}` | Szczegóły kopii |
| DELETE | `/backups/{id}` | Usunięcie kopii |
| GET | `/backups/{id}/download` | Pobranie pliku |
| POST | `/backups/restore` | Przywracanie |
| GET | `/backups/rollback-logs` | Historia rollback |
| POST | `/backups/cleanup?days=30` | Czyszczenie |

### Monitoring (`/api/monitoring`)

Wymaga: `FEATURE_MONITORING=true`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/monitoring/overview` | Przegląd monitoringu |
| GET | `/monitoring/config` | Konfiguracja globalna |
| PUT | `/monitoring/config` | Aktualizacja konfiguracji |
| GET | `/monitoring/routers/{id}/config` | Konfiguracja routera |
| POST | `/monitoring/routers/{id}/check` | Uruchomienie health check |
| GET | `/monitoring/routers/{id}/history` | Historia health |
| GET | `/monitoring/alerts` | Lista alertów |
| GET | `/monitoring/alerts/active` | Aktywne alerty |
| POST | `/monitoring/alerts/acknowledge` | Potwierdzenie alertów |
| POST | `/monitoring/alerts/resolve` | Rozwiązanie alertów |

### Notyfikacje (`/api/notifications`)

Wymaga: `FEATURE_NOTIFICATIONS=true`

**Kanały:**

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/notifications/channels` | Lista kanałów |
| POST | `/notifications/channels` | Tworzenie kanału |
| PUT | `/notifications/channels/{id}` | Aktualizacja |
| DELETE | `/notifications/channels/{id}` | Usunięcie |
| POST | `/notifications/channels/{id}/test` | Test kanału |

**Reguły:**

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/notifications/rules` | Lista reguł |
| POST | `/notifications/rules` | Tworzenie reguły |
| PUT | `/notifications/rules/{id}` | Aktualizacja |
| DELETE | `/notifications/rules/{id}` | Usunięcie |

**Typy zdarzeń:** `router_offline`, `router_online`, `update_available`, `update_completed`, `update_failed`, `backup_completed`, `backup_failed`, `scan_completed`, `script_executed`, `health_warning`, `health_critical`, `schedule_failed`

### Skrypty (`/api/scripts`)

Wymaga: `FEATURE_SCRIPTS=true`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/scripts` | Lista skryptów |
| POST | `/scripts` | Tworzenie skryptu |
| POST | `/scripts/validate` | Walidacja składni |
| GET | `/scripts/{id}` | Szczegóły skryptu |
| PUT | `/scripts/{id}` | Aktualizacja |
| DELETE | `/scripts/{id}` | Usunięcie |
| POST | `/scripts/{id}/execute` | Wykonanie (1 router) |
| POST | `/scripts/{id}/bulk-execute` | Wykonanie masowe |
| GET | `/scripts/{id}/executions` | Historia wykonań |

### Webhooki (`/api/webhooks`)

Wymaga: `FEATURE_WEBHOOKS=true`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/webhooks` | Lista webhooków |
| GET | `/webhooks/events` | Dostępne zdarzenia |
| POST | `/webhooks` | Tworzenie webhooka |
| PUT | `/webhooks/{id}` | Aktualizacja |
| DELETE | `/webhooks/{id}` | Usunięcie |
| POST | `/webhooks/{id}/test` | Test webhooka |
| GET | `/webhooks/{id}/deliveries` | Historia dostarczeń |
| POST | `/webhooks/{id}/deliveries/{did}/resend` | Ponowne wysłanie |

### Raporty (`/api/reports`)

Wymaga: `FEATURE_REPORTS=true`

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/reports` | Generowanie raportu |
| GET | `/reports` | Lista raportów |
| GET | `/reports/download/{filename}` | Pobranie raportu |
| DELETE | `/reports/{filename}` | Usunięcie raportu |
| GET | `/reports/quick/inventory` | Szybki eksport inventory |
| GET | `/reports/quick/health` | Szybki eksport health |

**Formaty:** CSV, XLSX, PDF, JSON

---

## WebSocket

### Task Progress (`/ws/tasks/{task_id}`)

Śledzenie postępu zadania w czasie rzeczywistym.

```javascript
const ws = new WebSocket('ws://host:8000/ws/tasks/abc-123');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  // {
  //   task_id: "abc-123",
  //   status: "running",
  //   progress: 5,
  //   total: 10,
  //   current_item: "192.168.1.5",
  //   current_message: "Updating router...",
  //   progress_percent: 50
  // }
};
```

### System Status (`/ws/status`)

Aktualizacje statusu systemu co 5 sekund.

```javascript
const ws = new WebSocket('ws://host:8000/ws/status');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // {
  //   type: "status",
  //   routers: {
  //     total: 8,
  //     online: 7,
  //     offline: 1,
  //     needs_update: 2
  //   },
  //   tasks: {
  //     running: 1
  //   }
  // }
};
```

---

## Modele danych

### Router

```python
class Router:
    id: int                      # ID
    ip: str                      # Adres IP
    port: int = 8728             # Port API
    username: str                # Użytkownik
    password: str                # Hasło

    # Informacje z routera
    identity: str                # Nazwa routera
    model: str                   # Model urządzenia
    architecture: str            # Architektura (arm, arm64, x86)
    ros_version: str             # Pełna wersja ROS
    firmware: str                # Wersja firmware
    upgrade_firmware: str        # Dostępna wersja firmware
    update_channel: str          # Kanał aktualizacji
    installed_version: str       # Zainstalowana wersja
    latest_version: str          # Najnowsza wersja w kanale
    uptime: str                  # Czas działania
    memory_total_mb: int         # Pamięć RAM

    # Status
    is_online: bool              # Czy online
    has_updates: bool            # Czy dostępna aktualizacja ROS
    has_firmware_update: bool    # Czy dostępna aktualizacja FW

    # Znaczniki czasu
    last_seen: datetime          # Ostatnio widziany
    last_scan: datetime          # Ostatni skan
    created_at: datetime         # Utworzony
    updated_at: datetime         # Zaktualizowany
```

### Task

```python
class Task:
    id: str                      # UUID
    type: str                    # Typ: scan, quick_scan, update, backup, script
    status: str                  # pending, running, completed, failed, cancelled

    # Konfiguracja
    config: dict                 # Parametry zadania

    # Postęp
    progress: int                # Aktualny postęp
    total: int                   # Łączna liczba elementów
    current_item: str            # Aktualnie przetwarzany element

    # Wyniki
    results: dict                # Wyniki zadania
    error: str                   # Błąd (jeśli failed)

    # Znaczniki czasu
    created_at: datetime
    started_at: datetime
    completed_at: datetime
```

### User

```python
class User:
    id: int
    username: str
    email: str
    password_hash: str
    role: str                    # admin, operator, viewer
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### Group

```python
class Group:
    id: int
    name: str
    description: str
    parent_id: int               # Rodzic (hierarchia)
    created_at: datetime
    updated_at: datetime

    # Relacje
    routers: List[Router]        # Routery w grupie
    children: List[Group]        # Podgrupy
```

---

## Autentykacja i uprawnienia

### Metody autentykacji

1. **JWT Bearer Token** - nagłówek `Authorization: Bearer <token>`
2. **HttpOnly Cookies** - `access_token` i `refresh_token`
3. **API Keys** - nagłówek `X-API-Key: <key>`

### Role i uprawnienia

| Rola | Opis |
|------|------|
| **admin** | Pełne uprawnienia |
| **operator** | Zarządzanie routerami, skanowanie, aktualizacje |
| **viewer** | Tylko odczyt |

**Uprawnienia szczegółowe:**

| Uprawnienie | Admin | Operator | Viewer |
|-------------|-------|----------|--------|
| VIEW_ROUTERS | ✓ | ✓ | ✓ |
| MANAGE_ROUTERS | ✓ | ✓ | - |
| RUN_SCANS | ✓ | ✓ | - |
| RUN_UPDATES | ✓ | ✓ | - |
| MANAGE_GROUPS | ✓ | ✓ | - |
| MANAGE_SCHEDULES | ✓ | ✓ | - |
| CREATE_BACKUPS | ✓ | ✓ | - |
| RESTORE_BACKUPS | ✓ | ✓ | - |
| DELETE_BACKUPS | ✓ | ✓ | - |
| VIEW_SCRIPTS | ✓ | ✓ | ✓ |
| MANAGE_SCRIPTS | ✓ | - | - |
| EXECUTE_SCRIPTS | ✓ | ✓ | - |
| MANAGE_USERS | ✓ | - | - |
| MANAGE_NOTIFICATIONS | ✓ | ✓ | - |
| MANAGE_MONITORING | ✓ | ✓ | - |
| MANAGE_WEBHOOKS | ✓ | ✓ | - |
| EXPORT_REPORTS | ✓ | ✓ | - |

---

## Frontend

### Struktura komponentów

```
src/
├── components/
│   ├── Dashboard.vue          # Strona główna
│   ├── RouterList.vue         # Lista routerów
│   ├── GroupList.vue          # Grupy routerów
│   ├── BatchOperations.vue    # Skanowanie, aktualizacje, skrypty
│   ├── Automation.vue         # Harmonogramy, backupy, historia
│   ├── Settings.vue           # Notyfikacje, webhooki, użytkownicy
│   ├── ReportsAndLogs.vue     # Raporty i logi
│   ├── MonitoringDashboard.vue # Monitoring i alerty
│   ├── LoginPage.vue          # Logowanie
│   └── shared/
│       ├── StatCard.vue       # Karta statystyk
│       ├── ProgressTracker.vue # Pasek postępu
│       └── ConsoleOutput.vue  # Wyjście konsoli
├── stores/
│   ├── main.js                # Główny store (routery, zadania, UI)
│   ├── auth.js                # Autentykacja
│   ├── groups.js              # Grupy
│   ├── schedules.js           # Harmonogramy
│   ├── monitoring.js          # Monitoring
│   └── notifications.js       # Notyfikacje
├── services/
│   └── api.js                 # Klient API
└── router/
    └── index.js               # Routing
```

### Routing

| Ścieżka | Komponent | Wymagana rola |
|---------|-----------|---------------|
| `/login` | LoginPage | - |
| `/` | Dashboard | any |
| `/routers` | RouterList | any |
| `/groups` | GroupList | any |
| `/operations` | BatchOperations | operator+ |
| `/automation` | Automation | operator+ |
| `/monitoring` | MonitoringDashboard | any |
| `/reports` | ReportsAndLogs | any |
| `/settings` | Settings | admin |

### Pinia Stores

**main.js** - główny store:
- `routers` - lista routerów
- `routerStats` - statystyki
- `tasks` - zadania
- `selectedRouterIds` - zaznaczone routery
- `notifications` - powiadomienia toast
- `theme` - motyw (dark/light)

**auth.js** - autentykacja:
- `user` - zalogowany użytkownik
- `isAuthenticated` - status
- `hasPermission(perm)` - sprawdzanie uprawnień

---

## Konfiguracja

### Zmienne środowiskowe

```bash
# Baza danych
DATABASE_URL=sqlite:///./data/mikrotik.db

# Bezpieczeństwo
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Domyślne dane logowania do routerów
DEFAULT_USERNAME=admin
DEFAULT_PASSWORD=

# Feature flags
FEATURE_SCHEDULING=true
FEATURE_MONITORING=true
FEATURE_NOTIFICATIONS=true
FEATURE_SCRIPTS=true
FEATURE_WEBHOOKS=true
FEATURE_REPORTS=true

# Serwer
HOST=0.0.0.0
PORT=8000
API_PREFIX=/api
```

### Format pliku list.txt

```
# Komentarz
192.168.1.1:8728:admin:password
192.168.1.2         # Domyślne dane
192.168.1.3:8728    # Tylko port
```

Format: `IP[:PORT[:USERNAME[:PASSWORD]]]`

---

## Kody błędów HTTP

| Kod | Znaczenie |
|-----|-----------|
| 200 | OK - sukces |
| 201 | Created - zasób utworzony |
| 204 | No Content - sukces bez treści |
| 400 | Bad Request - nieprawidłowe dane |
| 401 | Unauthorized - brak autoryzacji |
| 403 | Forbidden - brak uprawnień |
| 404 | Not Found - nie znaleziono |
| 409 | Conflict - konflikt (np. IP już istnieje) |
| 500 | Internal Server Error - błąd serwera |

---

## Przykłady użycia API

### Logowanie i pobieranie routerów

```bash
# Logowanie
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=admin" \
  -c cookies.txt

# Lista routerów
curl http://localhost:8000/api/routers \
  -b cookies.txt

# Szybki skan
curl -X POST http://localhost:8000/api/scan/quick \
  -b cookies.txt

# Zmiana kanału
curl -X POST "http://localhost:8000/api/routers/1/change-channel?channel=stable" \
  -b cookies.txt
```

### Aktualizacja routerów

```bash
curl -X POST http://localhost:8000/api/tasks/update \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "router_ids": [1, 2, 3],
    "upgrade_firmware": true,
    "dry_run": false
  }'
```

---

*Dokumentacja wygenerowana: 2026-02-01*
