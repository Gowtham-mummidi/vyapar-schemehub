import os, sys, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

def safe(text, maxlen=150):
    return str(text).encode('utf-8', errors='replace').decode('utf-8')[:maxlen]

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from app.services.ingestion_pipeline import ingestion_pipeline
from google.genai import types

PDF_DIR = r"C:\Users\rk100\Downloads\msme"
OUTPUT = os.path.join(os.path.dirname(__file__), 'extracted_schemes.json')

pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
pdf_files.sort()
print(f"Found {len(pdf_files)} PDF files")

all_schemes = []

for pdf_name in pdf_files:
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_name} ({size_kb:.0f} KB)")
    print('='*60)

    pages = ingestion_pipeline.extract_pdf_pages(pdf_path)
    if not pages:
        print(f"  WARNING: No text extracted")
        continue

    full_text = "\n".join(p[1] for p in pages)
    text_len = len(full_text)
    print(f"  Extracted {text_len} chars from {len(pages)} pages")
    print(f"  Preview: {safe(full_text, 150)}")

    result = ingestion_pipeline.extract_full_scheme(full_text)
    if result and result.get('name'):
        print(f"  [OK] Extracted: {safe(result['name'], 80)}")
        result['_source_file'] = pdf_name
        all_schemes.append(result)
        continue

    print(f"  Single failed, trying multi-scheme extract...")
    try:
        client = ingestion_pipeline.gemini_client
        if not client:
            print(f"  No Gemini client")
            continue
        truncated = full_text[:25000]
        prompt = (
            "Extract ALL government MSME schemes mentioned in the following document. "
            "Return a JSON array of scheme objects. Each object must have:\n"
            '  "name": string (scheme name),\n'
            '  "description": string (2-3 sentences),\n'
            '  "ministry": string,\n'
            '  "funding_type": "Subsidy"|"Grant"|"Loan"|"Equity"|"Guarantee",\n'
            '  "max_benefit_amount": number (INR),\n'
            '  "eligibility_rules": {\n'
            '    "max_turnover": number|null,\n'
            '    "max_investment": number|null,\n'
            '    "allowed_sectors": ["All"] or list,\n'
            '    "allowed_states": ["All"] or list,\n'
            '    "msme_categories": ["Micro","Small","Medium"]\n'
            '  },\n'
            '  "required_documents": ["list"]\n\n'
            f"Document:\n{truncated}\n\n"
            "Return ONLY the JSON array. No markdown formatting."
        )
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
        multi = json.loads(cleaned.strip())
        if isinstance(multi, list) and len(multi) > 0:
            for m in multi:
                m['_source_file'] = pdf_name
            all_schemes.extend(multi)
            print(f"  [OK] Extracted {len(multi)} schemes")
        else:
            print(f"  No schemes in response")
    except Exception as e:
        print(f"  Multi-extract failed: {str(e)[:150]}")

print(f"\n{'='*60}")
print(f"Total: {len(all_schemes)} schemes")
for i, s in enumerate(all_schemes):
    name = safe(s.get('name', '?'), 80)
    src = s.get('_source_file', '?')
    print(f"  {i+1}. {name} (from {src})")

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(all_schemes, f, indent=2, ensure_ascii=False, default=str)
print(f"\nSaved: {OUTPUT}")
