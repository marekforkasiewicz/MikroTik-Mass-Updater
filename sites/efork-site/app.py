from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('EFORK_SITE_DB', '/data/client_zone.db'))
DEFAULT_CLIENT_ZONE_USER = os.environ.get('EFORK_SITE_CLIENT_USER', 'admin')
DEFAULT_CLIENT_ZONE_PASSWORD = os.environ.get('EFORK_SITE_CLIENT_PASSWORD', 'admin')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('EFORK_SITE_SECRET_KEY', 'efork-site-dev-secret')


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    company_name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    contact_email TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    project_type TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    summary TEXT,
    stack TEXT,
    view_title TEXT,
    view_body TEXT,
    embed_url TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (client_id, slug),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_access_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""


SEED_SQL = """
INSERT OR IGNORE INTO clients (slug, name, company_name, status, contact_email, note)
VALUES
    ('infoveto', 'Infoveto', 'Infoveto', 'active', 'kontakt@infoveto.pl', 'Wewnętrzny wpis startowy do strefy klienta');

INSERT OR IGNORE INTO projects (
    client_id, slug, name, project_type, status, summary, stack, view_title, view_body, embed_url
)
SELECT
    c.id,
    'multifarm',
    'Multifarm PBX',
    'system komunikacji z pacjentem',
    'active',
    'System do automatycznych połączeń i SMS-ów związanych z receptami, oparty o scenariusze IVR, przyciski DTMF, kolejkę połączeń i integrację z FreePBX.',
    'FreePBX, Asterisk, FastAPI, Vue, SMS, IVR',
    'Projekt: Multifarm PBX',
    'Multifarm PBX obsługuje automatyczne kampanie głosowe i SMS dotyczące recept. Kluczowa logika projektu działa na przyciskach IVR: wybór pacjenta uruchamia konkretną akcję, na przykład wysłanie SMS, powtórzenie komunikatu albo przejście do kolejnej recepty. System planuje połączenia, generuje komunikaty i zapisuje historię kontaktu z pacjentem.',
    'https://multifarm.efork.pl/'
FROM clients c
WHERE c.slug = 'infoveto';
"""


