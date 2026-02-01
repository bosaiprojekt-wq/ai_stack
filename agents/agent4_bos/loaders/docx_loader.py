from docx import Document

def load_docx(path: str, paragraphs_per_page: int = 50):
    """
    Returns a list of text "pages" from a DOCX file.
    Each page contains up to `paragraphs_per_page` paragraphs.
    """
    doc = Document(path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    pages = []
    for i in range(0, len(paragraphs), paragraphs_per_page):
        pages.append("\n".join(paragraphs[i:i+paragraphs_per_page]))
    
    return pages
