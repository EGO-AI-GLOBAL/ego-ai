# EGO de Bolso — cenários virais (Dia 7)

## Correr simulador

```powershell
cd "raiz do projeto"
python scripts/simulate_bolso_viral.py
python scripts/simulate_bolso_viral.py --users 200 --weeks 8
```

## O que mede

| Variável | Significado |
|----------|-------------|
| `share_rate` | % de utilizadores activos que tocam «Postar» / partilham por semana |
| `invite_click` | % de contactos que abrem o link Play/TestFlight |
| `install_rate` | % de cliques que viram instalação |
| `retention_d7` | % de novos que ficam activos 7 dias |

## Cenários

| Cenário | Quando usar |
|---------|-------------|
| **Pessimista** | Só orgânico, sem Reels, poucos testadores |
| **Base** | Meta interna com cartão novo + WA/IG + 50 testadores |
| **Otimista** | Reels + repost + incentivo «responde com teu nível» |

## Acções que movem a agulha (já no app 1.0.53+)

1. Cartão gradiente com nome do pet + desafio de nível
2. WhatsApp com links Android + iPhone na legenda
3. Desafio semanal 4/7 dias (1.0.55+) — motivo para voltar
4. Push 10h/18h com nome do avatar

## Meta sugerida (cenário BASE, 120 users, 6 semanas)

- **+80–120** instalações novas via partilha
- **K > 0,3** = crescimento lento mas positivo
- **K > 1,0** = viral (só com otimista + marketing forte)
