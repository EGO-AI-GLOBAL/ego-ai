# Programa de indicação (influenciadores)

## Como funciona

1. Você cadastra o influenciador com um **código** (ex.: `MARIA10`).
2. O influenciador divulga o link: `https://egoai.com.br/signup?ref=MARIA10` (ou o usuário digita o cupom no cadastro — campo sempre visível).
3. Quem se cadastra com o código:
   - **não vê** o plano **EGO Lançamento** (R$ 10,94);
   - vê o card **Plano parceiro · 10% na 1ª assinatura**;
   - ganha **10% de desconto na primeira compra** (cupom Stripe no checkout).
4. No **primeiro pagamento** desse usuário, o sistema:
   - registra **R$ 10,00** de comissão para o parceiro (`pending`);
   - lança **despesa automática** na planilha (`COMISSAO_INDICACAO` em `registro-diario.csv`).
5. No fim do mês, rode o relatório e repasse via PIX:

```bash
python custo/financeiro/relatorio_repasses_parceiros.py --month 2026-06
```

Abra `custo/financeiro/parceiros/repasses-2026-06-resumo.csv` — **total por parceiro** e chave PIX.

## Passo a passo (uma vez)

### 1. Supabase

Execute no SQL Editor:

`supabase/migrations/20260530120000_referral_partners.sql`

### 2. Stripe — cupom de 10% (só na 1ª fatura)

No [Stripe Dashboard](https://dashboard.stripe.com):

1. **Products → Coupons → Create**
   - Percent off: **10%**
   - Duration: **Once** (aplica só na primeira cobrança da assinatura)
2. **Promotion codes → Create**
   - Código público, ex.: `EGOINDICA10`
   - Vincule ao cupom acima
3. Em **cada Payment Link** de plano pago: ative **“Allow promotion codes”** (ou equivalente).

No Railway / `.env` da API e do webhook:

```env
STRIPE_REFERRAL_PROMO_CODE=EGOINDICA10
REFERRAL_ADMIN_SECRET=uma-senha-forte-só-sua
```

(O app só coloca o cupom no link se o usuário tiver código de indicação válido no cadastro.)

### 3. Cadastrar um influenciador

```bash
curl -X POST "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/referrals/partners" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: SUA_REFERRAL_ADMIN_SECRET" \
  -d "{\"code\":\"MARIA10\",\"display_name\":\"Maria Influencer\",\"contact_email\":\"maria@exemplo.com\",\"payout_pix\":\"maria@email.com\"}"
```

Resposta inclui `signup_link` para enviar ao parceiro.

### 4. Planilha mensal (repasse)

Navegador ou script:

```bash
curl -o indicacoes-2026-05.csv \
  "https://ego-ai-production-a2c2.up.railway.app/api/v1/admin/referrals/report.csv?month=2026-05" \
  -H "X-Admin-Key: SUA_REFERRAL_ADMIN_SECRET"
```

Ou localmente:

```bash
python scripts/referral_monthly_report.py --month 2026-05 --out indicacoes-2026-05.csv
```

A planilha traz cada indicação paga e um **resumo por parceiro** (total em R$ e quantidade).

## Deploy

1. Rodar migration no Supabase  
2. Configurar variáveis no Railway (API + webhook Stripe)  
3. Novo build do app (campo no cadastro + link `?ref=`)  
4. Criar cupom/promo no Stripe e habilitar códigos nos Payment Links  

## Observações

- Comissão fixa **R$ 10,00** por indicado, **apenas no primeiro pagamento**.
- O desconto de 10% depende do cupom Stripe “once”; renovações não têm desconto.
- Pagamento ao influenciador é **manual** (você usa o CSV); depois pode marcar `paid` no banco se quiser controle interno.