def get_db() -> sqlite3.Connection:
    if 'db' not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(SCHEMA_SQL)
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(projects)").fetchall()
        }
        if 'embed_url' not in columns:
            conn.execute("ALTER TABLE projects ADD COLUMN embed_url TEXT")
        conn.executescript(SEED_SQL)
        conn.execute(
            """
            UPDATE projects
            SET
                name = 'Multifarm PBX',
                project_type = 'system komunikacji z pacjentem',
                summary = 'System do automatycznych połączeń i SMS-ów związanych z receptami, oparty o scenariusze IVR, przyciski DTMF, kolejkę połączeń i integrację z FreePBX.',
                stack = 'FreePBX, Asterisk, FastAPI, Vue, SMS, IVR',
                view_title = 'Projekt: Multifarm PBX',
                view_body = 'Multifarm PBX obsługuje automatyczne kampanie głosowe i SMS dotyczące recept. Kluczowa logika projektu działa na przyciskach IVR: wybór pacjenta uruchamia konkretną akcję, na przykład wysłanie SMS, powtórzenie komunikatu albo przejście do kolejnej recepty. System planuje połączenia, generuje komunikaty i zapisuje historię kontaktu z pacjentem.',
                embed_url = 'https://multifarm.efork.pl/'
            WHERE slug = 'multifarm'
            """
        )
        conn.execute(
            """
            DELETE FROM projects
            WHERE slug = 'efork-landing'
            """
        )
        project = conn.execute(
            """
            SELECT id
            FROM projects
            WHERE slug = 'multifarm'
            """
        ).fetchone()
        if project:
            existing = conn.execute(
                """
                SELECT id
                FROM project_access_accounts
                WHERE username = ?
                """,
                (DEFAULT_CLIENT_ZONE_USER,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE project_access_accounts
                    SET project_id = ?, status = 'active'
                    WHERE id = ?
                    """,
                    (project[0], existing[0]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO project_access_accounts (project_id, username, password_hash, status)
                    VALUES (?, ?, ?, 'active')
                    """,
                    (
                        project[0],
                        DEFAULT_CLIENT_ZONE_USER,
                        generate_password_hash(DEFAULT_CLIENT_ZONE_PASSWORD),
                    ),
                )
        conn.commit()


@app.teardown_appcontext
def close_db(_error: object | None) -> None:
    db = g.pop('db', None)
    if db is not None:
        db.close()


def fetch_projects(client_slug: str) -> tuple[dict, list[dict]]:
    client = get_db().execute(
        """
        SELECT slug, name, company_name, status, contact_email, note
        FROM clients
        WHERE slug = ?
        """,
        (client_slug,),
    ).fetchone()
    if not client:
        abort(404)

    projects = get_db().execute(
        """
        SELECT
            p.slug,
            p.name,
            p.project_type,
            p.status,
            p.summary,
            p.stack,
            p.view_title,
            p.view_body,
            p.embed_url,
            p.updated_at
        FROM projects p
        JOIN clients c ON c.id = p.client_id
        WHERE c.slug = ?
        ORDER BY p.name COLLATE NOCASE
        """,
        (client_slug,),
    ).fetchall()
    return dict(client), [dict(row) for row in projects]


def fetch_access_account(username: str) -> dict | None:
    row = get_db().execute(
        """
        SELECT
            paa.id,
            paa.username,
            paa.password_hash,
            paa.status,
            p.id AS project_id,
            p.slug AS project_slug,
            c.slug AS client_slug
        FROM project_access_accounts paa
        JOIN projects p ON p.id = paa.project_id
        JOIN clients c ON c.id = p.client_id
        WHERE paa.username = ?
        """,
        (username,),
    ).fetchone()
    return dict(row) if row else None


def get_session_access() -> dict | None:
    account_id = session.get('client_zone_account_id')
    if not account_id:
        return None
    row = get_db().execute(
        """
        SELECT
            paa.id,
            paa.username,
            paa.status,
            p.id AS project_id,
            p.slug AS project_slug,
            c.slug AS client_slug
        FROM project_access_accounts paa
        JOIN projects p ON p.id = paa.project_id
        JOIN clients c ON c.id = p.client_id
        WHERE paa.id = ?
        """,
        (account_id,),
    ).fetchone()
    return dict(row) if row else None


def require_client_zone_auth():
    access = get_session_access()
    if not access or access.get('status') != 'active':
        session.pop('client_zone_account_id', None)
        return redirect(url_for('client_zone_login', next=request.path))
    return access


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/strefa-klienta')
def client_zone():
    access = require_client_zone_auth()
    if not isinstance(access, dict):
        return access
    return redirect(url_for('project_view', client_slug=access['client_slug'], project_slug=access['project_slug']))


@app.route('/strefa-klienta/login', methods=['GET', 'POST'])
def client_zone_login():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        account = fetch_access_account(username)
        if account and account['status'] == 'active' and check_password_hash(account['password_hash'], password):
            session['client_zone_account_id'] = account['id']
            target = request.args.get('next') or url_for('client_zone')
            return redirect(target)
        error = 'Nieprawidłowy login lub hasło.'
    return render_template('client_zone_login.html', error=error)


@app.post('/strefa-klienta/logout')
def client_zone_logout():
    session.pop('client_zone_account_id', None)
    return redirect(url_for('client_zone_login'))


@app.get('/strefa-klienta/<client_slug>')
def client_projects(client_slug: str):
    access = require_client_zone_auth()
    if not isinstance(access, dict):
        return access
    if access['client_slug'] != client_slug:
        abort(403)
    client, projects = fetch_projects(client_slug)
    return render_template('client_projects.html', client=client, projects=projects)


@app.get('/strefa-klienta/<client_slug>/<project_slug>')
def project_view(client_slug: str, project_slug: str):
    access = require_client_zone_auth()
    if not isinstance(access, dict):
        return access
    if access['client_slug'] != client_slug or access['project_slug'] != project_slug:
        abort(403)
    client, projects = fetch_projects(client_slug)
    project = next((item for item in projects if item['slug'] == project_slug), None)
    if not project:
        abort(404)
    return render_template('project_view.html', client=client, project=project)


@app.get('/api/client-zone/clients')
def api_clients():
    access = require_client_zone_auth()
    if not isinstance(access, dict):
        abort(401)
    client, projects = fetch_projects(access['client_slug'])
    return jsonify({'client': client, 'projects': projects})


@app.get('/api/client-zone/<client_slug>/projects')
def api_projects(client_slug: str):
    access = require_client_zone_auth()
    if not isinstance(access, dict):
        abort(401)
    if access['client_slug'] != client_slug:
        abort(403)
    client, projects = fetch_projects(client_slug)
    return jsonify({'client': client, 'projects': projects})


init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
