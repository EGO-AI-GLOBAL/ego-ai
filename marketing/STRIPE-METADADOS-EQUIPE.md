# Metadados Stripe — planos Equipe (obrigatório)

Em **cada Payment Link** de equipe, adicione metadados (Checkout → link → Metadata):

| Chave | Exemplo (Conexão 30 BR) |
|-------|-------------------------|
| `plan_tier` | `connection` |
| `team_seats` | `30` |
| `plan_type` | `team` |

Valores de `plan_tier`: `connection` · `premium` · `total`  
Valores de `team_seats`: `10` · `20` · `30` · `40` · `50` · `100`

Sem isso o webhook só ativa o tier individual e **não** grava o limite de e-mails.

Links guardados no código: `ego_api/team_stripe_checkout.py`
