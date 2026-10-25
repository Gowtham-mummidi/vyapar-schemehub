import requests, json

r = requests.get('http://localhost:8000/api/v1/schemes',
    headers={'Authorization': 'Bearer simulated-token'})
schemes = r.json()
print(f'Total schemes: {len(schemes)}')
for s in schemes:
    print(f'  - {s["name"]}')
    print(f'    funding: {s["funding_type"]}, pdf: {s.get("pdf_storage_path","none")}')
    rules = s.get('eligibility_rules', {})
    print(f'    rules: {json.dumps(rules)[:200]}')
    print(f'    documents: {s.get("required_documents", [])}')
