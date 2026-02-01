from pypdf import PdfReader

def load_pdf(path: str):
    """
    Returns a list of text "pages" from a PDF file.
    Each element corresponds to a PDF page.
    """
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages.append(text.strip())
    return pages
