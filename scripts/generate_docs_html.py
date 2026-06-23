#!/usr/bin/env python3
"""Gera HTML imprimível a partir de DOCUMENTACAO_COMPLETA.md (UTF-8, acentos corretos)."""
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "DOCUMENTACAO_COMPLETA.md"
OUT = ROOT / "DOCUMENTACAO_COMPLETA_EGO-AI.html"


def md_to_html(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_code = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            if in_code:
                out.append("<pre><code>")
            else:
                out.append("</code></pre>")
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("|") and line.endswith("|"):
            cells = [html.escape(c.strip()) for c in line.strip("|").split("|")]
            tag = "th" if "---" in line or (out and "<table>" in out[-3:]) else "td"
            if "---" in line:
                continue
            if not out or "<table>" not in "".join(out[-5:]):
                out.append("<table border='1' cellpadding='6' cellspacing='0'>")
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
        elif not line.strip():
            if out and out[-1] != "</table>":
                if "<table" in out[-1] or (len(out) > 1 and "<tr>" in out[-2]):
                    out.append("</table>")
            out.append("<br/>")
        elif line.startswith("- "):
            out.append(f"<li>{html.escape(line[2:])}</li>")
        else:
            esc = html.escape(line)
            esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
            esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
            out.append(f"<p>{esc}</p>")
    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<title>EGO-AI — Documentação Completa</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; line-height: 1.55; color: #1a1a1a; }}
  h1 {{ color: #7B2CBF; border-bottom: 2px solid #EEF0F3; padding-bottom: 0.5rem; }}
  h2 {{ color: #5a189a; margin-top: 2rem; }}
  h3 {{ color: #333; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.92rem; }}
  th {{ background: #EDE9FE; text-align: left; }}
  td, th {{ border: 1px solid #ddd; padding: 8px; }}
  code, pre {{ background: #f4f4f5; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  pre {{ padding: 12px; overflow-x: auto; }}
  @media print {{ body {{ margin: 1cm; }} h1,h2 {{ page-break-after: avoid; }} }}
</style>
</head>
<body>
{body}
<p><em>EGO-AI — Documentação gerada automaticamente. Para PDF: Arquivo → Imprimir → Guardar como PDF.</em></p>
</body>
</html>"""


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    OUT.write_text(md_to_html(text), encoding="utf-8")
    print(f"HTML gerado: {OUT}")


if __name__ == "__main__":
    main()
