# Deploying Modulus

Modulus ships as **one container**: a multi-stage [`Dockerfile`](Dockerfile) builds
the React frontend, then the FastAPI service serves that build **and** the JSON API
from the same origin. No CORS, no second service, one URL.

Because it's a plain Docker image, it runs unchanged on Render, Fly.io, Railway,
Google Cloud Run, or your own box. Steps below use **Render** (free, no card).

---

## 0. Test the image locally first (optional, ~2 min)

If you have Docker Desktop:

```bash
docker build -t modulus .
docker run --rm -p 8000:8000 modulus
```

Open <http://localhost:8000> — you should get the full app, and
<http://localhost:8000/api/materials> should return JSON. `Ctrl+C` to stop.

---

## 1. Push the repo to GitHub

The deploy pulls from GitHub, so commit and push first (the repo already has a
remote):

```bash
git add -A
git commit -m "Prepare Modulus for deployment"
git push
```

---

## 2. Deploy on Render (recommended)

1. Go to <https://dashboard.render.com> and sign in with GitHub.
2. **New +** → **Blueprint**.
3. Pick this repository. Render finds [`render.yaml`](render.yaml) and shows a
   service named **modulus** (Docker, free plan).
4. Click **Apply**. Render builds the image (first build ~5–8 min) and boots it.
5. When it goes **Live**, your URL is `https://modulus.onrender.com` (or
   `modulus-XXXX` if the name is taken — Render shows the real one at the top of
   the service page).

That URL is your live demo. Open it and click through Beam Optimizer → Validation
to confirm.

> **Not using the Blueprint?** You can instead do **New +** → **Web Service** →
> pick the repo → set **Runtime = Docker** → **Plan = Free** → **Create**. The
> `render.yaml` just automates those same choices.

### Free-plan caveat (worth a README footnote)

The free instance sleeps after ~15 min of no traffic; the next visitor triggers a
~30–60 s cold start, then it's fast. Fine for a portfolio link. To avoid sleep,
upgrade to Render's paid Starter plan, or use Fly.io below.

---

## 3. After it's live

Update the demo link in [`README.md`](README.md):

```md
🔗 **[Live demo](https://modulus.onrender.com)**
```

Commit and push — done.

---

## Alternatives

**Fly.io** (no idle sleep on the free allowance; needs a card on file):

```bash
# one-time
curl -L https://fly.io/install.sh | sh
fly auth login

# from the repo root — Fly detects the Dockerfile
fly launch --now
```

Accept the detected Dockerfile; Fly builds and deploys, then prints the URL. Fly
sets `PORT` automatically, which the Dockerfile's `CMD` already respects.

**Railway**: New Project → Deploy from GitHub repo → it auto-detects the
Dockerfile. Railway injects `PORT`, which the image honors. Free trial credit
applies.

---

## How the single-service wiring works

- `frontend/src/api.ts` calls the API at the relative path `/api`, so the same
  origin serves both — nothing to configure per environment.
- In dev, `vite.config.ts` proxies `/api` → `localhost:8000` (run the API with
  `python api.py` and the SPA with `npm run dev`).
- In the container, `api.py` mounts `../frontend/build` at `/` (FastAPI
  `StaticFiles(..., html=True)`), so `/` serves the SPA, `/assets/*` the hashed
  bundles, and `/api/*` the JSON endpoints. The mount is registered **after** the
  API routes, so the API always wins.
