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

## Dois agentes em paralelo — uma subida só

Quando **dois chats/agentes** trabalham ao mesmo tempo:

1. **Esperar** — ambos fazem `commit + push` para `main`; `git pull` até não haver diff em `app/` nem `ego_api/`.
2. **Gerar juntos** — `GERAR-E-SUBMETER-JUNTO.bat` (enfileira iOS + Android; grava `builds-VERSAO.ids.json`).
3. **Submeter juntos** — `AGUARDAR-E-SUBMETER.bat` (espera FINISHED nos dois; TestFlight + Play **uma vez**).

**Proibido** em release normal: `SUBMIT-IOS-*.bat` ou `PUBLICAR-*-PLAY.bat` separados; `eas submit --latest` (pode subir build antigo do outro agente).

Detalhe: `SYNC-AGENTES-RELEASE.txt`

| Zona | Agente típico |
|------|----------------|
| Monstrinhos | `daily-care`, `moodMonsters/`, `ego_api/daily_care.py` |
| EGO de Bolso | `wellness-journey`, `EgoDeBolsoChatCard`, `SocialShare` |
| Estável | auth, voz, chat core, Stripe — **ninguém** sem pedido |

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
