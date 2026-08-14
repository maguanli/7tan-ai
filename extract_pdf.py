# -*- coding: utf-8 -*-
import glob, os, sys

pdf_dir = r"D:\用户目录\下载\新建文件夹 123\contract_files"
pdfs = glob.glob(os.path.join(pdf_dir, "*.pdf"))
print("found pdfs:", len(pdfs))
for p in pdfs:
    print("PDF:", p)

if not pdfs:
    sys.exit(1)

text = ""
lib = None
try:
    import pypdf
    lib = "pypdf"
    reader = pypdf.PdfReader(pdfs[0])
    for page in reader.pages:
        text += (page.extract_text() or "")
        text += "\n---PAGE---\n"
except Exception as e:
    print("pypdf fail:", repr(e))
    try:
        import fitz
        lib = "fitz"
        doc = fitz.open(pdfs[0])
        for page in doc:
            text += page.get_text()
            text += "\n---PAGE---\n"
    except Exception as e2:
        print("fitz fail:", repr(e2))
        try:
            import pdfplumber
            lib = "pdfplumber"
            with pdfplumber.open(pdfs[0]) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "")
                    text += "\n---PAGE---\n"
        except Exception as e3:
            print("pdfplumber fail:", repr(e3))

print("lib used:", lib)
out = r"D:\7tan\7tanAI\contract_text.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write(text)
print("chars:", len(text))
print("saved:", out)
