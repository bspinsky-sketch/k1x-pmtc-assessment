# Module: Render Hosting

**Status:** STUB -- basic structure only; not fully documented
**Note:** Render free tier (512MB RAM) is INSUFFICIENT for LibreOffice. Use only with xlcalculator for formula evaluation, or upgrade to paid tier ($7/month eliminates spin-down and increases RAM).

---

## Known Constraints

- Free tier: 512MB RAM -- LibreOffice OOM-kills on every request (P028)
- Free tier: service spins down after 15 min inactivity; first request after idle takes ~30 sec
- Paid tier ($7/month): always-on, more RAM

## render.yaml Template (stub)

```yaml
services:
  - type: web
    name: [service-name]
    runtime: docker
    plan: free
    envVars:
      - key: FLASK_SECRET_KEY
        sync: false
      - key: FLASK_ENV
        value: production
```

## To Complete This Module

Document: account setup, environment variable configuration, auto-deploy from GitHub, custom domain setup, upgrade path.

