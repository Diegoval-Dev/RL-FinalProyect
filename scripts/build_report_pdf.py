"""Build the unified delivery PDF: front matter, chapters 1-9, figures and references."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = ROOT / "report" / "capitulos"
FIGURES_DIR = ROOT / "report" / "figuras"
REFERENCES = ROOT / "docs" / "08-informe" / "referencias.md"
OUTPUT = ROOT / "report" / "WAF-Arena_entrega_v1.0.pdf"

TITLE = "WAF Arena: defensor y atacante de inyección SQL con aprendizaje por refuerzo"
AUTHORS = "Diego Valenzuela, Daniel Dubón, Joaquín Puente, Nelson García"
COURSE = "Reinforcement Learning, Universidad del Valle de Guatemala"
VERSION = "Versión v1.0"

FIGURES_BY_CHAPTER = {
    "04": [
        (
            "EXP-D1_sarsa_vs_qlearning.png",
            "EXP-D1: SARSA frente a Q-learning. ER de validación en 0 (arriba) y "
            "tasa de rotura BRK durante el entrenamiento (abajo).",
        ),
    ],
    "05": [
        ("EXP-E2_weight_norm.png", "EXP-E2: norma de los pesos, Q-learning frente a SARSA lineal."),
        ("EXP-F_ablation.png", "EXP-F1 a F4: ablación de DQN."),
        (
            "EXP-F5_pareto.png",
            "EXP-F5: frontera detección y falsos positivos frente a ModSecurity.",
        ),
        ("EXP-G4_div_er.png", "EXP-G4: diversidad contra evasión por bono de entropía."),
    ],
    "06": [
        ("EXP-H1_er_vs_queries.png", "EXP-H1: evasión contra consultas reales."),
        ("EXP-I1_tpr.png", "EXP-I1: TPR por generación, ingenuo frente a pool."),
        ("EXP-I2_crossplay.png", "EXP-I2: matriz de cruces defensor por atacante."),
    ],
}

PREAMBLE = r"""
\usepackage{longtable,booktabs,array}
\usepackage{float}
\floatplacement{figure}{H}
\setlength{\emergencystretch}{3em}
\renewcommand{\arraystretch}{1.15}
\AtBeginEnvironment{longtable}{\footnotesize}
"""

DROP_RELATIVE_LINKS_FILTER = """
function Link(link)
  if link.target:match('^https?://') then return link end
  return link.content
end
"""


MATH_SYMBOLS = {
    "→": r"$\rightarrow$",
    "∈": r"$\in$",
    "≈": r"$\approx$",
    "≤": r"$\leq$",
    "≥": r"$\geq$",
}
INLINE_CODE = re.compile(r"(`[^`]*`)")


def replace_math_symbols(text: str) -> str:
    pieces = INLINE_CODE.split(text)
    for index in range(0, len(pieces), 2):
        for symbol, latex in MATH_SYMBOLS.items():
            pieces[index] = pieces[index].replace(symbol, latex)
    return "".join(pieces)


def chapter_number(path: Path) -> str:
    return path.name[:2]


def demote_nothing(text: str) -> str:
    return replace_math_symbols(text.strip()) + "\n"


def figures_block(chapter: str) -> str:
    figures = FIGURES_BY_CHAPTER.get(chapter, [])
    lines = ["\n\n## Figuras del capítulo\n"]
    for filename, caption in figures:
        lines.append(f"![{caption}]({FIGURES_DIR / filename}){{ width=85% }}\n")
    return "\n".join(lines) if figures else ""


def references_block() -> str:
    text = REFERENCES.read_text()
    text = re.sub(r"\]\(\.\./\.\./[^)]*\)", "]", text)
    return "# Referencias\n\n" + text.split("\n", 1)[1]


def front_matter() -> str:
    return f"""---
title: "{TITLE}"
author: "{AUTHORS}"
date: "{COURSE} · {VERSION}"
lang: es
toc: true
toc-depth: 2
numbersections: false
---

"""


def build_markdown() -> str:
    parts = [front_matter()]
    for chapter in sorted(CHAPTERS_DIR.glob("*.md")):
        parts.append(demote_nothing(chapter.read_text()))
        parts.append(figures_block(chapter_number(chapter)))
        parts.append("\n\\newpage\n")
    parts.append(references_block())
    return "\n".join(parts)


def run_pandoc(markdown: str, workdir: Path) -> None:
    source = workdir / "report.md"
    header = workdir / "header.tex"
    lua_filter = workdir / "relative_links.lua"
    source.write_text(markdown)
    header.write_text(PREAMBLE)
    lua_filter.write_text(DROP_RELATIVE_LINKS_FILTER)
    command = [
        "pandoc",
        str(source),
        "-o",
        str(OUTPUT),
        "--pdf-engine=xelatex",
        "--lua-filter",
        str(lua_filter),
        "-H",
        str(header),
        "-V",
        "geometry:margin=2.4cm",
        "-V",
        "fontsize=11pt",
        "-V",
        "mainfont=STIX Two Text",
        "-V",
        "monofont=Menlo",
        "-V",
        "colorlinks=true",
        "-V",
        "linkcolor=blue",
        "-V",
        "urlcolor=blue",
        "--resource-path",
        str(ROOT),
    ]
    subprocess.run(command, check=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        run_pandoc(build_markdown(), Path(tmp))
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
