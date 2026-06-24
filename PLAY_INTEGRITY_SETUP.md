# Play Integrity API — configuração EGO-AI

Protege chat e voz contra **APK clonado** a abusar da sua API OpenAI/Gemini.

## 1. Google Play Console

1. [Play Console](https://play.google.com/console) → **Integridade do app** → ativar **Play Integrity API**.
2. Anote o **número do projeto Google Cloud** (Cloud Project Number).

## 2. Google Cloud

1. [Google Cloud Console](https://console.cloud.google.com/) → mesmo projeto ligado à Play Console.
2. **APIs e serviços** → ativar **Play Integrity API**.
3. **IAM** → criar **conta de serviço** com papel **Play Integrity API Admin** (ou acesso à API).
4. **Chaves** → JSON da conta de serviço → guardar em local seguro (nunca no Git).

## 3. Backend (Railway / `.env` raiz)

```env
# Desligado em dev local (default)
EGO_PLAY_INTEGRITY=0

# Produção: monitor (só regista) ou enforce (bloqueia)
EGO_PLAY_INTEGRITY=1
EGO_PLAY_INTEGRITY_MODE=monitor
# EGO_PLAY_INTEGRITY_MODE=enforce

GOOGLE_CLOUD_PROJECT_NUMBER=123456789012
ANDROID_PACKAGE_NAME=com.egoai.app

# Colar JSON da conta de serviço numa linha (Railway Variables)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

Opcional:

```env
# Só app reconhecido na Play (bloqueia APK interno de teste)
EGO_PLAY_INTEGRITY_STRICT_APP=1

# Exigir MEETS_DEVICE_INTEGRITY (bloqueia alguns emuladores)
EGO_PLAY_INTEGRITY_REQUIRE_DEVICE=1
```

Reinstalar deps da API:

```powershell
pip install -r requirements-api.txt
```

## 4. App Android (`app/.env`)

```env
EXPO_PUBLIC_GOOGLE_CLOUD_PROJECT_NUMBER=123456789012
```

**Requer dev build ou APK** — não funciona no Expo Go.

```powershell
cd app
npm run build:android:preview
```

## 5. Testar

1. `EGO_PLAY_INTEGRITY=1` + `EGO_PLAY_INTEGRITY_MODE=monitor` na API.
2. Instalar APK no telemóvel.
3. Login → enviar mensagem de chat.
4. Logs Railway: `[EGO] play_integrity ok` ou motivo da falha.
5. Quando estiver estável: `EGO_PLAY_INTEGRITY_MODE=enforce`.

## Rotas protegidas (quando activo)

- `POST /api/v1/chat/messages`
- `POST /api/v1/chat/voice`
- `POST /api/v1/voice/realtime/*` (exceto status)

Header enviado pelo app: **`X-Play-Integrity`**.

Ver também: [SECURITY_PRELAUNCH_CHECKLIST.md](./SECURITY_PRELAUNCH_CHECKLIST.md) secção 8.
