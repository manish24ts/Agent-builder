# Agent Builder

A ChatGPT-style app: sign in, create your own agents (system prompt, model, tools),
chat with them, and everything is saved to Postgres.

- **Backend**: FastAPI + SQLAlchemy (async) + LangGraph + Groq, JWT auth, Google Sign-In
- **Frontend**: React (Vite), streaming chat over SSE

## What was already here vs. what was added

The repo you uploaded had the DB models, the LangGraph agent, the tool registry, and a
single `/chat/stream` route — but no auth, no CRUD for agents/conversations, no app
entrypoint, and no frontend. This pass added:

- `backend/db/models.py` — new `User` table; `Agent`/`Conversation.user_id` are now real
  foreign keys to `users.id`
- `backend/core/` — `config.py` (env settings), `security.py` (password hashing + JWT)
- `backend/api/deps.py` — `get_current_user` dependency (Bearer JWT)
- `backend/api/auth_routes.py` — register, login, Google sign-in, `/auth/me`
- `backend/api/agent_routes.py` — CRUD for a user's agents + `/agents/tools`
- `backend/api/conversation_routes.py` — CRUD for a user's conversations + message history
- `backend/api/chat_routes.py` — now requires auth and checks conversation ownership
- `backend/main.py` — the FastAPI app, wires all routers + CORS
- `backend/alembic/versions/1efee41ec55d_*.py` — migration adding `users` + FK constraints
- `backend/requirements.txt` — full dependency list (was missing entirely)
- `frontend/` — the entire React app

## 1. Backend setup

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env:
#   DATABASE_URL      — your Postgres connection string
#   JWT_SECRET         — any long random string
#   GOOGLE_CLIENT_ID   — from Google Cloud Console (see step 3)
#   GROQ_API_KEY       — from console.groq.com
```

Create the database, then run migrations from the **project root** (not `backend/`,
since `alembic.ini` lives there):

```bash
createdb agent_builder   # or create it however you normally do
cd ..
alembic upgrade head
```

Start the API:

```bash
uvicorn backend.main:app --reload --port 8000
```

Visit `http://localhost:8000/health` — you should see `{"status": "ok"}`.
Interactive API docs: `http://localhost:8000/docs`.

## 2. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
# edit .env:
#   VITE_API_URL           — http://localhost:8000
#   VITE_GOOGLE_CLIENT_ID  — same client ID as the backend (step 3)

npm run dev
```

Visit `http://localhost:5173`. Email/password sign-up works immediately with no extra
setup — Google is optional.

## 3. Google Sign-In setup (optional)

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth 2.0 Client ID** of type **Web application**.
3. Under **Authorized JavaScript origins**, add `http://localhost:5173`.
4. Copy the client ID into both `backend/.env` (`GOOGLE_CLIENT_ID`) and
   `frontend/.env` (`VITE_GOOGLE_CLIENT_ID`).
5. Restart both servers.

If you skip this, the Google button on the login/register screens will just show a
small note saying it isn't configured — email/password still works fine.

## 4. Using the app

1. Register or sign in.
2. On first login you'll be prompted to create an agent — give it a name, a system
   prompt, pick a Groq model, and optionally enable tools (math, GitHub analysis,
   charts, web search, Wikipedia, etc. — see `backend/tools/tools.py` for the full list
   and which ones need extra API keys).
3. Click **+ New chat**, type a message, and it streams back token-by-token. Tool calls
   show as a small "Using {tool}…" pill while they run.
4. Conversations are listed per-agent in the sidebar — rename or delete them, or switch
   agents from the dropdown at the top of the sidebar.

## 5. Deploying: Render (backend) + Vercel (frontend)

### Backend on Render

The repo includes `render.yaml` — a Blueprint that provisions the web service and a
free managed Postgres database together.

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, point it at the repo. It reads `render.yaml` and
   creates `agent-builder-backend` + `agent-builder-db` automatically.
3. `DATABASE_URL` and `JWT_SECRET` are filled in for you (from the DB and a generated
   secret). Set the rest manually in the service's **Environment** tab:
   - `GROQ_API_KEY`
   - `GOOGLE_CLIENT_ID` (optional — see step 3 in section 3 above)
   - `FRONTEND_ORIGIN` — your Vercel URL once you have it, e.g.
     `https://agent-builder.vercel.app` (comma-separate multiple origins if needed)
   - `FRONTEND_ORIGIN_REGEX` (optional) — to also allow Vercel *preview* deployments,
     e.g. `https://agent-builder-.*\.vercel\.app`
4. Deploy. The start command runs `alembic upgrade head` automatically before starting
   the server, so migrations apply on every deploy. Check `https://<your-service>.onrender.com/health`.

If you'd rather set it up by hand instead of using the Blueprint: create a Postgres
instance and a Python web service, set **Build Command** to
`pip install -r backend/requirements.txt`, **Start Command** to
`alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`, and add
the same env vars.

### Frontend on Vercel

`frontend/vercel.json` is already there for SPA routing (so React Router works on
refresh/direct links).

1. In Vercel: **New Project**, import the repo, set **Root Directory** to `frontend`.
   Framework preset should auto-detect as Vite.
2. Add environment variables (Project Settings → Environment Variables):
   - `VITE_API_URL` — your Render backend URL, e.g. `https://agent-builder-backend.onrender.com`
   - `VITE_GOOGLE_CLIENT_ID` — same client ID as the backend, if using Google sign-in
3. Deploy. Then go back to Render and set `FRONTEND_ORIGIN` to the Vercel URL Vercel
   just gave you, and redeploy the backend so CORS allows it.
4. If using Google sign-in, add the Vercel URL to **Authorized JavaScript origins** in
   the Google Cloud Console credential from section 3.

### After first deploy

- Render's free tier spins down on inactivity — the first request after idle will be
  slow (~30–60s cold start). Fine for testing, worth upgrading the plan for real use.
- Rotate `JWT_SECRET` if it was ever committed anywhere; Render's Blueprint generates
  one for you, so this only matters if you set it manually.

## Notes / things you may want to change before production

- CORS currently allows a single origin (`FRONTEND_ORIGIN`) — fine for local dev.
- JWTs are stored in `localStorage`. That's simple but vulnerable to XSS; for production
  consider httpOnly cookies instead.
- There's no rate limiting or email verification on `/auth/register`.
- `python_repl` and `requests_get` tools execute code / make arbitrary HTTP requests —
  they're in the tool registry but you may want to gate who can enable them.
