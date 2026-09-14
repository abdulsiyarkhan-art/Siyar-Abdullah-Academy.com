# Siyar Abdullah Academy

An online learning academy — courses in programming, web development, AI, data science, and digital skills, founded by Siyar Abdullah.

This project has two parts:

1. **`index.html`** — a complete, standalone frontend demo. Open it directly in any browser. All data (courses, enrollments, admin actions) lives in memory in JavaScript and resets on refresh — there is no live database behind it yet.
2. **`app.py`** — a real Flask + SQLAlchemy backend (models, REST API, authentication) that matches the frontend's data shape. It is not wired to `index.html` automatically; the two are provided as a matched pair so you can connect them.

## Viewing the frontend

Just open `index.html` in a browser — no build step, no server required. Try:
- Browsing and filtering courses (`Courses`)
- Opening a course, expanding the curriculum, and enrolling
- Logging in with **any** email/password (demo auth) — or `admin@siyarabdullah.academy` to see the Admin Dashboard
- Enrolling in a course and marking lessons complete on the learning page
- Creating a course from the Admin → Create Course form

## Running the backend

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and set a real `SECRET_KEY` and `SEED_ADMIN_PASSWORD`. Never commit `.env` to version control.

### 3. Set up the database
For local development, SQLite works out of the box with the default `DATABASE_URL`. For production, set `DATABASE_URL` to a PostgreSQL connection string, e.g.:
```
postgresql://username:password@localhost:5432/siyar_academy
```

Create the tables and seed initial data (an admin account and categories):
```bash
export FLASK_APP=app.py       # Windows: set FLASK_APP=app.py
flask seed
```

### 4. Run the server
```bash
flask --app app run --debug
```
The API is now available at `http://127.0.0.1:5000/api/...`.

## API overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create a student account |
| POST | `/api/auth/login` | Log in |
| POST | `/api/auth/logout` | Log out |
| GET  | `/api/auth/me` | Get current user |
| GET  | `/api/courses` | List published courses (supports `?category=`, `?difficulty=`, `?q=`) |
| GET  | `/api/courses/:id` | Course details with full curriculum |
| POST | `/api/courses` | Create a course (admin only) |
| PUT  | `/api/courses/:id` | Update a course (admin only) |
| DELETE | `/api/courses/:id` | Delete a course (admin only) |
| GET  | `/api/categories` | List categories |
| POST | `/api/categories` | Create a category (admin only) |
| POST | `/api/enrollments` | Enroll the current user in a course |
| GET  | `/api/user/courses` | Current user's enrolled courses + progress |
| POST | `/api/user/progress` | Mark a lesson complete |
| POST | `/api/courses/:id/reviews` | Submit a course review |
| POST | `/api/contact` | Submit a contact form message |
| POST | `/api/uploads` | Upload a file (admin only) |
| GET  | `/api/admin/summary` | Admin dashboard stats (admin only) |

## Connecting the frontend to the backend

`index.html` currently calls its own in-memory JavaScript functions (`login()`, `enroll()`, etc.). To go live:
1. Serve `index.html` from the same origin as the Flask app (or configure CORS with `flask-cors`).
2. Replace the in-memory functions in the `<script>` block with `fetch()` calls to the endpoints above.
3. Replace the hardcoded `COURSES`, `CATEGORIES`, and `INSTRUCTORS` arrays with data loaded from `/api/courses`, `/api/categories`, etc. on page load.

## Security notes

- Passwords are hashed with Werkzeug's `generate_password_hash` — never store plaintext passwords.
- Set a strong, random `SECRET_KEY` in production.
- Admin-only routes are protected by the `@admin_required` decorator, which checks the logged-in user's `role`.
- File uploads are restricted by extension and size (`MAX_CONTENT_LENGTH`); validate further before serving uploads publicly.
- Use HTTPS and secure, `HttpOnly` cookies in production (configure `SESSION_COOKIE_SECURE=True`).

## Project structure
```
.
├── index.html          # Standalone frontend demo (open directly in a browser)
├── app.py              # Flask backend: models, auth, REST API
├── requirements.txt    # Python dependencies
├── .env.example         # Environment variable template
└── README.md
```
