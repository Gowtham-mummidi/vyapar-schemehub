import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import BusinessProfile, Scheme, Recommendation
from app.services.eligibility_engine import eligibility_engine
from app.services.match_calculator import calculate_comprehensive_match
from decimal import Decimal

logger = logging.getLogger(__name__)

class RecommendationEngine:
    @staticmethod
    def calculate_match_score(
        profile: Optional[BusinessProfile],
        scheme: Scheme,
        is_eligible: bool,
        breakdown: Dict[str, Any]
    ) -> float:
        """
        Calculates a nuanced compatibility match score from 0.0 to 100.0
        based on the user's business profile and scheme parameters.
        """
        score, _, _ = calculate_comprehensive_match(profile, scheme, is_eligible, breakdown)
        return score

    @staticmethod
    def build_recommendation_reason(
        scheme: Scheme,
        score: float,
        is_eligible: bool,
        breakdown: Dict[str, Any],
        profile: Optional[BusinessProfile]
    ) -> str:
        """
        Generates a contextual, profile-aware recommendation reason string.
        """
        _, _, reason = calculate_comprehensive_match(profile, scheme, is_eligible, breakdown)
        return reason

    def generate_recommendations(self, db: Session, profile: BusinessProfile) -> List[Recommendation]:
        """
        Evaluates all active schemes against the business profile,
        updates or inserts recommendation objects, and returns them sorted by match_score.
        Uses in-memory batch processing for instant sub-second performance.
        """
        # Fetch active schemes
        schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
        if not schemes:
            return []

        # Batch-load existing recommendations for this profile (1 query instead of N queries)
        existing_recs_map = {
            rec.scheme_id: rec
            for rec in db.query(Recommendation).filter(Recommendation.user_id == profile.id).all()
        }

        recommendations = []

        for scheme in schemes:
            is_eligible, breakdown = eligibility_engine.check_eligibility(profile, scheme)
            score, aspects, reason = calculate_comprehensive_match(profile, scheme, is_eligible, breakdown)

            rec = existing_recs_map.get(scheme.id)
            if rec:
                rec.match_score = Decimal(str(score))
                rec.is_eligible = is_eligible
                rec.eligibility_reasons = breakdown
                rec.recommendation_reason = reason
            else:
                rec = Recommendation(
                    user_id=profile.id,
                    scheme_id=scheme.id,
                    match_score=Decimal(str(score)),
                    is_eligible=is_eligible,
                    eligibility_reasons=breakdown,
                    recommendation_reason=reason,
                    status="Viewed"
                )
                db.add(rec)

            recommendations.append(rec)

        db.commit()

        # Return sorted recommendations (highest match_score first)
        recommendations.sort(key=lambda x: float(x.match_score or 0.0), reverse=True)
        return recommendations


# Singleton instance
recommendation_engine = RecommendationEngine()
