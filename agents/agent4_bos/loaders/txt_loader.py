def load_txt(path: str, words_per_page: int = 500):
    """
    Returns a list of text "pages" from a TXT file.
    Each page contains up to `words_per_page` words.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    words = text.split()
    pages = []
    for i in range(0, len(words), words_per_page):
        pages.append(" ".join(words[i:i+words_per_page]))
    
    return pages
