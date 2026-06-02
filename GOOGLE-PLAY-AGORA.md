# Google Play — você já pagou os $25 (próximos cliques)

Conta liberada + celular cadastrado = pode usar **teste interno** para as 12 pessoas **baixarem pela Play Store** (link oficial).

**Package name do app:** `com.egoai.app` (tem de ser igual na Play Console e no build).

**API (já no ar):** `https://ego-ai-production-a2c2.up.railway.app`

**PDF no app:** API já no ar (`/api/v1/pdf/extract`). Gere **novo `.aab` v1.0.2** (EAS production) — ver `marketing/AGORA-PDF-E-TESTADORES.md`.

---

## PARTE 1 — Você clica na Play Console

### 1.1 Criar o app (se ainda não criou)

1. Abra [play.google.com/console](https://play.google.com/console)
2. **Criar app** / **Create app**
3. Nome: **EGO-AI**
4. Idioma: **Português (Brasil)**
5. Tipo: **App** → **Criar**

### 1.2 Identidade do app

1. Menu esquerdo: **Configuração do app** → **Detalhes do app**
2. **Nome do app:** EGO-AI
3. **ID do pacote:** deve ser **`com.egoai.app`** (ao criar o app, escolha/ confirme este ID — não dá para mudar depois)

### 1.3 Política de privacidade (obrigatório)

Precisa de um link **HTTPS** público.

- Se tiver site: `https://seusite.com/privacidade`
- Provisório: página no GitHub Pages / Google Sites com o texto de privacidade

Cole esse link em **Política de privacidade** na ficha do app.

### 1.4 Teste interno (12 pessoas)

1. Menu: **Testar e lançar** → **Teste interno**
2. Se pedir, complete o **questionário** (acesso ao app, anúncios = não, etc.)
3. **Criar nova versão** (vai pedir o ficheiro `.aab` — vem da Parte 2)
4. **Testadores** → **Criar lista de e-mails**
   - Nome: `Testadores EGO 12`
   - Adicione os **12 e-mails Gmail** dos testadores (**um e-mail por linha, sem cabeçalho**)
   - Modelo: `marketing/testadores-ego-ai.csv` e texto WhatsApp: `marketing/TESTADORES-WHATSAPP.txt`
5. **Guardar** → copie o **link de adesão** (opt-in)
6. Envie esse link no WhatsApp; cada um abre no Android → **Tornar-se testador** → **Instalar** na Play Store

---

## PARTE 2 — Gerar o `.aab` no PC (EAS / Expo)

Não precisa Android Studio para isto — o build corre na nuvem da Expo.

### 2.1 Terminal (pasta Copia)

```powershell
cd "C:\Users\Iury\OneDrive\Área de Trabalho\EGO-AI-APP - Copia\app"
npm install
npm install -g eas-cli
eas login
```

(Login com conta Expo — crie em [expo.dev](https://expo.dev) se não tiver.)

### 2.2 Ligar o projeto Expo

```powershell
eas init
```

Aceite criar/ligar projeto. Se pedir **Project ID**, confirme.

### 2.3 URL da API no build (produção)

```powershell
eas secret:create --scope project --name EXPO_PUBLIC_API_URL --value https://ego-ai-production-a2c2.up.railway.app --force
```

Opcional (política na loja):

```powershell
eas secret:create --scope project --name EXPO_PUBLIC_PRIVACY_POLICY_URL --value https://SEU-SITE/privacidade --force
```

### 2.4 Build para a Play Store

**Primeira vez (teste interno — gera `.aab`):**

```powershell
eas build --platform android --profile production
```

- Escolha **Let EAS create a keystore** (guarde a palavra-passe que mostrarem).
- Espere 15–30 min no site [expo.dev](https://expo.dev) → projeto → **Builds** → **Download** do `.aab`

**APK rápido só para você (opcional):**

```powershell
eas build --platform android --profile preview
```

---

## PARTE 3 — Subir o `.aab` no teste interno

1. Play Console → **Teste interno** → **Criar nova versão**
2. **Carregar** o `.aab` descarregado do EAS
3. **Nome da versão:** `1` (ou `1.0.0`)
4. **Notas da versão:** ex. "Primeira versão para testadores"
5. **Revisar versão** → **Iniciar lançamento para teste interno**

Espere processamento (minutos a algumas horas).

---

## PARTE 4 — Testadores instalam

1. Você envia o **link de teste interno** (Play Console → Testadores)
2. Cada pessoa:
   - Abre o link no **Android**
   - Aceita ser testador
   - Play Store → instala **EGO-AI**
3. Abrem o app → **Entrar** → testam voz e texto

**Seu celular** já cadastrado: pode instalar primeiro para validar.

---

## Checklist antes de enviar aos 12

- [ ] `eas build` production terminou sem erro
- [ ] `.aab` carregado no teste interno
- [ ] Link de testadores copiado
- [ ] Você instalou e fez login no seu Android
- [ ] Chat + microfone OK
- [ ] Railway com variáveis `GOOGLE_API_KEY`, Supabase

---

## iPhone

**Depois** que os 12 no Android estiverem OK → Apple Developer + TestFlight (outro guia).

---

## Se der erro comum

| Erro | O que fazer |
|------|-------------|
| Package name diferente | Play Console e `app.config.ts` têm de usar `com.egoai.app` |
| Falta política de privacidade | URL HTTPS na ficha do app |
| Build EAS falha | Copie o log e me envie |
| Testadores não veem o app | Esperar processamento; usar e-mail Gmail; link opt-in de novo |

---

## Me envie quando fizer

1. **Criou o app** na Play Console? (sim/não)  
2. **Package ID** que apareceu: `com.egoai.app` ou outro?  
3. Já correu `eas build`? (sim/não / erro)

Com isso ajusto o próximo passo (Vercel, CORS, screenshots, etc.).
