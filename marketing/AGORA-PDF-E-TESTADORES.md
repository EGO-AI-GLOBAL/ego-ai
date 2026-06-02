# Agora: PDF + liberar testadores (agenda depois)

Servidor Railway **já está pronto** (`api_build`: `2026-06-02-pdf-shared-cal-fix`, PDF ativo).

A agenda compartilhada com **convite por e-mail** fica para **depois** que os testadores instalarem e criarem conta.

---

## A — Você: novo build com PDF (obrigatório)

O PDF no telemóvel **só melhora** com um **novo `.aab`** na Play (build antigo não tem o envio estável).

1. Abra PowerShell na pasta do projeto.
2. Execute na ordem:

```powershell
cd "C:\Users\Iury\OneDrive\Área de Trabalho\EGO-AI-APP - Copia"
.\5-eas-login.bat
.\6-eas-build.bat
```

3. Espere o build em [expo.dev](https://expo.dev) (20–40 min).
4. Descarregue o ficheiro **`.aab`**.

**Versão deste build:** `1.0.2` (PDF por base64 + Leo/Luna + login corrigidos).

### Testar PDF antes de mandar aos 12

1. Instale **este** build no seu Android (teste interno).
2. Entre no app → Chat → ícone de documento → escolha um **PDF pequeno** (até 12 MB).
3. Deve aparecer aviso de documento carregado; pergunte: *«Resume em 5 tópicos»*.

Se falhar: confirme Wi‑Fi e que o health mostra `pdf_extract: true`.

---

## B — Play Console: liberar testadores

1. [play.google.com/console](https://play.google.com/console) → app **EGO-AI**.
2. **Testar e lançar** → **Teste interno** → **Criar nova versão**.
3. Carregue o **`.aab`** do passo A.
4. Notas da versão (exemplo):  
   `1.0.2 — PDF no chat, Leo/Luna, login e agenda (criar eventos).`
5. **Testadores** → lista **Testadores EGO 12** → importe  
   `marketing/testadores-ego-ai.csv`  
   (um e-mail por linha; inclua `sacolapersonalizada@uol.com.br` e os Gmail dos outros).
6. **Guardar** → copie o **link de adesão**.
7. Envie o texto em `marketing/TESTADORES-WHATSAPP.txt` (cole o link onde está `[COLE_AQUI_...]`).

Cada testador:

- Abre o link no Android (conta Google = e-mail da lista).
- **Tornar-se testador** → **Instalar** na Play Store.
- **Criar conta** no app (mesmo e-mail da lista).

---

## C — Depois (agenda compartilhada)

Quando alguém avisar *«já criei conta»*:

1. Agenda → agenda compartilhada → abrir a agenda.
2. Adicionar membro com **o mesmo e-mail** do cadastro dele.

Enquanto ninguém tiver conta, teste só **criar agenda** e **marcar reuniões** com a sua conta.

---

## Railway (já deve estar OK)

- `SUPABASE_SERVICE_ROLE_KEY` = true no health  
- `GOOGLE_API_KEY` = necessário para PDF com **fotos**; PDF só texto usa PyPDF2 no servidor  

Health: https://ego-ai-production-a2c2.up.railway.app/api/v1/health

---

## Ordem resumida

| # | O quê | Quem |
|---|--------|------|
| 1 | `eas build` production | Você |
| 2 | Subir `.aab` no teste interno | Você |
| 3 | Lista de e-mails + link WhatsApp | Você |
| 4 | Instalar + criar conta | Testadores |
| 5 | Convidar e-mails na agenda | Você (depois) |
