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
        Calculates a nuanced compatibility match score from 0.0 to 100.0.

        Scoring principles:
        - Ineligible businesses score low (10-40%) proportional to how close they are
        - Eligible businesses on broad/general schemes score moderate (45-65%)
        - Eligible businesses with specific sector/state/demographic matches score high (70-95%)

        Factors:
        1. Hard gate: eligibility pass/fail
        2. MSME category fit (up to 20 pts)
        3. Sector specificity — exact match on a targeted scheme is high value (up to 20 pts)
        4. Geographic specificity — state-specific schemes reward location match (up to 15 pts)
        5. Owner demographics alignment (up to 15 pts)
        6. Financial fit — turnover/investment sweet spot within scheme limits (up to 15 pts)
        7. Document/registration readiness (up to 10 pts)
        8. Specificity bonus — schemes that specifically target this user profile (up to 15 pts)
        """
        rules = scheme.eligibility_rules or {}

        # --- Hard gate: ineligible → low score proportional to failures ---
        if not is_eligible:
            total_tests = len(breakdown)
            if total_tests == 0:
                return 15.0
            passed_tests = sum(1 for k, v in breakdown.items() if v.get("status", False))
            return round((passed_tests / total_tests) * 40.0, 2)

        score = 0.0
        specificity_bonus = 0.0

        # 1. MSME category match (up to 20 pts)
        msme_cats = rules.get("msme_categories") or []
        if msme_cats and breakdown.get("msme_category", {}).get("status"):
            score += 20.0
        elif not msme_cats:
            score += 8.0  # No restriction = broad scheme baseline

        # 2. Sector match (up to 20 pts)
        allowed_sectors = rules.get("allowed_sectors") or []
        if allowed_sectors and "All" not in allowed_sectors:
            if profile.sector and profile.sector in allowed_sectors:
                score += 20.0
                specificity_bonus += 10.0  # Niche sector match
            else:
                score += 2.0  # Sector rule exists but user doesn't match specifically
        else:
            score += 7.0  # Broad sector scheme baseline

        # 3. Geographic match (up to 15 pts)
        allowed_states = rules.get("allowed_states") or []
        if allowed_states and "All" not in allowed_states:
            if profile.state and profile.state in allowed_states:
                score += 15.0
                specificity_bonus += 8.0
            else:
                score += 2.0
        else:
            score += 5.0  # National scheme baseline

        # 4. Owner demographics match (up to 15 pts)
        allowed_owners = rules.get("allowed_owner_categories") or []
        if allowed_owners and "All" not in allowed_owners and "General" not in allowed_owners:
            is_demographic_target = (
                ("Female" in allowed_owners and profile.gender_of_owner == "Female") or
                (profile.social_category in allowed_owners and profile.social_category != "General") or
                ("Minority" in allowed_owners and profile.is_minority_owned)
            )
            if is_demographic_target:
                score += 15.0
                specificity_bonus += 8.0
            else:
                score += 2.0  # Not the scheme's target demographic
        else:
            score += 5.0  # Open to all demographics baseline

        # 5. Financial fit (up to 15 pts): reward being in the sweet spot
        max_turnover = rules.get("max_turnover")
        max_investment = rules.get("max_investment")
        financial_pts = 0.0
        financial_checks = 0

        if max_turnover and float(profile.annual_turnover or 0) > 0:
            ratio = float(profile.annual_turnover) / float(max_turnover)
            if 0.10 <= ratio <= 0.80:
                financial_pts += 7.5
            elif ratio < 0.10:
                financial_pts += 3.0
            else:
                financial_pts += 1.0  # near/over limit
            financial_checks += 1

        if max_investment and float(profile.investment_in_plant_machinery or 0) > 0:
            ratio = float(profile.investment_in_plant_machinery) / float(max_investment)
            if 0.10 <= ratio <= 0.80:
                financial_pts += 7.5
            elif ratio < 0.10:
                financial_pts += 3.0
            else:
                financial_pts += 1.0
            financial_checks += 1

        if financial_checks == 0:
            score += 4.0  # no financial data or no rules → small neutral credit
        else:
            score += min(financial_pts, 15.0)

        # 6. Document/registration readiness (up to 10 pts)
        req_regs = rules.get("required_registrations") or []
        user_regs = profile.registrations or {}
        if req_regs:
            matched = sum(1 for r in req_regs if user_regs.get(r.lower(), False))
            readiness = matched / len(req_regs)
            score += round(readiness * 10.0, 1)
        else:
            score += 4.0  # no registration requirements

        # 7. Specificity bonus: schemes specifically targeting this user are more valuable
        score += min(specificity_bonus, 15.0)

        # Score bands:
        # - Eligible but very generic scheme  → ~43–55%
        # - Some specific matches             → ~65–80%
        # - Tight profile+sector+state+demo   → 85–95%
        return round(min(max(score, 20.0), 95.0), 2)

    def _build_recommendation_reason(
        self,
        scheme: Scheme,
        score: float,
        is_eligible: bool,
        breakdown: Dict[str, Any],
        profile: BusinessProfile
    ) -> str:
        """Generates a contextual, profile-aware recommendation reason string."""
        prefix = f"{int(round(score))}% Match"
        if score >= 85:
            quality = "Top Match"
        elif score >= 70:
            quality = "Strong Match"
        elif score >= 55:
            quality = "Good Match"
        elif score >= 40:
            quality = "Partial Match"
        else:
            quality = "Low Match"

        rules = scheme.eligibility_rules or {}
        reason_parts = []

        if is_eligible:
            # Sector specificity
            allowed_sectors = rules.get("allowed_sectors") or []
            if allowed_sectors and "All" not in allowed_sectors and profile.sector in allowed_sectors:
                reason_parts.append(f"{profile.sector} sector scheme")

            # State specificity
            allowed_states = rules.get("allowed_states") or []
            if allowed_states and "All" not in allowed_states and profile.state in allowed_states:
                reason_parts.append(f"available in {profile.state}")

            # Demographics
            allowed_owners = rules.get("allowed_owner_categories") or []
            if "Female" in allowed_owners and profile.gender_of_owner == "Female":
                reason_parts.append("women entrepreneur benefit")
            if profile.social_category in (allowed_owners or []) and profile.social_category not in ("General", None):
                reason_parts.append(f"{profile.social_category} category incentive")
            if "Minority" in allowed_owners and profile.is_minority_owned:
                reason_parts.append("minority-owned business benefit")

            # MSME category
            msme_cat = breakdown.get("msme_category", {})
            if msme_cat.get("status") and msme_cat.get("current_value"):
                reason_parts.append(f"{msme_cat['current_value']} enterprise eligible")

            if not reason_parts:
                reason_parts = [scheme.funding_type or "MSME Scheme", "meets core criteria"]

            aspect_text = " · ".join(reason_parts[:3])
            return f"✨ {prefix} ({quality}): {aspect_text}."
        else:
            # Find which checks failed
            failed = [
                key.replace("_", " ").title()
                for key, val in (breakdown or {}).items()
                if not val.get("status", True)
            ]
            if failed:
                return f"ℹ️ {prefix} ({quality}): Review {', '.join(failed[:2])} criteria to qualify."
            return f"ℹ️ {prefix} ({quality}): Review eligibility criteria for specific parameter limits."

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
            
            # Blend with semantic similarity score if project information is present
            project_query = (profile.project_description or "").strip()
            if not project_query:
                regs = profile.registrations or {}
                projs = regs.get("projects", [])
                if projs:
                    project_query = " ".join([f"{p.get('title', '')} {p.get('description') or p.get('desc') or ''}" for p in projs]).strip()
                elif profile.project_title:
                    project_query = profile.project_title.strip()

            if project_query and is_eligible:
                try:
                    # Query similarity vector fragments for this scheme
                    hits = rag_service.search_similar_chunks(
                        query=project_query,
                        scheme_id=str(scheme.id),
                        limit=3
                    )
                    if hits:
                        # Qdrant cosine similarity scores usually range 0.0 - 1.0
                        max_similarity = max(float(hit.get("score", 0.0)) for hit in hits)
                        # Normalize a 0.4 - 0.9 similarity to a 0 - 100 score
                        semantic_score = min(max(0.0, (max_similarity - 0.3) / 0.6) * 100.0, 100.0)
                        # Blended score: 70% criteria eligibility + 30% semantic fit
                        score = 0.7 * score + 0.3 * semantic_score
                except Exception as e:
                    logger.error(f"Semantic scoring calculation failed for scheme {scheme.name}: {str(e)}")

            # Round final score
            score = round(min(max(score, 10.0), 95.0), 2)

            # Build a meaningful recommendation reason from profile + scheme analysis
            reason = self._build_recommendation_reason(scheme, score, is_eligible, breakdown, profile)

            # Check if recommendation already exists for this scheme and profile
            rec = db.query(Recommendation).filter(
                Recommendation.user_id == profile.id,
                Recommendation.scheme_id == scheme.id
            ).first()
            
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
        recommendations.sort(key=lambda x: float(x.match_score), reverse=True)
        return recommendations

# Singleton instance
recommendation_engine = RecommendationEngine()

