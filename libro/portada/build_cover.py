"""
build_cover.py — Portada envolvente KDP de "Vertex Forensic Lab" (paperback 6x9, papel blanco) + portada eBook.
Mismo diseño que las de "Vertex-Core" y "Vertex-Core SQL". Arte: arte.png (generado con build_art.py).

Uso, desde E:\\vertex-forensic-lab\\libro\\portada:
  python build_art.py      # genera (o regenera) el arte
  python build_cover.py
Requiere: reportlab, Pillow y pdftoppm (poppler) para la versión eBook.
IMPORTANTE: PAGES tiene que ser el número real de páginas del interior (build/vertex-forensic-lab.pdf):
cambia el ancho del lomo. Compila primero el PDF y actualiza el número.
"""
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph

HERE = Path(__file__).parent
FONTS = HERE.parent / "fonts"
ART = HERE / "arte.png"

PAGES = 99                          # páginas del interior (build/vertex-forensic-lab.pdf, 6 nov 2026)
SPINE = PAGES * 0.002252            # papel blanco, B/N
BLEED = 0.125
TRIM_W, TRIM_H = 6.0, 9.0
W = BLEED + TRIM_W + SPINE + TRIM_W + BLEED
H = BLEED + TRIM_H + BLEED

for name, f in [("Serif", "source-serif-4-latin-400-normal.ttf"), ("SerifIt", "source-serif-4-latin-400-italic.ttf"),
                ("SerifSB", "source-serif-4-latin-600-normal.ttf"), ("Sans", "source-sans-3-latin-400-normal.ttf"),
                ("SansSB", "source-sans-3-latin-600-normal.ttf"), ("SansB", "source-sans-3-latin-700-normal.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / f)))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="SerifSB", italic="SerifIt", boldItalic="SerifSB")

BG = HexColor("#060B13")
WHITE = HexColor("#F2F5F8")
SOFT = HexColor("#B9C6D3")
ACCENT = HexColor("#22D3EE")       # cian del arte
AMBER = HexColor("#F59E0B")


def cover_image(c, x, y, w, h):
    """Dibuja el arte cubriendo (x,y,w,h), recortando lo que sobre, centrado."""
    im = Image.open(ART)
    iw, ih = im.size
    s = max(w / iw, h / ih)
    dw, dh = iw * s, ih * s
    c.saveState()
    p = c.beginPath(); p.rect(x, y, w, h); c.clipPath(p, stroke=0, fill=0)
    c.drawImage(ImageReader(im), x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)
    c.restoreState()


def front_text(c, x0, y0, w, h, top_safe, bottom_safe, left_safe):
    lx = x0 + left_safe
    top = y0 + h - top_safe
    c.setFillColor(WHITE)
    c.setFont("SansB", 36)  # 19 caracteres: a 42 pt se saldría del área segura
    c.drawString(lx, top - 34, "Vertex Forensic Lab")
    c.setFillColor(ACCENT)
    c.rect(lx + 2, top - 52, 1.25 * inch, 2.2, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Sans", 19)
    c.drawString(lx + 1, top - 82, "Cazar enjambres de agentes de IA")
    c.drawString(lx + 1, top - 105, "con señuelos, tarpit, un perito local")
    c.drawString(lx + 1, top - 128, "y contención real")
    c.setFillColor(SOFT)
    c.setFont("SerifIt", 11.5)
    c.drawString(lx + 1, top - 153, "Del Canary Token al acta firmada: defensa activa en tu propia máquina")
    c.setFillColor(WHITE)
    c.setFont("SansSB", 17)
    c.drawString(lx + 1, y0 + bottom_safe + 16, "Denis Sánchez Leyva")
    c.setFillColor(SOFT)
    c.setFont("Sans", 9.5)
    c.drawString(lx + 1, y0 + bottom_safe, "VERTEX CODERS LLC")


def paperback():
    out = HERE / "Vertex-Forensic-Lab-portada-paperback.pdf"
    c = canvas.Canvas(str(out), pagesize=(W * inch, H * inch), initialFontName="Sans")
    c.setTitle("Vertex Forensic Lab — portada paperback"); c.setAuthor("Denis Sánchez Leyva")
    c.setFillColor(BG); c.rect(0, 0, W * inch, H * inch, stroke=0, fill=1)

    # ---------- portada (derecha) ----------
    fx = (BLEED + TRIM_W + SPINE) * inch
    cover_image(c, fx, 0, (TRIM_W + BLEED) * inch, H * inch)
    front_text(c, fx, 0, (TRIM_W + BLEED) * inch, H * inch,
               top_safe=(BLEED + 0.55) * inch, bottom_safe=(BLEED + 0.5) * inch, left_safe=0.45 * inch)

    # ---------- lomo ----------
    sx = (BLEED + TRIM_W) * inch
    c.setFillColor(HexColor("#08111C")); c.rect(sx, 0, SPINE * inch, H * inch, stroke=0, fill=1)
    c.saveState()
    c.translate(sx + SPINE * inch / 2, H * inch / 2)
    c.rotate(-90)                      # se lee de arriba abajo (norma en EE. UU.)
    fs = 7.5
    t1, t2 = "VERTEX FORENSIC LAB", "   ·   DENIS SÁNCHEZ LEYVA"
    w1 = pdfmetrics.stringWidth(t1, "SansSB", fs); w2 = pdfmetrics.stringWidth(t2, "Sans", fs)
    base = -fs * 0.35
    c.setFont("SansSB", fs); c.setFillColor(WHITE)
    c.drawString(-(w1 + w2) / 2, base, t1)
    c.setFont("Sans", fs); c.setFillColor(SOFT)
    c.drawString(-(w1 + w2) / 2 + w1, base, t2)
    c.restoreState()

    # ---------- contraportada (izquierda) ----------
    m = (BLEED + 0.5) * inch
    bx, bw = m, (TRIM_W - 1.0) * inch
    top = H * inch - (BLEED + 0.6) * inch
    hook = ParagraphStyle("hook", fontName="SansSB", fontSize=17.5, leading=23, textColor=WHITE)
    body = ParagraphStyle("body", fontName="Serif", fontSize=11.3, leading=16, textColor=SOFT, spaceAfter=10)
    bul = ParagraphStyle("bul", parent=body, leftIndent=12, bulletIndent=0, spaceAfter=5,
                         bulletColor=ACCENT, bulletFontName="SansB")
    quote = ParagraphStyle("q", fontName="SerifIt", fontSize=13.5, leading=18, textColor=WHITE, leftIndent=12,
                           spaceBefore=12, spaceAfter=14)
    small = ParagraphStyle("s", fontName="Serif", fontSize=9.8, leading=13.5, textColor=SOFT)
    story = [
        Paragraph("Uno explora. Otro ataca con lo que el primero encontró. "
                  "Tu firewall ve dos visitantes y no ve el enjambre.", hook),
        Paragraph("&nbsp;", ParagraphStyle("sp", fontName="Serif", fontSize=8, leading=12)),
        Paragraph("Este libro construye <b>Vertex Forensic Lab</b>, un laboratorio de defensa activa contra "
                  "enjambres de agentes de IA que cabe en tu portátil. Probado con tráfico real desde Parrot, "
                  "registró 12 transferencias de un token robado del Scout al Exploit, hizo pagar a cada carga "
                  "unos 6.4 segundos frente a los 0.2 de un escáner, rechazó los intentos de tomar el mando y "
                  "dejó al atacante fuera con una regla real de Windows Firewall.", body),
        Paragraph("Lo que aprenderás:", ParagraphStyle("h", parent=body, textColor=WHITE, fontName="SerifSB",
                                                     spaceAfter=6, spaceBefore=4)),
    ]
    for b in ["Medir el tráfico: huella, entropía y una cadencia que no mienta",
              "Una trampa con firma HMAC que delata la relación Scout-Exploit",
              "Un tarpit que hace que atacar sea caro",
              "Un perito que decide con evidencia comprobable",
              "Contener sin dispararte en el pie, y que no te usen el escudo",
              "Firmar un acta que se pueda defender, y abrirla por MCP"]:
        story.append(Paragraph(b, bul, bulletText="•"))
    story.append(Paragraph("«El modelo puede asistir, pero no puede dar fe.»", quote))
    story.append(Paragraph("<b>Denis Sánchez Leyva</b> es fundador de Vertex Coders LLC (Miami) y autor de "
                           "más de una docena de libros sobre inteligencia artificial, agentes y MCP. "
                           "Trabaja de noche y programa en las horas libres.", small))
    fr = Frame(bx, 1.9 * inch, bw, top - 1.9 * inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
               showBoundary=0)
    fr.addFromList(story, c)
    assert not story, "la contraportada no cabe"
    # pie: editorial (izquierda; abajo a la derecha va el código de barras de KDP)
    c.setFillColor(ACCENT); c.setFont("SansSB", 9.5)
    c.drawString(bx, m + 0.42 * inch, "VERTEX CODERS LLC")
    c.setFillColor(SOFT); c.setFont("Sans", 8.5)
    c.drawString(bx, m + 0.24 * inch, "Seguridad defensiva · Miami, FL")
    c.showPage(); c.save()
    return out


def ebook():
    """Portada Kindle 1600x2560 (1:1.6). Se dibuja a 6x9.6 in y se rasteriza a 1600x2560."""
    out = HERE / "ebook_tmp.pdf"
    ew, eh = 6.0 * inch, 9.6 * inch
    c = canvas.Canvas(str(out), pagesize=(ew, eh), initialFontName="Sans")
    c.setFillColor(BG); c.rect(0, 0, ew, eh, stroke=0, fill=1)
    cover_image(c, 0, 0, ew, eh)
    front_text(c, 0, 0, ew, eh, top_safe=0.55 * inch, bottom_safe=0.5 * inch, left_safe=0.45 * inch)
    c.showPage(); c.save()
    return out


if __name__ == "__main__":
    import subprocess
    p = paperback()
    e = ebook()
    subprocess.run(["pdftoppm", "-r", str(1600 / 6), "-jpeg", "-jpegopt", "quality=95", "-singlefile", str(e),
                    str(HERE / "eb")], check=True)
    im = Image.open(HERE / "eb.jpg").convert("RGB").resize((1600, 2560), Image.LANCZOS)
    im.save(HERE / "Vertex-Forensic-Lab-portada-ebook.jpg", quality=95, dpi=(300, 300))
    (HERE / "eb.jpg").unlink(); e.unlink()
    print(f"OK  paperback {W:.3f} x {H:.3f} in (lomo {SPINE:.3f} in) -> {p.name}")
    print("OK  ebook 1600x2560 -> Vertex-Forensic-Lab-portada-ebook.jpg")
