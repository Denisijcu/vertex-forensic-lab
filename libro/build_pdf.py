"""
build_pdf.py — Genera el interior KDP (6x9 in) de "Vertex Forensic Lab" con pandoc + XeLaTeX.
Mismo diseño que "Vertex-Core" y "Vertex-Core SQL" (Source Serif 4 / Source Sans 3).

Uso, desde E:\\vertex-forensic-lab\\libro:
  python build_pdf.py [carpeta_manuscrito] [carpeta_fuentes]
Por defecto: ./manuscrito y ./fonts. Salida: ./build/vertex-forensic-lab.pdf
Requiere: pandoc, xelatex y el paquete de Python pyphen.
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAN = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "manuscrito"
FONTS = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "fonts"
OUT = HERE / "build"
OUT.mkdir(exist_ok=True)
JOB = "vertex-forensic-lab"

FRONT = ["front-01-dedicatoria.md", "front-02-prefacio.md", "front-03-para-quien-es.md",
         "front-04-como-leer.md"]
BODY = ["cap-01-el-enemigo-cambio.md", "cap-02-cinco-capas-y-una-sola-verdad.md",
        "cap-03-medir-la-fisica-del-trafico.md", "cap-04-una-trampa-con-firma.md",
        "cap-05-que-cada-pregunta-le-cueste.md", "cap-06-el-modelo-asiste-no-da-fe.md",
        "cap-07-contener-sin-dispararse-en-el-pie.md", "cap-08-que-no-te-usen-el-escudo.md",
        "cap-09-campo-de-tiro.md", "cap-10-un-acta-que-se-pueda-defender.md",
        "cap-11-un-agente-que-consulta-la-boveda.md", "cap-12-lo-que-todavia-falla.md"]
BACK = ["back-01-conclusion.md", "apendice-A-comandos.md", "apendice-B-glosario.md",
        "apendice-C-referencia-tecnica.md", "back-02-sobre-el-autor.md"]

FIXES = []  # erratas detectadas al compilar: (buscar, reemplazar)

# La serif (subconjunto latino) no tiene estos glifos. En la prosa se convierten en símbolos
# matemáticos de LaTeX; dentro del código no se tocan (DejaVu Sans Mono sí los tiene).
SYMBOLS = [("Δ", r"$\Delta$"), ("→", r"$\rightarrow$"), ("≥", r"$\geq$"), ("≤", r"$\leq$"),
           ("−", r"$-$"), ("≈", r"$\approx$")]


def tex_escape(s):
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}")]:
        s = s.replace(a, b)
    return s


import pyphen  # noqa: E402

_HY = pyphen.Pyphen(lang="es", left=3, right=3)
_WORD = re.compile(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]{7,}")
_CODESPAN = re.compile(r"(`[^`]*`)")


def hyphenate(line):
    """Inserta guiones blandos (U+00AD) en palabras largas de la prosa, sin tocar código ni URLs."""
    parts = re.split(r"(`[^`]*`|https?://\S+|\S+\.(?:com|org|io|md|py|json|yaml|txt|duckdb|ps1|sh)\S*|\]\([^)]*\))", line)
    for i in range(0, len(parts), 2):
        parts[i] = _WORD.sub(lambda m: _HY.inserted(m.group(0), hyphen="\u00ad"), parts[i])
    return "".join(parts)


def symbols(line):
    """Sustituye en la prosa los glifos que no tiene la serif, respetando el código en línea."""
    parts = _CODESPAN.split(line)
    for i in range(0, len(parts), 2):
        for a, b in SYMBOLS:
            parts[i] = parts[i].replace(a, b)
    return "".join(parts)


def preprocess(fn, txt):
    for a, b in FIXES:
        txt = txt.replace(a, b)
    if fn == "front-01-dedicatoria.md":
        cuerpo = [p.strip().replace("\n", " ") for p in txt.split("# Dedicatoria", 1)[1].strip().split("\n\n")]
        return ("```{=latex}\n\\clearpage\\thispagestyle{empty}"
                "\\vspace*{1.8in}\\begin{center}\\itshape\n```\n\n" +
                "\n\n```{=latex}\n\\par\\vspace{12pt}\n```\n\n".join(cuerpo) +
                "\n\n```{=latex}\n\\end{center}\n```\n")
    if fn == "front-02-prefacio.md":
        txt = txt.replace("— Denis Sánchez Leyva\nMiami, noviembre de 2026",
                          "```{=latex}\n\\par\\vspace{8pt}\\begin{flushright}\\itshape — Denis Sánchez Leyva\\\\ Miami, noviembre de 2026\\end{flushright}\n```")
    lines = txt.splitlines()
    # quitar la nota "> Borrador. Fuente: ..." que va justo después del título de cada capítulo
    if fn.startswith("cap-"):
        i = next(k for k, l in enumerate(lines) if l.startswith("# "))
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and lines[j].lstrip().startswith(">"):
            while j < len(lines) and lines[j].lstrip().startswith(">"):
                j += 1
            lines = lines[:i + 1] + lines[j:]
    out, fence = [], None  # fence = marcador del bloque de código abierto (``` o ````)
    for l in lines:
        m = re.match(r"^(`{3,})", l)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence and l.strip() == fence:
                fence = None
        in_code = fence is not None
        if not in_code and l.startswith("# "):
            title = l[2:].strip()
            label, name = title.split(" — ", 1) if " — " in title else ("", title)
            out += ["", "```{=latex}", r"\vcchapter{%s}{%s}" % (tex_escape(label), tex_escape(name)), "```", ""]
            continue
        if not in_code and l.strip() == "---":
            out += ["", "```{=latex}", r"\vcbreak", "```", ""]
            continue
        if not in_code and not m and not l.startswith("    "):
            if not l.startswith(("#", "|")):
                l = hyphenate(l)
            l = symbols(l)  # después de partir: si no, el guion blando cae dentro de \rightarrow
        out.append(l)
    return "\n".join(out)


def to_latex(files):
    md = "\n\n".join(preprocess(f, (MAN / f).read_text(encoding="utf-8")) for f in files)
    r = subprocess.run(["pandoc", "-f", "markdown-auto_identifiers+smart+lists_without_preceding_blankline",
                        "-t", "latex", "--highlight-style=tango", "--wrap=preserve", "--columns=40"],
                       input=md, capture_output=True, text=True, check=True, encoding="utf-8")
    tex = r.stdout.replace("\u00ad", "\\-")
    tex = tex.replace(r"\_", r"\_\allowbreak{}")  # identificadores largos con guion bajo (tablas, prosa)
    # rutas largas en código en línea: permitir corte tras "/" y "\"
    tex = re.sub(r"\\texttt\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
                 lambda m: r"\texttt{" + m.group(1).replace("/", r"/\allowbreak{}")
                 .replace(r"\textbackslash{}", r"\textbackslash{}\allowbreak{}") + "}", tex)
    return tex


front, body, back = to_latex(FRONT), to_latex(BODY), to_latex(BACK)

# macros de resaltado que necesita pandoc (de un documento standalone mínimo)
hl = subprocess.run(["pandoc", "-s", "-f", "markdown", "-t", "latex", "--highlight-style=tango"],
                    input="```python\nx=1\n```", capture_output=True, text=True, check=True).stdout
hl = hl[hl.index(r"\usepackage{color}"):]
hl = hl[:hl.index(r"\usepackage{longtable") if r"\usepackage{longtable" in hl else hl.index(r"\setlength{\emergencystretch")]
hl = re.sub(r"\\DefineVerbatimEnvironment\{Highlighting\}\{Verbatim\}\{commandchars=\\\\\\\{\\\}\}\n?", "", hl)

F = FONTS.resolve().as_posix() + "/"
tex = r"""\documentclass[10.5pt,twoside,openany]{book}
\usepackage[paperwidth=6in,paperheight=9in,inner=0.8in,outer=0.6in,top=0.75in,bottom=0.8in,headsep=0.22in,footskip=0.4in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{fontspec}
\usepackage{polyglossia}
\setdefaultlanguage{spanish}
\setmainfont{source-serif-4-latin-400-normal.ttf}[Path=@@VC_FONTDIR@@, ItalicFont=source-serif-4-latin-400-italic.ttf,
  BoldFont=source-serif-4-latin-600-normal.ttf, BoldItalicFont=source-serif-4-latin-600-italic.ttf, Ligatures=TeX]
\newfontfamily\headfont{source-sans-3-latin-600-normal.ttf}[Path=@@VC_FONTDIR@@, BoldFont=source-sans-3-latin-700-normal.ttf, Ligatures=TeX]
\newfontfamily\headlight{source-sans-3-latin-400-normal.ttf}[Path=@@VC_FONTDIR@@, Ligatures=TeX]
\setmonofont{DejaVu Sans Mono}[Scale=0.80]
\usepackage{microtype}
\usepackage{xcolor}
\definecolor{vcaccent}{HTML}{1F5F8B}
\definecolor{vcgray}{HTML}{6B6B6B}
\definecolor{vcquote}{HTML}{F2F5F8}
\usepackage{fvextra}
\usepackage{graphicx}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{enumitem}
\setlist{itemsep=2pt,topsep=4pt,leftmargin=1.3em}
\usepackage{longtable,booktabs,array,calc}
\usepackage[hidelinks,pdftitle={Vertex Forensic Lab: Cazar enjambres de agentes de IA con señuelos, tarpit, un perito local y contención real},pdfauthor={Denis Sánchez Leyva}]{hyperref}
\usepackage{xurl}
\usepackage{bookmark}
\usepackage{etoolbox}
\usepackage[framemethod=default]{mdframed}
\linespread{1.12}
\setlength{\parindent}{1.2em}
\setlength{\parskip}{0pt}
\widowpenalty=10000 \clubpenalty=10000
\emergencystretch=3em \tolerance=1500
\providecommand{\tightlist}{\setlength{\itemsep}{1pt}\setlength{\parskip}{0pt}}
\setcounter{secnumdepth}{-10}
\setcounter{tocdepth}{0}

@@VC_HIGHLIGHT@@
\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\},breaklines,breakanywhere,breaknonspaceingroup,fontsize=\small}
\renewenvironment{Shaded}{\begin{mdframed}[backgroundcolor=vcquote,linewidth=0pt,innerleftmargin=6pt,innerrightmargin=6pt,innertopmargin=5pt,innerbottommargin=5pt,skipabove=8pt,skipbelow=8pt]}{\end{mdframed}}
\RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines,breakanywhere,fontsize=\small,frame=leftline,framerule=1.2pt,rulecolor=\color{vcaccent},xleftmargin=4pt}
\renewenvironment{quote}{\begin{mdframed}[backgroundcolor=vcquote,linecolor=vcaccent,topline=false,bottomline=false,rightline=false,linewidth=2pt,innerleftmargin=8pt,innerrightmargin=8pt,innertopmargin=6pt,innerbottommargin=6pt,skipabove=8pt,skipbelow=8pt]\small\itshape\setlength{\parindent}{0pt}}{\end{mdframed}}

