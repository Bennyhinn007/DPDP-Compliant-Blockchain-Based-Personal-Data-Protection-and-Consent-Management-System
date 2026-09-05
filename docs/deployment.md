# Deployment Guide

How to deploy the DPDP Healthcare Platform to a **free public URL**.

## Architecture of the deployment

```
Vercel (React frontend)  ──HTTPS──►  Render (Flask backend)  ──►  MongoDB Atlas
                                              │
                                              └──►  Ethereum Sepolia (optional, real anchoring)
```

> **About RFID:** the ESP32 RFID terminal talks to the backend over your *local*
> Wi-Fi, so the tap feature only works when the backend runs on your laptop
> (local demo). In the cloud it degrades gracefully — sensitive actions simply
> show "physical verification required." Run the **cloud** version for your
> shareable link, and the **local** version for the live viva. Both use the
> same codebase.

Everything below uses **free tiers**. Total cost: ₹0.

---

## Step 0 — Prerequisites

- Your code is pushed to GitHub (it is).
- Accounts (all free, sign in with GitHub):
  - [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
  - [Render](https://dashboard.render.com/)
  - [Vercel](https://vercel.com/signup)
- Your **ENCRYPTION_KEY** value. Use the same key everywhere or previously-seeded
  data won't decrypt. Generate one if needed:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

---

## Step 1 — Database: MongoDB Atlas

1. Create a **free M0 cluster** (any region; pick one near you).
2. **Database Access** → Add New Database User → username + password (save these).
3. **Network Access** → Add IP Address → **Allow access from anywhere** (`0.0.0.0/0`).
   *(Fine for a demo; tighten later for real production.)*
4. **Connect** → **Drivers** → copy the connection string. It looks like:
   ```
   mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Replace `<user>` and `<password>`. This is your **`MONGO_URI`**.

---

## Step 2 — Backend: Render

**Option A — Blueprint (uses the included `render.yaml`, easiest):**

1. Render dashboard → **New +** → **Blueprint** → connect this GitHub repo.
2. Render reads `render.yaml` and creates the `dpdp-backend` web service.
3. Fill in the secret env vars it prompts for (see the table below).

**Option B — Manual web service:**

1. **New +** → **Web Service** → select the repo.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Health Check Path:** `/health`

**Environment variables** (Render dashboard → Environment):

| Key | Value |
|-----|-------|
| `FLASK_ENV` | `production` |
| `PYTHON_VERSION` | `3.13.4` |
| `MONGO_URI` | your Atlas connection string from Step 1 |
| `MONGO_DB_NAME` | `dpdp_healthcare` |
| `SECRET_KEY` | a long random string |
| `JWT_SECRET_KEY` | a different long random string |
| `ENCRYPTION_KEY` | your Fernet key (Step 0) |
| `CORS_ORIGINS` | your Vercel URL (fill in after Step 3) |
| `GOOGLE_CLIENT_ID` | your Google OAuth client ID |

> The app **refuses to boot in production** if `ENCRYPTION_KEY` is missing or the
> secret keys are still the dev defaults — that's the guardrail working, not a bug.

3. Deploy. When it's live, note the URL: `https://dpdp-backend.onrender.com`.

**Seed the database once** (Render → your service → **Shell**):
```bash
python -m app.db_init
python seeds/seed_demo.py
```

Verify: open `https://dpdp-backend.onrender.com/health` → `{"status":"healthy"}`.

> **Free-tier note:** Render sleeps the service after ~15 min idle; the first
> request then takes ~30–50s to wake. For a live demo, hit the URL once a minute
> before you present, or open `/health` to warm it up.

---

## Step 3 — Frontend: Vercel

1. Vercel → **Add New** → **Project** → import the repo.
2. Settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (auto-detected; `vercel.json` is included)
3. **Environment Variables:**

   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://dpdp-backend.onrender.com/api/v1` |
   | `VITE_GOOGLE_CLIENT_ID` | your Google OAuth client ID |

4. **Deploy.** You get a URL like `https://dpdp-health.vercel.app`.

---

## Step 4 — Wire everything together

1. **CORS:** in Render, set `CORS_ORIGINS` to your Vercel URL
   (e.g. `https://dpdp-health.vercel.app`). Redeploy the backend.
2. **Google OAuth origins:** Google Cloud Console → APIs & Services →
   Credentials → your OAuth client → **Authorized JavaScript origins** →
   add your Vercel URL. (Without this, the Google button fails.)
3. Open your Vercel URL and log in with a demo account.

---

## Step 5 (optional but impressive) — Real Sepolia anchoring

Make on-chain anchors real and publicly verifiable on Etherscan.

1. Get a free Sepolia RPC URL from [Infura](https://infura.io) or
   [Alchemy](https://alchemy.com).
2. Create a throwaway wallet, fund it from a
   [Sepolia faucet](https://sepoliafaucet.com) (free test ETH).
3. In Render, set:
   | Key | Value |
   |-----|-------|
   | `BLOCKCHAIN_NETWORK` | `sepolia` |
   | `SEPOLIA_RPC_URL` | your Infura/Alchemy Sepolia URL |
   | `SEPOLIA_PRIVATE_KEY` | the throwaway wallet's private key (0x…) |
4. Redeploy. New record anchors now produce real transactions, and the
   Record Lifecycle Story shows a **"View on block explorer"** link.

> The private key controls only worthless testnet ETH, but still keep it in
> Render's env vars — never in the repo.

---

## Quick troubleshooting

| Symptom | Fix |
|---------|-----|
| Frontend loads but every API call fails (CORS error in console) | Set `CORS_ORIGINS` on Render to the exact Vercel URL, redeploy |
| Backend won't start, logs mention "Refusing to start in production" | Set the missing secret it names (usually `ENCRYPTION_KEY`) |
| Login works but data shows `[DECRYPTION_FAILED]` | `ENCRYPTION_KEY` differs from the one used when seeding — reseed or reuse the key |
| Google button does nothing | Add the Vercel URL to Google Authorized JavaScript origins |
| First request very slow | Render free tier cold start; warm it via `/health` before demoing |
| Deep link (e.g. `/dashboard`) 404s on refresh | Ensure `frontend/vercel.json` rewrites are deployed |

---

## Local demo (for the viva, with RFID)

Keep running the local stack for the full RFID experience:

```bash
# backend
cd backend && python run.py         # :5000

# frontend
cd frontend && npm run dev          # :5173
```

Point the ESP32 firmware's backend URL at your laptop's LAN IP (e.g.
`http://192.168.x.x:5000`), and tap a card — the physical-presence gate
unlocks the erasure / DPO actions live.
