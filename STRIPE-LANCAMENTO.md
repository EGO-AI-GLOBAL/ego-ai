# EGO Lançamento — R$ 9,90/mês promocional (Stripe cobra 9,99)

**Link de pagamento (Brasil):**

https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K

## Regras

- Preço promocional **R$ 9,99/mês** (depois **R$ 29,90** Conexão — avisar no Termos).
- **Sem cupom** neste link (códigos promocionais desligados).
- Metadado Stripe: `plan_tier` = `connection` (mesmos limites EGO Conexão no app).
- Cupom indicação **EGOINDICA10** não se aplica a este produto.

## Railway (quando for lançar)

```env
STRIPE_CHECKOUT_LAUNCH_URL=https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K
```

## Teste com utilizador (activar plano no Supabase)

O app acrescenta `client_reference_id` = id do utilizador. Teste manual:

```
https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K?client_reference_id=UUID-DO-USUARIO
```

Cartão teste Stripe: `4242 4242 4242 4242`

Depois: app → Conta / Planos → puxar para atualizar.

## Logo no produto Stripe

`marketing/brand/logo-site.png`

## Desactivar oferta (após 3–6 meses)

1. Stripe → Links de pagamento → desactivar este link.
2. Assinaturas activas → migrar preço para EGO Conexão R$ 29,90 na próxima renovação.
