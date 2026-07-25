# Deploying Modulus

Modulus ships as **one container**: a multi-stage [`Dockerfile`](Dockerfile) builds
the React frontend, then the FastAPI service serves that build **and** the JSON API
from the same origin. No CORS, no second service, one URL.

Because it's a plain Docker image, it runs unchanged on Render, Fly.io, Railway,
Google Cloud Run, or your own box.

## Which host? (free, no credit card)

| Host | Free? | Card? | Sleeps | Best for |
| ---- | ----- | ----- | ------ | -------- |
| **Render** (recommended) | ✅ | ❌ none | after ~15 min idle (~30–60 s cold start) | simplest — `render.yaml` is ready, ~3 clicks |
| **Hugging Face Spaces** | ✅ | ❌ none | after ~48 h idle | a link that stays warm between interviews |
| Fly.io | free allowance | ✅ required | configurable | snappier cold starts |
| Railway | trial credit | ✅ after trial | no | quick Docker deploys |

**Recommendation:** deploy on **Render** to get a free live URL fastest (Section 2).
If you want it to stay awake longer for a link you'll share on a CV, use
**Hugging Face Spaces** (Section 4). Both are free and need no card.

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

## 4. Hugging Face Spaces (free, no card, stays warm ~48 h)

Good when you want the link reliably awake for people clicking it off your CV.

1. Create a Space at <https://huggingface.co/new-space> → **SDK: Docker** → blank.
   HF makes a small git repo with a `README.md` that has a YAML header.
2. Edit that Space `README.md` header so HF routes to our server's port:
   ```yaml
   ---
   title: Modulus
   emoji: 🔩
   sdk: docker
   app_port: 8000
   ---
   ```
   (Our `Dockerfile` already listens on `8000` by default, so nothing else changes.)
3. Push this project into the Space repo (from your clone of it):
   ```bash
   git remote add space https://huggingface.co/spaces/<your-user>/modulus
   git push space master:main
   ```
   HF builds the Docker image and serves it at
   `https://<your-user>-modulus.hf.space`.

Then update the README demo link as in Section 3.

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
