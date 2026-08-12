import io
import pdfplumber
from docx import Document


def extract_text(uploaded_file):
    """Extract plain text from an uploaded PDF, DOCX, or TXT file (Streamlit UploadedFile)."""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if name.endswith(".pdf"):
        text_parts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    # .txt or anything else: decode as plain text
    return data.decode("utf-8", errors="ignore")