\titleformat{\section}{\headfont\large\color{vcaccent}}{}{0pt}{}
\titlespacing*{\section}{0pt}{16pt plus 4pt}{6pt}
\titleformat{\subsection}{\headfont\normalsize}{}{0pt}{}
\titlespacing*{\subsection}{0pt}{12pt plus 3pt}{4pt}
\titleformat{\subsubsection}{\headfont\small\itshape}{}{0pt}{}
\titlespacing*{\subsubsection}{0pt}{10pt}{3pt}
\titleformat{\chapter}[display]{}{}{0pt}{}
\titlespacing*{\chapter}{0pt}{0pt}{0pt}

\newcommand{\vcrunning}{}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE]{\headlight\footnotesize\color{vcgray}\MakeUppercase{Vertex Forensic Lab}}
\fancyhead[RO]{\headlight\footnotesize\color{vcgray}\vcrunning}
\fancyfoot[LE,RO]{\headlight\small\thepage}
\renewcommand{\headrulewidth}{0pt}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[LE,RO]{\headlight\small\thepage}}

\newcommand{\vcchapter}[2]{%
  \clearpage
  \phantomsection\addcontentsline{toc}{chapter}{\ifstrempty{#1}{#2}{#1 — #2}}%
  \renewcommand{\vcrunning}{#2}%
  \thispagestyle{plain}%
  \vspace*{0.2in}%
  \ifstrempty{#1}{}{{\headlight\small\color{vcaccent}\MakeUppercase{#1}\par}\vspace{6pt}}%
  {\headfont\fontsize{22}{26}\selectfont\raggedright #2\par}%
  \vspace{6pt}{\color{vcaccent}\rule{0.9in}{1.5pt}}\par
  \vspace{0.25in}\noindent\ignorespaces}
\newcommand{\vcbreak}{\par\vspace{8pt}\begin{center}{\color{vcaccent}\textbullet\quad\textbullet\quad\textbullet}\end{center}\vspace{4pt}}

\begin{document}
\frontmatter
\pagestyle{empty}
\begin{titlepage}
\vspace*{1.6in}
{\headfont\fontsize{34}{38}\selectfont Vertex Forensic Lab\par}
\vspace{10pt}{\color{vcaccent}\rule{1.4in}{2pt}}\par\vspace{14pt}
{\headlight\fontsize{15}{19}\selectfont Cazar enjambres de agentes de IA\\con señuelos, tarpit, un perito local\\y contención real\par}
\vspace{12pt}
{\itshape\color{vcgray} Del Canary Token al acta firmada:\\observabilidad forense y defensa activa\\en tu propia máquina\par}
\vfill
{\headfont\large Denis Sánchez Leyva\par}
\vspace{3pt}{\headlight\small\color{vcgray}Vertex Coders LLC · Miami, FL\par}
\vspace{0.3in}
\end{titlepage}
\newpage
\null\vfill
{\footnotesize\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}
\textit{Vertex Forensic Lab: Cazar enjambres de agentes de IA con señuelos, tarpit, un perito local y contención real}

Primera edición, 2026

© 2026 Denis Sánchez Leyva — Vertex Coders LLC. Todos los derechos reservados.

Ninguna parte de esta publicación puede ser reproducida, distribuida o transmitida en cualquier forma o por cualquier medio sin el permiso previo por escrito del autor, salvo en el caso de citas breves para reseñas y ciertos usos no comerciales permitidos por la ley de derechos de autor.

Este libro trata de seguridad defensiva. Las pruebas de ataque que describe se realizaron desde una máquina propia, en una red virtual propia, contra un honeypot construido para recibirlas. No utilices estas técnicas contra sistemas que no sean tuyos o para los que no tengas autorización expresa por escrito.

El código y los ejemplos de este libro se ofrecen con fines educativos, «tal cual», sin garantía de ningún tipo. Un sistema que modifica las reglas del firewall puede cortar la conectividad de la máquina en la que se ejecuta; pruébalo primero en un entorno aislado. El autor no se hace responsable de daños derivados de su uso.

Las marcas y nombres de productos mencionados pertenecen a sus respectivos dueños.

Publicado de forma independiente.\par}
\pagestyle{fancy}
@@VC_FRONT@@
\clearpage
\renewcommand{\vcrunning}{Índice}
\renewcommand{\contentsname}{Índice}
\begingroup
\titleformat{\chapter}[display]{\headfont\fontsize{22}{26}\selectfont}{}{0pt}{}
\titlespacing*{\chapter}{0pt}{0.2in}{0.25in}
\tableofcontents
\endgroup
\mainmatter
@@VC_BODY@@
\backmatter
@@VC_BACK@@
\end{document}
"""
# marcadores únicos: "BACK" a secas coincidía con la palabra LOOPBACK del capítulo 2
tex = tex.replace("@@VC_HIGHLIGHT@@", hl).replace("@@VC_FONTDIR@@", F)
tex = tex.replace("@@VC_FRONT@@", front).replace("@@VC_BODY@@", body).replace("@@VC_BACK@@", back)
tex = tex.replace(r"\begin{document}", r"""\makeatletter
\renewcommand*\l@chapter[2]{\addpenalty{-\@highpenalty}\vskip 0.55em plus 1pt
  \setlength\@tempdima{0pt}\begingroup\parindent\z@\rightskip\@pnumwidth\parfillskip-\@pnumwidth
  \leavevmode\headlight\small #1\nobreak\leaders\hbox{$\m@th\mkern 4mu\hbox{.}\mkern 4mu$}\hfill\nobreak
  \hb@xt@\@pnumwidth{\hss\headlight\small #2}\par\penalty\@highpenalty\endgroup}
\makeatother
\begin{document}""", 1)
(OUT / f"{JOB}.tex").write_text(tex, encoding="utf-8")
for _ in range(3):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"{JOB}.tex"], cwd=OUT,
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:])
        sys.exit(1)
print("OK", OUT / f"{JOB}.pdf")
