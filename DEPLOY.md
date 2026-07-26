# Deploying Modulus

Modulus ships as **one container**: a multi-stage [`Dockerfile`](Dockerfile) builds
the React frontend, then the FastAPI service serves that build **and** the JSON API
from the same origin. No CORS, no second service, one URL.

Because it's a plain Docker image, it runs unchanged on Render, Fly.io, Railway,
Google Cloud Run, or your own box.

## Which host? (free, no credit card)

Two shapes:
- **Single service** — one Docker container serves the API **and** the SPA on one URL.
- **Split** — a free HF **static** Space hosts the frontend; the API runs as Docker
  elsewhere. (Heads-up: HF's own **Docker/Gradio Spaces now require a PRO plan** —
  only **static** Spaces are free — so the Python API can't live on a free Space.)

| Option | Free? | Card? | Notes |
| ------ | ----- | ----- | ----- |
| **Render** — single service (Docker) | ✅ | ❌ | ~3 clicks (`render.yaml`); sleeps after ~15 min idle |
| **HF static frontend + Render API** | ✅ | ❌ | frontend always-up on HF; API still sleeps on Render free |
| DigitalOcean App Platform | via Student Pack $200 credit | ⚠️ maybe | always-on, no sleep |
| Fly.io / Railway | free allowance / trial | ✅ required | Docker, snappier cold starts |

Fastest to a working link: **Render single service** (Section 2). For an HF-hosted
front door: **HF static + Render API** (Section 4). Both are free, no card.

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
5. When it goes **Live**, your URL is `https://<your-service>.onrender.com` (or
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
🔗 **[Live demo](https://<your-service>.onrender.com)**
```

Commit and push — done.

---

## 4. HF static frontend + hosted API (free, HF-hosted front door)

Free HF Spaces only run **static** sites, so the Python API runs on Render
(Section 2) and a free HF **static** Space serves the React frontend pointed at it.
The API's CORS already allows any origin, so no per-origin config is needed.

**Step A — deploy the API on Render.** Follow Section 2; the same service doubles as
the API. Note its URL, e.g. `https://<your-service>.onrender.com`.

**Step B — build the frontend against that API.** The frontend bakes in `VITE_API_URL`
at build time:

```bash
cd frontend
VITE_API_URL="https://<your-service>.onrender.com" npm run build   # bakes in the API origin
cd ..
```

**Step C — publish `frontend/build/` as a static Space.**

1. Log in once: `hf auth login` (write token from <https://huggingface.co/settings/tokens>).
2. Create the Space: <https://huggingface.co/new-space> → name `modulus-web` →
   **SDK: Static** → **Blank** → Create.
3. Upload the build (the ready static-Space README is at
   [`deploy/huggingface/README.md`](deploy/huggingface/README.md)):
   ```bash
   cp deploy/huggingface/README.md frontend/build/README.md
   hf upload <your-user>/modulus-web frontend/build . --repo-type space \
     --commit-message "Publish Modulus frontend"
   ```

The Space serves at `https://<your-user>-modulus-web.static.hf.space` — an always-up
demo link (only the API sleeps). Update the README demo link (Section 3). To ship
frontend changes later, re-run Step B + the `hf upload` in Step C.

---

## Alternatives (require a credit card on file)

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
