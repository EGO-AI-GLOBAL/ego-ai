# EGO-AI — Crescimento diário

Cole os números do SQL todo dia (~12h50) e me manda print ou esta tabela.

**SQL rápido:** `supabase/CRESCIMENTO-DIARIO.sql` (Supabase → SQL Editor → RUN)

---

## Tabela de crescimento

| Data | perfis_total | ja_logaram | cadastros_hoje | login_hoje | cadastros_7d | chat_7d | Δ cadastros* | Notas |
|------|-------------:|-----------:|---------------:|-----------:|-------------:|--------:|-------------:|-------|
| 25/06/2026 | 28 | 9 | 8 | 3 | 5 | 5 | — | Baseline pós-Reels 1+2 |
| 26/06/2026 | | | | | | | | Reel 5 orgânico (agenda 23h) |
| 27/06/2026 | | | | | | | | **Reel 6** solidão 3h — orgânico |
| 28/06/2026 | | | | | | | | **Reel 7** carga mental — orgânico |
| 29/06/2026 | | | | | | | | SQL + DECISAO-REEL-6-7.txt |

\* **Δ cadastros** = `perfis_total` hoje − `perfis_total` ontem (crescimento líquido do dia)

---

## Como ler

| Coluna | Bom sinal |
|--------|-----------|
| `cadastros_hoje` | 1+ por dia com ads ativos |
| `ja_logaram` / `perfis_total` | > 60% já logaram |
| `usaram_chat_7d` | ≥ metade dos cadastros da semana |
| Δ cadastros | +2 ou mais/dia com R$25 em ads |

---

## Meta da semana (com Reel 3 + ads site)

| Métrica | Fraco | OK | Bom |
|---------|------:|---:|----:|
| perfis_total (fim semana) | < 35 | 35–45 | 46+ |
| cadastros_7d | ≤ 2 | 3–10 | 11+ |
| usaram_chat_7d | 0–1 | 2–5 | 6+ |

---

## Formato para me mandar (copiar)

```
CRESCIMENTO 25/06
perfis_total: 28
ja_logaram: 9
cadastros_hoje: 8
login_hoje: 3
cadastros_7d: 5
chat_7d: 5
```
