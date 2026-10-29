"""Render a 10-document sample of the corpus as PDFs (reportlab) so the
PDF-parsing path in ingest.parse_pdf is exercised on real files."""
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas


def render_sample(docs, out_dir, n=10):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for doc in docs[:n]:
        path = out_dir / f"{doc['doc_id']}.pdf"
        c = canvas.Canvas(str(path), pagesize=LETTER)
        for page_text in doc["pages"]:
            y = 750
            c.setFont("Helvetica", 11)
            words, line = page_text.split(), ""
            for w in words:
                if len(line) + len(w) > 95:
                    c.drawString(40, y, line)
                    y -= 15
                    line = w + " "
                else:
                    line += w + " "
            if line:
                c.drawString(40, y, line)
            c.showPage()
        c.save()
    return n
