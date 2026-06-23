#!/usr/bin/env python3
"""Gera PDF a partir de DOCUMENTACAO_COMPLETA.md (requer fpdf2)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "DOCUMENTACAO_COMPLETA.md"
PDF_PATH = ROOT / "DOCUMENTACAO_COMPLETA_EGO-AI.pdf"


def _sanitize(text: str) -> str:
    """Substitui caracteres problemáticos por ASCII seguro."""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2192": "->",
        "\u2514": "+",
        "\u251c": "+",
        "\u2502": "|",
        "\u2500": "-",
        "\u00e7": "c",
        "\u00e3": "a",
        "\u00f5": "o",
        "\u00e1": "a",
        "\u00e9": "e",
        "\u00ed": "i",
        "\u00f3": "o",
        "\u00fa": "u",
        "\u00c1": "A",
        "\u00c9": "E",
        "\u00cd": "I",
        "\u00d3": "O",
        "\u00da": "U",
        "\u00c3": "A",
        "\u00c7": "C",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("ascii", "replace").decode("ascii")


def main() -> int:
    try:
        from fpdf import FPDF
    except ImportError:
        print("Instale: pip install fpdf2")
        return 1

    if not MD_PATH.is_file():
        print(f"Ficheiro nao encontrado: {MD_PATH}")
        return 1

    text = MD_PATH.read_text(encoding="utf-8")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)

    def write_line(line: str, size: int = 9, bold: bool = False) -> None:
        line = _sanitize(line)
        if not line.strip():
            pdf.ln(3)
            return
        pdf.set_font("Helvetica", style="B" if bold else "", size=size)
        w = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.multi_cell(w, 5, line)
        pdf.ln(1)

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            continue
        if line.startswith("# "):
            write_line(line[2:].strip(), size=16, bold=True)
        elif line.startswith("## "):
            write_line(line[3:].strip(), size=13, bold=True)
        elif line.startswith("### "):
            write_line(line[4:].strip(), size=11, bold=True)
        elif line.startswith("|") and "---" in line:
            continue
        else:
            clean = re.sub(r"`([^`]+)`", r"\1", line)
            clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
            write_line(clean, size=9)

    pdf.output(str(PDF_PATH))
    print(f"PDF gerado: {PDF_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
