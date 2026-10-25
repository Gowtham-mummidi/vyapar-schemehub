import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import BusinessProfile, Scheme, Recommendation
from app.services.eligibility_engine import eligibility_engine
from app.services.rag_service import rag_service
from decimal import Decimal

logger = logging.getLogger(__name__)

class RecommendationEngine:
    @staticmethod
    def calculate_match_score(profile: BusinessProfile, scheme: Scheme, is_eligible: bool, breakdown: Dict[str, Any]) -> float:
        """
        Calculates a compatibility match score from 0.0 to 100.0.
        Factors:
        1. Eligibility status (60% weight - base eligible gets 60 points)
        2. Sector specificity (15% weight - matches highly specific sector rather than "All")
        3. Geographic specificity (10% weight - state specific matching gets extra points)
        4. Target demographics alignment (10% weight - women/SC/ST owned match)
        5. Document readiness (5% weight - user already has required documents)
        """
        if not is_eligible:
            # Check how close they are. Let's give a small score proportional to passing tests
            total_tests = len(breakdown)
            if total_tests == 0:
                return 0.0
            passed_tests = sum(1 for k, v in breakdown.items() if v.get("status", False))
            return round((passed_tests / total_tests) * 40.0, 2)

        score = 60.0  # Base score for eligibility
        
        # Sector matching
        rules = scheme.eligibility_rules or {}
        allowed_sectors = rules.get("allowed_sectors", [])
        if allowed_sectors and profile.sector in allowed_sectors and "All" not in allowed_sectors:
            score += 15.0  # Niche industry match
        else:
            score += 7.0   # General/Broad sector match

        # Geographic matching
        allowed_states = rules.get("allowed_states", [])
        if allowed_states and profile.state in allowed_states and "All" not in allowed_states:
            score += 10.0  # State-specific matching scheme
        else:
            score += 5.0   # National/Central scheme

        # Demographics preference
        allowed_owners = rules.get("allowed_owner_categories", [])
        if allowed_owners:
            is_demographic_target = (
                ("Female" in allowed_owners and profile.gender_of_owner == "Female") or
                (profile.social_category in allowed_owners and profile.social_category != "General") or
                ("Minority" in allowed_owners and profile.is_minority_owned)
            )
            if is_demographic_target:
                score += 10.0
            else:
                score += 3.0
        else:
            score += 5.0   # Neutral target

        # Document Readiness
        required_docs = scheme.required_documents or []
        user_regs = profile.registrations or {}
        if required_docs:
            matched_docs = 0
            for doc in required_docs:
                # Map standard doc strings to profile registrations fields
                doc_key = doc.lower().strip()
                if user_regs.get(doc_key, False):
                    matched_docs += 1
            readiness_ratio = matched_docs / len(required_docs)
            score += readiness_ratio * 5.0
        else:
            score += 5.0  # No documents required

        return min(round(score, 2), 100.0)

    def generate_recommendations(self, db: Session, profile: BusinessProfile) -> List[Recommendation]:
        """
        Evaluates all active schemes against the business profile,
        updates or inserts recommendation objects, and returns them sorted by match_score.
        Integrates semantic matching if a project description is specified.
        """
        # Fetch active schemes
        schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
        recommendations = []
        
        for scheme in schemes:
            is_eligible, breakdown = eligibility_engine.check_eligibility(profile, scheme)
            score = self.calculate_match_score(profile, scheme, is_eligible, breakdown)
            
            # Blend with semantic similarity score if project_description is present
            if profile.project_description and profile.project_description.strip() and is_eligible:
                try:
                    # Query similarity vector fragments for this scheme
                    hits = rag_service.search_similar_chunks(
                        query=profile.project_description,
                        scheme_id=str(scheme.id),
                        limit=3
                    )
                    if hits:
                        # Qdrant cosine similarity scores usually range 0.0 - 1.0 (sometimes slightly diff depending on model)
                        # We extract maximum score and normalize
                        max_similarity = max(float(hit.get("score", 0.0)) for hit in hits)
                        # Cosine similarity for matching concepts typically is > 0.5
                        # Normalize a 0.4 - 0.9 similarity to a 0 - 100 score
                        semantic_score = min(max(0.0, (max_similarity - 0.3) / 0.6) * 100.0, 100.0)
                        
                        # Blended score: 70% criteria eligibility + 30% semantic fit
                        score = 0.7 * score + 0.3 * semantic_score
                except Exception as e:
                    logger.error(f"Semantic scoring calculation failed for scheme {scheme.name}: {str(e)}")
            
            # Check if recommendation already exists for this scheme and profile
            rec = db.query(Recommendation).filter(
                Recommendation.user_id == profile.id,
                Recommendation.scheme_id == scheme.id
            ).first()
            
            if rec:
                rec.match_score = Decimal(str(round(score, 2)))
                rec.is_eligible = is_eligible
                rec.eligibility_reasons = breakdown
            else:
                rec = Recommendation(
                    user_id=profile.id,
                    scheme_id=scheme.id,
                    match_score=Decimal(str(round(score, 2))),
                    is_eligible=is_eligible,
                    eligibility_reasons=breakdown,
                    status="Viewed"
                )
                db.add(rec)
                
            recommendations.append(rec)
            
        db.commit()
        
        # Return sorted recommendations (highest match_score first)
        recommendations.sort(key=lambda x: float(x.match_score), reverse=True)
        return recommendations

# Singleton instance
recommendation_engine = RecommendationEngine()

