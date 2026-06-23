# Vídeos de marketing — Luna e Leo

Vídeos com **avatar animado falando** + **voz do app** (Edge TTS: Francisca = Luna, Antonio = Leo).

## Gerar tudo de uma vez

```powershell
pip install edge-tts
winget install ffmpeg
# ou: choco install ffmpeg

python scripts/generate_marketing_videos.py
```

**Saída:**

| Pasta | Arquivos |
|-------|----------|
| `luna/` | `01-criativo-a-solidao.mp4` … `04-stories-10s.mp4` |
| `leo/` | idem |
| `_loops/` | cópia dos loops `avatar-*-speaking.mp4` do app |
| `_audio/` | MP3 intermediários (pode apagar depois) |

Formato padrão: **9:16 (1080×1920)** para Reels/TikTok/Stories.  
Para manter proporção original: `python scripts/generate_marketing_videos.py --square`

## Roteiros (texto falado)

Os textos são os de `marketing/anuncios/SCRIPTS_15S_FALAS.md`.  
Para alterar, edite `CLIPS` em `scripts/generate_marketing_videos.py` e rode de novo.

## Uso em anúncios

1. **Criativo A (solidão):** `01-criativo-a-solidao.mp4`  
2. **Criativo B (produtividade):** `02-criativo-b-produtividade.mp4`  
3. **Orgânico:** `03-desabafo-domingo.mp4`  
4. **Stories:** `04-stories-10s.mp4`

Combine no CapCut com legendas queimadas e CTA “Baixe grátis” se quiser.

## Sem ffmpeg

O script só gera MP3 em `_audio/`. Instale ffmpeg e execute novamente para obter os MP4.
