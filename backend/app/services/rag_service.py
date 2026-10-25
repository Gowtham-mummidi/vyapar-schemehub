import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from google import genai
from google.genai import types
from app.config import settings
from app.services.embedding_service import embedding_service
from app.models import BusinessProfile, Scheme

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.qdrant_client = None
        self.gemini_client = None
        self.collection_name = settings.QDRANT_COLLECTION_NAME

        # Initialize Qdrant Client
        try:
            if settings.QDRANT_API_KEY:
                self.qdrant_client = QdrantClient(
                    url=settings.QDRANT_HOST,
                    api_key=settings.QDRANT_API_KEY
                )
            else:
                self.qdrant_client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT
                )
            logger.info("Qdrant Client initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant ({str(e)}). Running in fallback/mock search mode.")

        # Initialize Gemini Client
        try:
            # The new google-genai SDK uses client.models.generate_content
            # It expects api_key or reads from GEMINI_API_KEY environment variable
            # If the user hasn't set it yet, we use a placeholder or handle authentication errors gracefully
            api_key = settings.GEMINI_API_KEY if settings.GEMINI_API_KEY != "placeholder_gemini_key" else None
            if api_key:
                self.gemini_client = genai.Client(api_key=api_key)
            else:
                # Try to auto-resolve from environment variable
                self.gemini_client = genai.Client()
            logger.info("Gemini Client initialized successfully.")
        except Exception as e:
             logger.warning(f"Could not initialize Gemini Client ({str(e)}). LLM features will fall back to rule-based mock strings.")

    def ensure_collection(self):
        if not self.qdrant_client:
            return
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=3072,
                        distance=qmodels.Distance.COSINE
                    )
                )
            try:
                self.qdrant_client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="scheme_id",
                    field_schema="keyword"
                )
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {str(e)}")

    def add_scheme_chunks(self, scheme_id: str, chunks: List[str], metadata: List[Dict[str, Any]]):
        """
        Generates embeddings for chunks and upserts them into Qdrant collection.
        """
        self.ensure_collection()
        if not self.qdrant_client:
            logger.warning("Qdrant client not connected. Skipping vector storage.")
            return

        try:
            embeddings = embedding_service.get_embeddings(chunks)
            points = []
            for i, (chunk, vector, meta) in enumerate(zip(chunks, embeddings, metadata)):
                # Inject scheme_id into metadata
                meta["scheme_id"] = str(scheme_id)
                meta["content"] = chunk
                
                # Create a point ID
                import uuid
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{scheme_id}_{i}"))
                
                points.append(qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=meta
                ))

            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Successfully indexed {len(points)} chunks for scheme {scheme_id} in Qdrant.")
        except Exception as e:
            logger.error(f"Failed to upsert points to Qdrant: {str(e)}")

    def delete_scheme_chunks(self, scheme_id: str):
        """
        Deletes vector points matching scheme_id.
        """
        if not self.qdrant_client:
             return
        try:
             self.qdrant_client.delete(
                  collection_name=self.collection_name,
                  points_selector=qmodels.FilterSelector(
                       filter=qmodels.Filter(
                            must=[
                                 qmodels.FieldCondition(
                                      key="scheme_id",
                                      match=qmodels.MatchValue(value=str(scheme_id))
                                 )
                            ]
                       )
                  )
             )
             logger.info(f"Deleted vector chunks for scheme {scheme_id}.")
        except Exception as e:
             logger.error(f"Failed to delete scheme vectors: {str(e)}")

    def search_similar_chunks(self, query: str, scheme_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search in Qdrant.
        """
        if not self.qdrant_client:
            logger.warning("Qdrant client offline. Returning empty query contexts.")
            return []

        try:
            query_vector = embedding_service.get_embedding(query)
            
            # Apply filter if scheme_id is provided
            query_filter = None
            if scheme_id:
                query_filter = qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="scheme_id",
                            match=qmodels.MatchValue(value=str(scheme_id))
                        )
                    ]
                )
                
            search_results = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit
            )
            
            results = []
            for hit in search_results.points:
                results.append({
                    "score": hit.score,
                    "content": hit.payload.get("content", ""),
                    "scheme_id": hit.payload.get("scheme_id", ""),
                    "page": hit.payload.get("page", 1),
                    "title": hit.payload.get("title", "Government Scheme document")
                })
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            results = []

        if not results:
            try:
                from app.database import SessionLocal
                from app.models import Scheme
                from sqlalchemy import or_
                with SessionLocal() as db:
                    tokens = [w.strip() for w in query.split() if len(w.strip()) > 3]
                    matched_schemes = []
                    if scheme_id:
                        matched_schemes = db.query(Scheme).filter(Scheme.id == scheme_id).all()
                    elif tokens:
                        filters = [Scheme.name.ilike(f"%{token}%") for token in tokens] + [Scheme.description.ilike(f"%{token}%") for token in tokens]
                        matched_schemes = db.query(Scheme).filter(or_(*filters)).limit(limit).all()
                    
                    for s in matched_schemes:
                        content = f"Scheme Name: {s.name}\nMinistry: {s.ministry}\nFunding Type: {s.funding_type}\nMax Benefit: ₹{float(s.max_benefit_amount or 0):,.2f}\nDescription: {s.description}\nEligibility: {s.eligibility_rules}\nRequired Documents: {', '.join(s.required_documents or [])}"
                        results.append({
                            "score": 1.0,
                            "content": content,
                            "scheme_id": str(s.id),
                            "page": 1,
                            "title": s.name
                        })
            except Exception as e:
                logger.warning(f"Database fallback context search failed: {e}")

        return results

    def _fallback_answer(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        query_lower = query.lower().strip()

        answers = {
            "cgtmse": (
                "**Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)**\n\n"
                "CGTMSE provides collateral-free credit guarantees to Micro and Small Enterprises. "
                "Key features:\n"
                "- Collateral-free loans up to ₹5 Crore (₹2 Crore for retail/MSME)\n"
                "- Covers term loans and working capital facilities\n"
                "- Guarantee cover up to 85% for micro enterprises, 75% for small enterprises\n"
                "- Eligible for new and existing MSMEs\n"
                "- Nominal annual guarantee fee of 0.75-1.0%"
            ),
            "turnover": (
                "**How Annual Turnover Affects MSME Eligibility**\n\n"
                "Annual turnover is a key criterion for MSME classification and scheme eligibility:\n\n"
                "- **Micro Enterprise**: Turnover ≤ ₹5 Crore\n"
                "- **Small Enterprise**: Turnover ≤ ₹50 Crore\n"
                "- **Medium Enterprise**: Turnover ≤ ₹250 Crore\n\n"
                "Higher turnover can make you eligible for larger loan amounts under schemes like CGTMSE, "
                "but may also disqualify you from micro-enterprise-specific benefits. "
                "Many state subsidies have specific turnover brackets for maximum benefit eligibility."
            ),
            "women": (
                "**Special Benefits for Women Entrepreneurs**\n\n"
                "Several MSME schemes offer additional benefits for women-owned enterprises:\n\n"
                "1. **Bharatiya Mahila Bank Business Loan** - Loans up to ₹20 Crore for women entrepreneurs\n"
                "2. **Mudra Yojana** - Priority processing for women applicants under Shishu, Kishor, Tarun categories\n"
                "3. **Stand-Up India** - Loans up to ₹1 Crore for women entrepreneurs from SC/ST categories\n"
                "4. **Annapurna Scheme** - Working capital loans for women in food catering business\n"
                "5. **Dena Shakti Scheme** - Loans up to ₹20 Lakh for women in retail, manufacturing, micro-credit\n\n"
                "Many state schemes also offer 5-10% fee concession or 1-2% interest subvention for women entrepreneurs."
            ),
            "document": (
                "**Common Documents Required for MSME Registration & Schemes**\n\n"
                "1. **Udyam Registration Certificate** (mandatory for all MSME benefits)\n"
                "2. **Aadhaar Card** of the proprietor/partners/directors\n"
                "3. **PAN Card** of the business entity\n"
                "4. **GST Registration Certificate** (if applicable)\n"
                "5. **Bank Statement** (last 6-12 months)\n"
                "6. **Business Address Proof** (rent agreement/utility bill/property deed)\n"
                "7. **Project Report / Business Plan** (for loan/subsidy applications)\n"
                "8. **Financial Statements** (audited P&L, balance sheet for last 2-3 years)\n"
                "9. **CA Certification of Turnover and Investment**\n"
                "10. **MSME Classification Certificate** (Udyam Certificate)"
            ),
            "udyam": (
                "**Udyam Registration**\n\n"
                "Udyam is the government's online portal for MSME registration:\n\n"
                "- Completely free online registration process\n"
                "- Requires Aadhaar number and PAN\n"
                "- Registration is instant once verified\n"
                "- Certificate includes Udyam Registration Number (URN)\n"
                "- Valid for lifetime, no renewal required\n"
                "- Registration link: https://udyamregistration.gov.in\n\n"
                "Benefits of Udyam registration: Priority sector lending, collateral-free loans, "
                "subsidies on patent registration, and eligibility for government tenders."
            ),
            "pm mudra": (
                "**Pradhan Mantri Mudra Yojana (PMMY)**\n\n"
                "Mudra provides loans up to ₹10 Lakh to non-corporate, non-farm small/micro enterprises:\n\n"
                "- **Shishu**: Loans up to ₹50,000 (startups and early-stage businesses)\n"
                "- **Kishor**: Loans from ₹50,001 to ₹5 Lakh (growth-stage businesses)\n"
                "- **Tarun**: Loans from ₹5,00,001 to ₹10 Lakh (established businesses)\n\n"
                "Interest rates range from 8-12% depending on the lending institution. "
                "No collateral or third-party guarantee required for most Mudra loans."
            ),
            "subsidy": (
                "**MSME Subsidy Schemes Overview**\n\n"
                "Common subsidy types available for MSMEs:\n\n"
                "1. **Capital Investment Subsidy** - 15-25% subsidy on plant & machinery for units in backward areas\n"
                "2. **Interest Subsidy** - 2-3% interest subvention on term loans\n"
                "3. **Patent Subsidy** - 50% rebate on patent filing costs (national + international)\n"
                "4. **ISO Certification Subsidy** - 75% reimbursement up to ₹75,000\n"
                "5. **Bar Code Subsidy** - 75% of registration cost up to ₹15,000\n"
                "6. **Market Development Assistance** - Support for international trade fairs/exhibitions\n\n"
                "Eligibility and subsidy amounts vary by state and enterprise category."
            ),
            "eligibility": (
                "**MSME Eligibility Criteria**\n\n"
                "Eligibility for MSME schemes depends on multiple factors:\n\n"
                "1. **Enterprise Classification** - Micro/Small/Medium based on investment & turnover\n"
                "2. **Sector** - Some schemes target specific industries (textiles, food processing, etc.)\n"
                "3. **Location** - State-specific schemes may require local registration\n"
                "4. **Business Age** - Minimum 1-3 years operational for certain schemes\n"
                "5. **Owner Demographics** - SC/ST/OBC/Women/Minority categories get priority\n"
                "6. **Registration Status** - Udyam, GST, and other certificates required\n\n"
                "Use our profile builder to check which schemes match your specific parameters."
            ),
        }

        for keyword, answer in answers.items():
            if keyword in query_lower:
                return answer

        if contexts:
            snippets = "\n\n".join(
                f"**Source**: {c.get('title', 'Document')} (Page {c.get('page', 1)})\n{c.get('content', '')[:500]}"
                for c in contexts[:2]
            )
            return (
                f"I found relevant information from the document database. Here are the matching excerpts:\n\n{snippets}\n\n"
                f"For a more detailed AI-generated response, please ensure the Gemini API key has available quota."
            )

        return (
            "I'm your MSME Scheme Assistant. I can help you with questions about:\n\n"
            "• **CGTMSE** - Collateral-free credit guarantee details\n"
            "• **Turnover** - How annual turnover affects eligibility\n"
            "• **Women Entrepreneurs** - Special benefits and schemes\n"
            "• **Documents** - Required documents for MSME registration\n"
            "• **Udyam Registration** - How to register\n"
            "• **Mudra Yojana** - PM Mudra loan details\n"
            "• **Subsidies** - Available MSME subsidy schemes\n"
            "• **Eligibility** - General MSME eligibility criteria\n\n"
            "Please type any of these topics for detailed information, or ask a specific question about your scheme eligibility."
        )

    def answer_query(self, query: str, scheme_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves context chunks and answers questions using Gemini 2.0 Flash.
        Falls back to rule-based answers when Gemini API is unavailable.
        """
        contexts = self.search_similar_chunks(query, scheme_id=scheme_id, limit=4)
        context_str = "\n\n".join([f"--- Context {i+1} (Source: {c['title']}, Page: {c['page']}) ---\n{c['content']}" for i, c in enumerate(contexts)])
        
        system_instruction = (
            "You are an expert government scheme assistant for Indian MSMEs. "
            "Use the provided document context fragments to answer the user's questions. "
            "If no document context is provided or the answer cannot be found in the context, "
            "answer from your general knowledge about Indian MSME schemes, eligibility criteria, "
            "and government policies. Always be helpful, clear, and structured. "
            "Mention that you're providing general guidance when answering without specific document context."
        )
        
        has_context = bool(context_str and context_str.strip() and context_str != "No document matches found.")
        prompt_parts = [f"User Query: {query}"]
        if has_context:
            prompt_parts.append(f"\n\nRetrieved Document Context:\n{context_str}")
        else:
            prompt_parts.append("\n\nNote: No specific document matches were found. Please answer based on your general knowledge of Indian MSME government schemes.")
        prompt = "\n".join(prompt_parts)
        
        if not self.gemini_client:
            return {"response": self._fallback_answer(query, contexts), "sources": contexts}
            
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3
                )
            )
            return {"response": response.text, "sources": contexts}
        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            return {"response": self._fallback_answer(query, contexts), "sources": contexts}

    def generate_explanation(self, profile: BusinessProfile, scheme: Scheme, breakdown: Dict[str, Any]) -> str:
        """
        Generates Explainable AI reasons explaining why a business profile qualifies for a scheme.
        Falls back to rule-based explanation when Gemini API is unavailable.
        """
        eligible = all(v.get("status", True) for v in breakdown.values())
        
        def _rule_based_explanation():
            if eligible:
                passing = [k.replace('_', ' ').title() for k, v in breakdown.items() if v.get("status", True)]
                reasons = (
                    f"✅ **{scheme.name}** — You Qualify!\n\n"
                    f"Based on your profile, your business meets the eligibility criteria for this scheme. "
                    f"Your annual turnover of ₹{float(profile.annual_turnover):,.2f} and investment of "
                    f"₹{float(profile.investment_in_plant_machinery):,.2f} are within the prescribed limits. "
                    f"Your enterprise sector '{profile.sector}' and location '{profile.state}' match the scheme's target criteria.\n\n"
                    f"**Passing Parameters:** {', '.join(passing)}.\n\n"
                    f"**Estimated Max Benefit:** ₹{float(scheme.max_benefit_amount):,.2f}\n"
                    f"**Documents Needed:** {', '.join(scheme.required_documents or ['Udyam Registration'])}"
                )
                return reasons
            else:
                mismatches = [k.replace('_', ' ').title() for k, v in breakdown.items() if not v.get("status", True)]
                reasons = (
                    f"❌ **{scheme.name}** — Currently Does Not Match\n\n"
                    f"Your business does not fully meet the eligibility criteria due to the following:\n"
                    f"**Failing Parameters:** {', '.join(mismatches)}.\n\n"
                    f"**Suggestions:**\n"
                )
                for k, v in breakdown.items():
                    if not v.get("status", True):
                        if "turnover" in k:
                            reasons += f"- Reduce annual turnover to ≤ ₹{float(v.get('limit', 0)):,.2f} or look for schemes with higher limits\n"
                        elif "investment" in k:
                            reasons += f"- Adjust investment in plant & machinery to ≤ ₹{float(v.get('limit', 0)):,.2f}\n"
                        elif "sector" in k:
                            reasons += f"- Check if your sector '{v.get('current_value', 'N/A')}' is eligible; consider diversification\n"
                        elif "state" in k:
                            reasons += f"- This scheme is restricted to specific states. Look for central/national schemes applicable in your state\n"
                        elif "business_age" in k:
                            reasons += f"- Your business needs to be older. Consider reapplying after meeting the minimum age requirement\n"
                        elif "registrations" in k:
                            reasons += f"- Complete the required registrations: {', '.join(v.get('missing', []))}\n"
                        elif "owner_demographics" in k:
                            reasons += f"- Explore schemes targeting your demographic category instead\n"
                        else:
                            reasons += f"- Review and update your {k} parameter\n"
                return reasons

        if not self.gemini_client:
            return _rule_based_explanation()

        prompt = (
            f"Please write a short, professional, and personalized explanation of why the business qualifies "
            f"for the scheme '{scheme.name}' (or why they do not qualify, if not eligible).\n\n"
            f"MSME Profile:\n"
            f"- Company Name: {profile.company_name}\n"
            f"- State: {profile.state}\n"
            f"- Sector: {profile.sector}\n"
            f"- Turnover: INR {float(profile.annual_turnover):,.2f}\n"
            f"- Investment: INR {float(profile.investment_in_plant_machinery):,.2f}\n"
            f"- Owner Demographics: Social: {profile.social_category}, Gender: {profile.gender_of_owner}, Minority: {profile.is_minority_owned}\n\n"
            f"Scheme Details:\n"
            f"- Name: {scheme.name}\n"
            f"- Description: {scheme.description}\n"
            f"- Benefits: Max Benefit of INR {float(scheme.max_benefit_amount):,.2f}\n\n"
            f"Eligibility Check Logs:\n"
            f"{breakdown}\n\n"
            f"Write a concise paragraph explaining eligibility in a friendly, supportive tone. "
            f"Highlight specific benefits the MSME can claim and list required documents."
        )

        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"XAI generation error: {str(e)}")
            return _rule_based_explanation()

# Singleton instance
rag_service = RAGService()
