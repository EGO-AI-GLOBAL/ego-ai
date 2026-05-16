# EGO-AI — App Android e iPhone

App nativo (Capacitor) que abre o teu **EGO-AI no Streamlit** em ecrã completo, como uma app instalada.

## Pré-requisitos

1. **EGO-AI publicado em HTTPS** (ex.: [Streamlit Cloud](https://streamlit.io/cloud))
2. **Node.js 18+** — [nodejs.org](https://nodejs.org/)
3. **Android:** [Android Studio](https://developer.android.com/studio)
4. **iPhone:** Mac com [Xcode](https://developer.apple.com/xcode/) (build iOS só no macOS)

## Configuração (uma vez)

```bash
cd mobile
npm install
```

Define a URL do teu app:

```bash
npm run configure -- https://SEU-APP.streamlit.app
```

Ou copia `.env.example` para `.env` e edita `EGO_APP_URL`.

## Gerar projetos nativos (uma vez)

```bash
npm run init:android
npm run init:ios
```

No Windows só o Android funciona localmente; iOS precisa de Mac.

## Abrir no emulador ou telemóvel

```bash
npm run android
# ou (Mac)
npm run ios
```

No Android Studio: Run ▶ num emulador ou telemóvel com depuração USB.

No Xcode: escolhe simulador ou iPhone e Run.

## APK de teste (Android)

Depois de `npm run cap:sync`:

```bash
cd android
gradlew.bat assembleDebug
```

O APK fica em `android/app/build/outputs/apk/debug/app-debug.apk`.

## Publicar nas lojas

| Loja | Conta | Notas |
|------|--------|--------|
| Google Play | Play Console (~$25 único) | Gera AAB assinado no Android Studio |
| App Store | Apple Developer ($99/ano) | Archive no Xcode → App Store Connect |

O app é um **WebView** do teu Streamlit: atualizações de lógica não exigem nova versão na loja, desde que a URL `EGO_APP_URL` aponte para o servidor atualizado.

## Estrutura

- `capacitor.config.js` — URL do Streamlit e permissões de navegação
- `www/` — ecrã de arranque (offline)
- `android/` / `ios/` — projetos nativos (gerados, não versionados no git)

## Problemas comuns

- **Ecrã branco:** confirma `EGO_APP_URL` com `https://` e que o site abre no browser do telemóvel.
- **Login Supabase:** o domínio `*.supabase.co` já está em `allowNavigation`.
- **Microfone (voz):** o browser dentro do app pede permissão; aceita no telemóvel.
