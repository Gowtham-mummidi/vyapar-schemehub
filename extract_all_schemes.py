import os, sys, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.WARNING)

from app.services.ingestion_pipeline import ingestion_pipeline
from google.genai import types

PDF_DIR = r"C:\Users\rk100\Downloads\msme"
OUTPUT = os.path.join(os.path.dirname(__file__), 'extracted_schemes.json')

all_schemes = []
seen_names = set()

def safe(text, maxlen=150):
    s = str(text).encode('utf-8', errors='replace').decode('utf-8')[:maxlen]
    return s.replace('\ufffd', '?')

for pdf_name in sorted(os.listdir(PDF_DIR)):
    if not pdf_name.lower().endswith('.pdf'):
        continue
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_name} ({size_kb:.0f} KB)")
    print('='*60)

    pages = ingestion_pipeline.extract_pdf_pages(pdf_path)
    if not pages:
        print("  No text extracted")
        continue

    # Chunk the document into overlapping sections
    full_text = "\n".join(p[1] for p in pages)
    print(f"  {len(full_text)} chars, {len(pages)} pages")

    client = ingestion_pipeline.gemini_client
    if not client:
        print("  No Gemini client")
        continue

    # Process in chunks of ~30000 chars
    chunk_size = 30000
    overlap = 2000
    start = 0
    doc_schemes = []
    seen_in_doc = set()

    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        segment = full_text[start:end]

        prompt = (
            "Extract ALL government MSME schemes mentioned in the following text. "
            "Return a JSON array. Each object must have:\n"
            '  "name": string,\n'
            '  "description": string (2-3 sentences),\n'
            '  "ministry": string,\n'
            '  "funding_type": "Subsidy"|"Grant"|"Loan"|"Equity"|"Guarantee",\n'
            '  "max_benefit_amount": number (INR) or null,\n'
            '  "eligibility_rules": {\n'
            '    "max_turnover": number or null,\n'
            '    "max_investment": number or null,\n'
            '    "allowed_sectors": ["All"] or list,\n'
            '    "allowed_states": ["All"] or list,\n'
            '    "msme_categories": ["Micro","Small","Medium"]\n'
            '  },\n'
            '  "required_documents": ["list"] or ["Not specified"]\n\n'
            f"Text:\n{segment}\n\n"
            "Return ONLY the JSON array. No markdown."
        )

        try:
            resp = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            cleaned = resp.text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            schemes = json.loads(cleaned.strip())
            if not isinstance(schemes, list):
                schemes = [schemes]
            for s in schemes:
                name = s.get('name', '').strip()
                if name and name not in seen_in_doc:
                    seen_in_doc.add(name)
                    doc_schemes.append(s)
        except Exception as e:
            print(f"  Chunk error: {str(e)[:100]}")

        start = end - overlap if end < len(full_text) else len(full_text)

    print(f"  Found {len(doc_schemes)} unique schemes in this PDF")
    for s in doc_schemes:
        s['_source_file'] = pdf_name
        name = s.get('name', '?')
        if name not in seen_names:
            seen_names.add(name)
            all_schemes.append(s)

print(f"\n{'='*60}")
print(f"Total unique schemes: {len(all_schemes)}")
for i, s in enumerate(all_schemes):
    print(f"  {i+1}. {safe(s.get('name','?'), 80)}  [{s.get('funding_type','?')}]")

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(all_schemes, f, indent=2, ensure_ascii=False, default=str)
print(f"\nSaved: {OUTPUT}")
