# EGO-AI — pronto para testadores (objetivo: máxima conversão)

## Honesto sobre «95% vão assinar»

Nenhuma app no mundo garante **95%** de conversão em teste interno. Isso depende de preço, público, primeira impressão e se o app **funciona no primeiro minuto**.

O que **aumenta muito** a taxa de assinatura:

1. **Zero erro vermelho** no primeiro uso  
2. **Leo/Luna fixos** — confiança no produto  
3. **Agenda e lembrete funcionam** na hora  
4. **Oferta clara** (R$ 9,90 lançamento) visível em Planos  
5. **Stripe abre** ao tocar Assinar  

O código 1.0.5 mira isso. Conversão realista boa em teste: **10–30%** se tudo fluir; **95%** só com público muito quente + oferta única.

---

## Checklist «pronto» (tem de passar tudo)

### Técnico (obrigatório)

- [ ] `/api/v1/health` → ok  
- [ ] Supabase: 5 tabelas (`VERIFICAR-E-CORRIGIR.sql`)  
- [ ] Railway: `STRIPE_CHECKOUT_LAUNCH_URL` (oferta R$ 9,90)  
- [ ] Leo: escolhe → Chat, não volta  
- [ ] Sem vermelho em Chat/Agenda  
- [ ] Nome da reunião = texto do chat  
- [ ] Planos: cartões visíveis **mesmo** se houver aviso amarelo/vermelho pequeno  

### Experiência do testador (5 minutos)

1. Instalar / abrir app  
2. Criar conta ou entrar  
3. Escolher **Leo**  
4. Uma pergunta no chat (ver resposta)  
5. Marcar compromisso na agenda compartilhada  
6. Abrir **Planos** → ver **Lançamento R$ 9,90** → **Assinar** (Stripe abre)  

Se isto fluir, o testador **pode** assinar.

---

## Ordem de trabalho (grátis até Play)

1. Android Studio → `TESTAR-NO-PC-ANDROID.bat` ou USB  
2. Checklist acima ✓  
3. **Um** build Expo (julho ou Starter $19)  
4. Play teste interno  
5. Mensagem WhatsApp para testadores (roteiro dos 5 minutos acima)  

---

## Railway (oferta assinatura)

Variável obrigatória para conversão:

```
STRIPE_CHECKOUT_LAUNCH_URL=https://buy.stripe.com/7sYfZjfeC3mWfu810S4ow0K
```

Redeploy após guardar.

---

## O que NÃO fazer antes dos testadores

- Novos builds Expo «só para ver»  
- Mexer em Leo + API + planos ao mesmo tempo  
- Prometer 95% sem medir (contar quantos testaram vs quantos pagaram Stripe)
