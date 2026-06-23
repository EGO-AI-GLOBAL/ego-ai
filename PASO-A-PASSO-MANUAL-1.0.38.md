# EGO-AI 1.0.38 — passo a passo (só o que é MANUAL)

Tudo o resto já está no código. Siga esta ordem.

---

## Fase 1 — Git e API (15 min)

### 1. Commit e push
No PC, na pasta do projeto:
```powershell
git add app ego_api flask_api.py scripts ego_api/config.py
git add app/src/components/DailyCare*.tsx app/src/components/WellnessJourneyCard.tsx
git add app/src/components/SocialFollowBar.tsx app/src/components/Trial*.tsx
git add marketing/RELEASE-1.0.38.txt marketing/VALIDAR-1.0.38.txt marketing/NOTAS-1.0.38-PLAY.txt
git add GERAR-1.0.38.bat ATUALIZAR-1.0.38.bat SUBMIT-IOS-1.0.38.bat PUBLICAR-1.0.38-PLAY.bat VALIDAR-1.0.38.bat
git commit -m "feat: 1.0.38 Desafio Diário, Jornada, trial banner e partilha social"
git push origin main
```

### 2. Railway — redeploy
1. Abra [Railway](https://railway.app) → projeto EGO-AI → **Deploy** (ou aguarde auto-deploy do push)
2. Confirme variáveis (Variables):
   ```
   EGO_LATEST_APP_VERSION=1.0.38
   EGO_LATEST_ANDROID_VERSION_CODE=72
   EGO_TRIAL_DAYS=20
   EGO_MAINTENANCE=0
   EGO_DAILY_CARE_COMMUNITY_TOP=21
   ```
3. Health OK:
   ```
   https://ego-ai-production-a2c2.up.railway.app/api/v1/health
   ```
   Deve mostrar `api_build` com `1.0.38-daily-care-journey-trial`

### 3. Supabase (se ainda não fez)
SQL Editor → executar uma vez:
- `supabase/migrations/20260604120000_profiles_phone_invites.sql`

---

## Fase 2 — Preparar build no PC (automático)

Duplo clique: **`ATUALIZAR-1.0.38.bat`**

Deve terminar sem erros (regression + smoke + npm).

---

## Fase 3 — Builds EAS (manual — demora ~30–60 min)

Duplo clique: **`GERAR-1.0.38.bat`**

- iOS build **23**
- Android versionCode **72**

Aguarde os dois builds terminarem no [expo.dev](https://expo.dev).

---

## Fase 4 — Lojas (manual)

### iPhone (TestFlight)
1. **`SUBMIT-IOS-1.0.38.bat`**
2. App Store Connect → TestFlight → build 23 → testadores

### Android (Play teste fechado)
1. Expo → download `.aab` do build 72
2. Play Console → teste fechado → nova versão
3. Notas: copiar de `marketing/NOTAS-1.0.38-PLAY.txt`
4. Guia: **`PUBLICAR-1.0.38-PLAY.bat`** (abre os ficheiros)

---

## Fase 5 — Testar antes do vídeo (30 min)

Duplo clique: **`VALIDAR-1.0.38.bat`**

Teste no **celular real** (Android + iPhone se possível):
1. Cadastro novo → vê Desafio Diário no chat
2. Toque no emoji → ranking sobe
3. «Postar e desafiar» → WhatsApp ou Stories
4. Banner «X dias grátis» aparece
5. Chat texto + voz ainda funcionam

**Só depois** de tudo OK → gravar vídeo de divulgação.

---

## O que NÃO precisa fazer agora

| Item | Quando |
|------|--------|
| 500 níveis / trilha Círculo | 1.0.39 |
| Site egoai.com.br | Quando DNS estiver pronto |
| Vídeo marketing | Depois da validação |

---

## Se algo falhar

| Problema | Solução |
|----------|---------|
| Desafio não aparece | API não deployada — repetir Fase 1 |
| «Acesso expirado» sem paywall bonito | Atualizar app para 1.0.38 |
| Build EAS falha | `VERIFICAR-ANTES-DO-BUILD.bat` |
| Regression guard falha | Não publicar — avisar no chat |

---

## Resumo em 5 linhas

1. `git push` → Railway redeploy  
2. `ATUALIZAR-1.0.38.bat`  
3. `GERAR-1.0.38.bat`  
4. Submit iOS + Play Android  
5. `VALIDAR-1.0.38.bat` → vídeo  
