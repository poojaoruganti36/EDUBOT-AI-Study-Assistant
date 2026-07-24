from PyPDF2 import PdfReader


def extract_pdf_text(files) -> str:
    pages: list[str] = []
    for file in files:
        reader = PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text.strip())
    return "\n\n".join(pages)
