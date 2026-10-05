# ICDE 2027 LaTeX template

ICDE 2027 research papers use the standard IEEE conference format rather than a conference-specific class. The official ICDE instructions point authors to the IEEE conference templates.

- ICDE 2027 instructions: <https://icde2027.github.io/cf-research-papers.html>
- IEEE authoring templates: <https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/>
- IEEEtran distribution: <https://ctan.org/pkg/ieeetran>
- Downloaded on: 2026-10-05
- Document class: `\documentclass[conference]{IEEEtran}`
- Research-paper limit: 12 pages excluding references and the AI-generated-content acknowledgment; no appendix

The unmodified distribution is stored in `IEEEtran.zip` and extracted under `IEEEtran/`. The conference starter file is `IEEEtran/bare_conf.tex`.

To compile on Anvil:

```bash
module load texlive/20200406
cd IEEEtran
pdflatex -interaction=nonstopmode -halt-on-error bare_conf.tex
```

The manuscript in the parent directory already uses IEEEtran conference mode and can be compiled with:

```bash
module load texlive/20200406
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```
