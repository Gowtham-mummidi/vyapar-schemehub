import logging
import os
import json
import fitz  # PyMuPDF
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app.models import Scheme
from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

def _simple_chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            last_space = text.rfind(' ', start + chunk_size - overlap, end)
            if last_space > start:
                end = last_space
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else len(text)
    return chunks if chunks else [text]

class IngestionPipeline:
    def __init__(self):
        self.gemini_client = None
        try:
            api_key = settings.GEMINI_API_KEY if settings.GEMINI_API_KEY != "placeholder_gemini_key" else None
            if api_key:
                self.gemini_client = genai.Client(api_key=api_key)
            else:
                self.gemini_client = genai.Client()
        except Exception:
            pass

    def extract_pdf_pages(self, pdf_path: str) -> List[Tuple[int, str]]:
        """
        Extracts text from PDF page by page.
        Returns:
            List of tuples: (page_number, text_content)
        """
        pages_content = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    pages_content.append((page_num + 1, text))
            doc.close()
        except Exception as e:
            logger.error(f"Failed to parse PDF document pages: {str(e)}")
        return pages_content

    def run_ingestion(self, db: Session, scheme: Scheme, temp_file_path: str) -> bool:
        """
        Runs the complete scheme PDF ingestion pipeline:
        1. Page-by-page text extraction
        2. Chunking via RecursiveCharacterTextSplitter
        3. Indexing chunks in Qdrant Vector DB
        4. Auto-generating structured eligibility rules using Gemini
        """
        # Step 1: Extract pages
        pages = self.extract_pdf_pages(temp_file_path)
        if not pages:
            logger.warning("No text extracted from PDF. Aborting pipeline.")
            return False
            
        full_text = "\n".join([p[1] for p in pages])
        
        # Step 2: Split text into chunks with page numbers in metadata
        chunks = []
        metadatas = []
        
        for page_num, page_text in pages:
            page_chunks = _simple_chunk_text(page_text)
            for i, chunk in enumerate(page_chunks):
                chunks.append(chunk)
                metadatas.append({
                    "page": page_num,
                    "chunk_index": i,
                    "title": scheme.name
                })
                
        # Step 3: Upsert chunks to Qdrant collection
        try:
            rag_service.add_scheme_chunks(
                scheme_id=str(scheme.id),
                chunks=chunks,
                metadata=metadatas
            )
        except Exception as e:
            logger.error(f"Vector database ingestion failed: {str(e)}")
            # Continue so PostgreSQL database can still be updated
            
        # Step 4: Extract Structured Eligibility Rules using Gemini
        structured_rules = self.extract_rules_with_llm(full_text)
        if structured_rules:
            scheme.eligibility_rules = structured_rules
            # Update funding type and max benefit if found
            if "max_benefit_amount" in structured_rules:
                try:
                    from decimal import Decimal
                    scheme.max_benefit_amount = Decimal(str(structured_rules["max_benefit_amount"]))
                except Exception:
                    pass
            if "funding_type" in structured_rules:
                scheme.funding_type = structured_rules["funding_type"]
                
            db.commit()
            logger.info(f"Successfully extracted structured rules for: {scheme.name}")
            
        return True

    def extract_full_scheme(self, document_text: str) -> Dict[str, Any]:
        """
        Extracts full scheme details (name, description, ministry, eligibility rules, etc.) from PDF text using Gemini.
        Returns a dict suitable for creating a Scheme object.
        Falls back to defaults if Gemini is unavailable.
        """
        if not self.gemini_client:
            logger.warning("Gemini Client not configured. Cannot extract scheme from PDF.")
            return {}

        truncated = document_text[:25000]
        prompt = (
            "Analyze the following Indian government MSME scheme document and extract all details "
            "into a structured JSON object. Use the exact schema below.\n\n"
            "Schema:\n"
            "{\n"
            '  "name": "Full scheme name as a string",\n'
            '  "description": "Detailed description (2-4 sentences)",\n'
            '  "ministry": "Ministry name (e.g. Ministry of MSME, Govt of India)",\n'
            '  "funding_type": "One of: Grant, Subsidy, Loan, Equity, Guarantee",\n'
            '  "max_benefit_amount": number (maximum benefit in INR, or 0 if not found),\n'
            '  "official_link": "URL string or empty string",\n'
            '  "eligibility_rules": {\n'
            '    "max_turnover": number or null,\n'
            '    "max_investment": number or null,\n'
            '    "min_business_age": number or null,\n'
            '    "max_business_age": number or null,\n'
            '    "allowed_sectors": ["list of sectors"] or ["All"],\n'
            '    "allowed_states": ["list of states"] or ["All"],\n'
            '    "allowed_owner_categories": ["SC","ST","OBC","Female","Minority","General"] or ["All"],\n'
            '    "required_registrations": ["GST","Udyam","PAN","Aadhaar"] or [],\n'
            '    "msme_categories": ["Micro","Small","Medium"]\n'
            '  },\n'
            '  "required_documents": ["list of document names"]\n'
            '}\n\n'
            f"Document text:\n{truncated}\n\n"
            "Return ONLY the raw JSON object. No markdown, no code fences."
        )

        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            cleaned = response.text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            result = json.loads(cleaned.strip())
            logger.info(f"Extracted scheme from PDF: {result.get('name', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to extract scheme from PDF: {str(e)}")
            return {}

    def extract_rules_with_llm(self, document_text: str) -> Dict[str, Any]:
        """
        Prompts Gemini 2.5 Flash to convert raw document text into JSON structured eligibility rules.
        """
        if not self.gemini_client:
            logger.warning("Gemini Client not configured. Returning default empty rules.")
            return self._get_default_rules()

        # We truncate document_text to avoid exceeding tokens if document is very large
        truncated_text = document_text[:20000]

        prompt = (
            "Analyze the following Indian government MSME scheme document text and extract eligibility rules "
            "into a structured JSON format. Ensure all numeric limits are parsed as numbers.\n\n"
            "Required Output Schema:\n"
            "{\n"
            "  \"max_turnover\": float or null, (Maximum turnover in INR allowed, e.g. 50000000)\n"
            "  \"max_investment\": float or null, (Maximum investment in plant & machinery in INR, e.g. 10000000)\n"
            "  \"min_business_age\": int or null, (Minimum operational age in years)\n"
            "  \"max_business_age\": int or null, (Maximum age of business in years)\n"
            "  \"allowed_sectors\": list of strings or null, (e.g. [\"Manufacturing\", \"Services\", \"Textiles\", \"IT\"] or null if all)\n"
            "  \"allowed_states\": list of strings or null, (e.g. [\"Maharashtra\", \"Gujarat\"] or [\"All\"])\n"
            "  \"allowed_owner_categories\": list of strings or null, (e.g. [\"SC\", \"ST\", \"OBC\", \"Female\", \"Minority\", \"General\"])\n"
            "  \"required_registrations\": list of strings or null, (e.g. [\"GST\", \"Udyam\", \"PAN\"])\n"
            "  \"msme_categories\": list of strings or null, (e.g. [\"Micro\", \"Small\", \"Medium\"])\n"
            "  \"funding_type\": string (one of: \"Grant\", \"Subsidy\", \"Loan\", \"Equity\", \"Guarantee\")\n"
            "  \"max_benefit_amount\": float or null (Maximum funding benefit in INR, e.g. 2000000)\n"
            "}\n\n"
            f"Scheme Document Text:\n{truncated_text}\n\n"
            "Return ONLY the raw JSON block without formatting wrappers like ```json."
        )

        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                )
            )
            
            # Parse text as JSON
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
                
            rules_dict = json.loads(cleaned_text.strip())
            return rules_dict
        except Exception as e:
            logger.error(f"Failed to extract structured rules via Gemini: {str(e)}")
            return self._get_default_rules()

    def _get_default_rules(self) -> Dict[str, Any]:
        return {
            "max_turnover": None,
            "max_investment": None,
            "min_business_age": None,
            "max_business_age": None,
            "allowed_sectors": ["All"],
            "allowed_states": ["All"],
            "allowed_owner_categories": ["All"],
            "required_registrations": [],
            "msme_categories": ["Micro", "Small", "Medium"],
            "funding_type": "Subsidy",
            "max_benefit_amount": 0.0
        }

# Singleton instance
ingestion_pipeline = IngestionPipeline()
