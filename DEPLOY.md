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

## 4. Hugging Face Spaces (recommended free host — no card, ~48 h warm)

Best for a CV link: free CPU Basic Spaces get **16 GB RAM / 2 vCPU** and only sleep
after ~48 h idle (adjustable in the Space settings). Modulus is CPU-only, so the
free tier runs it fully — no Pro needed.

A ready Space README with the required Docker/port front-matter is checked in at
[`deploy/huggingface/README.md`](deploy/huggingface/README.md). It stays out of the
GitHub landing page and only configures the Space.

1. **Log in once:** `pip install -U "huggingface_hub[cli]"` then `hf auth login`
   (paste a **write** token from <https://huggingface.co/settings/tokens>). This
   also sets the git credential used to push.
2. **Create the Space:** <https://huggingface.co/new-space> → name `modulus` →
   **SDK: Docker** → **Blank** → Create.
3. **Populate it** from your clone of this repo (run in Git Bash, from the repo root):
   ```bash
   git clone https://huggingface.co/spaces/<your-user>/modulus ../modulus-space
   cp deploy/huggingface/README.md ../modulus-space/README.md
   cp Dockerfile .dockerignore ../modulus-space/
   cp -r backend frontend ../modulus-space/
   cd ../modulus-space && git add -A && git commit -m "Deploy Modulus" && git push
   ```
4. HF builds the image (first build ~5–8 min) and serves it at
   `https://<your-user>-modulus.hf.space`. Update the demo link (Section 3).

To ship later changes, re-run the `cp` commands and `git push` from the Space clone.

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
