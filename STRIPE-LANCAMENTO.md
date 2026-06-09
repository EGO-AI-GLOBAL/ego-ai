# EGO Lançamento — R$ 10,94/mês (base R$ 9,99 + impostos/taxas embutidos)

**Link de pagamento (Brasil) — ativo:**

https://buy.stripe.com/aFa6oJc2q3mW81G7pg4ow0P

**Link antigo — desactivar no Stripe:**

https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K

## Regras

- Preço cobrado **R$ 10,94/mês** (6 meses) → **R$ 19,90/mês** (6 meses) → **R$ 29,90/mês** (EGO Conexão). Reajuste manual nas assinaturas ativas (ver `marketing/LEMBRETE-STRIPE-PRECOS-MANUAL.txt`).
- No produto Stripe: preço já inclui **6% impostos + ~3,5% taxa Stripe** sobre a base R$ 9,99. **Não** usar alíquota manual no catálogo.
- **Sem cupom** neste link (códigos promocionais desligados).
- Metadado Stripe: `plan_tier` = `connection` (mesmos limites EGO Conexão no app).
- Cupom indicação **EGOINDICA10** não se aplica a este produto.

## Railway (quando for lançar)

```env
STRIPE_CHECKOUT_LAUNCH_URL=https://buy.stripe.com/aFa6oJc2q3mW81G7pg4ow0P
EGO_LAUNCH_OFFER_PRICE_BRL=10.94
```

## Teste com utilizador (activar plano no Supabase)

O app acrescenta `client_reference_id` = id do utilizador. Teste manual:

```
https://buy.stripe.com/aFa6oJc2q3mW81G7pg4ow0P?client_reference_id=UUID-DO-USUARIO
```

Cartão teste Stripe: `4242 4242 4242 4242`

Depois: app → Conta / Planos → puxar para atualizar.

## Logo no produto Stripe

`marketing/brand/logo-site.png`

## Desactivar oferta (após 3–6 meses)

1. Stripe → Links de pagamento → desactivar este link.
2. Assinaturas activas → migrar preço para EGO Conexão R$ 29,90 na próxima renovação.
