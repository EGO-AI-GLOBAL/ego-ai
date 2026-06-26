# EGO-AI — guia para agentes (não quebrar produção)

## Paridade Android + iOS (obrigatório — não pedir ao utilizador)

O app é **Expo/React Native**: quase todo o UI (`app/src/`, `app/app/`) corre **nos dois**.

| Tipo de mudança | Regra |
|-----------------|--------|
| **UI, textos, avatares, banner, chat, agenda** | Um diff → **Android e iOS** (mesmo código) |
| **Ícone** | `app.config.ts`: `icon` (iOS) **e** `android.adaptiveIcon` — alinhar visual |
| **Link de atualização** | `AppUpdateBanner`: Play **e** TestFlight (`Platform.OS` ou API `play_store_url` + `ios_update_url`) |
| **Build loja** | Mesma versão `app.config.ts` → **EAS Android + iOS** na mesma release (salvo bloqueio Apple) |
| **API / Supabase** | Uma vez — serve ambos |

**Checklist antes de dizer “só Android” ou “só iOS”:**
1. A alteração é só nativa (Gradle/Xcode)? → documentar exceção.
2. Caso contrário → tratar **sempre os dois** no mesmo commit/release.
3. Nunca corrigir ícone/banner/texto numa plataforma e deixar a outra para “depois”.

## Quatro agentes em paralelo — tudo fechado sempre

Quando **vários chats/agentes** trabalham ao mesmo tempo (actualmente **4**):

### Fechar tarefa (cada agente — só a sua zona)

1. Trabalhar **só na zona** (tabela abaixo) — não mexer nas outras
2. `regression_guard` + `smoke_test_api`
3. `git commit` + `git push origin main`
4. Criar/actualizar **`SYNC-AGENTES-[NOME]-1.0.XX.txt`** com **✅ PRONTO**
5. Confirmar **`git status` limpo** em `app/` e `ego_api/` (só da tua feature)
6. Avisar utilizador — **não correr GERAR/EAS**

**Proibido** (agentes Bolso, API, Marketing): `GERAR-*.bat`, `SUBIR-BUILD-*.bat`, `eas build`, `eas submit`.

### Build e lojas — **só agente Monstrinhos**

1. Esperar **todos** os `SYNC-AGENTES-*-1.0.XX.txt` com ✅ PRONTO
2. `PREPARAR-1.0.XX.bat` (regression + smoke + sync-check)
3. `GERAR-1.0.XX.bat` → `AGUARDAR-E-SUBMETER-1.0.XX.bat`

Regra Cursor: `.cursor/rules/sync-build-dois-agentes.mdc`

| Zona | Nome sync | Ficheiro |
|------|-----------|----------|
| **Monstrinhos** (único que faz build) | MONSTRINHOS | `moodMonsters/`, `daily_care.py`, GERAR/EAS |
| EGO de Bolso | BOLSO | `wellness_journey`, `companion/`, `EgoDeBolso*` |
| Segurança/API | API | Play Integrity, RLS, Railway |
| Marketing/Parceiros | MARKETING | `referrals`, signup, landing |

## Zonas ESTÁVEIS — não alterar sem pedido explícito + teste

| Área | Ficheiros principais | O que já funciona |
|------|----------------------|-------------------|
| **Auth / sessão** | `app/src/context/AuthContext.tsx`, `app/src/api/client.ts` (`login`, `refreshSessionToken`, interceptor 401), `ego_api/services.py` (`login`, `refresh_session`) | Ficar logado, refresh token |
| **Voz Android** | `app/src/hooks/useVoiceChat.ts`, `client.ts` (`sendChatVoiceFromUri`, `sendChatVoiceFileNative`) | Gravar → enviar → TTS |
| **Chat texto** | `client.ts` `sendChatMessage`, `ego_api/services.py` fluxo texto | Mensagens OpenAI/Gemini |
| **Vozes 12 avatares** | `ego_api/tts.py` `EDGE_TTS_VOICE_MAP` | Uma voz por persona |
| **Planos / limites** | `ego_api/db.py` `check_token_allowance`, `ego_api/plans.py` | Barra de uso, bloqueio |
| **Stripe** | `ego_api/stripe_webhook_handler.py`, `flask_api.py` webhook | Pagamentos |
| **Deploy** | Railway vars — **nunca** deixar `EGO_MAINTENANCE=1` em produção | App no ar |

## Zonas EXTENSÍVEIS — adicionar sem reescrever o estável

| Área | Onde acrescentar | Regra |
|------|------------------|-------|
| **Agenda manual** | `app/src/components/agenda/PersonalAgendaManual.tsx`, `SharedAgendaManual.tsx` | `agenda.tsx` só orquestra; não meter lógica no ecrã |
| **Comandos agenda no chat** | `ego_api/chat_schedule.py` — funções **novas** (`process_dismiss_*`) | Fast-path **antes** do LLM; não apagar fallbacks antigos |
| **Fuso horário** | `deviceTimezonePayload()` no client; `persist_client_timezone` na API | Enviar em **todo** POST chat/voz/bootstrap |

## Mapa de dependências (não cruzar sem necessidade)

```
App login ─────────────► Supabase auth (estável)
App chat texto ────────► services.process_chat_message (estável)
App voz ───────────────► upload nativo + Gemini áudio (estável)
App agenda manual ─────► REST reminders/agenda/shared (estável) — SEM passar pelo LLM
App agenda via avatar ► chat_schedule + LLM (extensível)
```

## Checklist obrigatório antes de deploy / build Play

```powershell
cd "raiz do projeto"
python scripts/regression_guard.py
python scripts/smoke_test_api.py
```

Windows: `VERIFICAR-ANTES-DEPLOY.bat`

## Se algo quebrou após update

1. Reverter **só** o ficheiro da feature nova (git), não “consertar tudo”.
2. Confirmar `/api/health` sem `maintenance: true`.
3. Testar **um** fluxo estável (login → chat texto → voz) antes de voltar a mexer na agenda.
