# Publicar EGO-AI

## Opção recomendada: Streamlit Cloud (mais estável)

1. https://share.streamlit.io → **Create app** → repo `EGO-AI-GLOBAL/ego-ai`
2. **Main file:** `app.py`
3. **Secrets** (copiar do `.streamlit/secrets.toml`):

```toml
GOOGLE_API_KEY = "..."
SUPABASE_URL = "https://SEU-REF.supabase.co"
SUPABASE_KEY = "sb_publishable_..."
```

4. **Save** → **Reboot**
5. Abrir o URL `https://....streamlit.app`

Não use `packages.txt` no Cloud.

---

## Railway (opcional, mais difícil)

- Serviço precisa de **512MB+ RAM**; Streamlit + Gemini pode falhar no plano grátis.
- Se falhar: **Deployments → View logs** e enviar as últimas linhas.
- Variables: `SUPABASE_URL`, `SUPABASE_KEY`, `GOOGLE_API_KEY`.

Para parar deploys automáticos: Railway → **Settings** → desligar **Deploy on push** até o Cloud estar OK.
