import re
import math
from typing import List, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models import Scheme, BusinessProfile
from app.schemas import SchemeOut, RecommendationOut
from app.services.eligibility_engine import eligibility_engine

# Common synonyms and intent mappings
SYNONYMS = {
    "women": ["female", "women", "woman", "nari", "mahila"],
    "female": ["female", "women", "woman", "nari", "mahila"],
    "loan": ["loan", "credit", "borrow", "advance", "debt", "lending", "cgtmse", "mudra"],
    "subsidy": ["subsidy", "grant", "rebate", "concession", "financial assistance", "clcss", "pmegp"],
    "grant": ["grant", "subsidy", "support", "aid", "seed fund"],
    "manufacturing": ["manufacturing", "maker", "production", "factory", "plant", "machinery", "industry", "industrial"],
    "technology": ["technology", "tech", "software", "digital", "modernization", "upgrade", "it"],
    "export": ["export", "international", "foreign", "trade", "overseas"],
    "solar": ["solar", "renewable", "green", "energy", "clean"],
    "collateral": ["collateral", "guarantee", "security", "collateral-free", "without security"]
}

class AISearchService:
    def search_and_match(
        self,
        db: Session,
        query: str,
        profile: Optional[BusinessProfile] = None,
        funding_type: str = "All",
        limit: int = 50
    ) -> List[RecommendationOut]:
        """
        Performs AI-powered semantic and intent matching on schemes,
        calculating an exact matched percentage (0 - 100%) for each scheme.
        """
        all_schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
        if not all_schemes:
            return []

        # Filter by funding type if specified
        if funding_type and funding_type != "All":
            all_schemes = [s for s in all_schemes if s.funding_type and s.funding_type.lower() == funding_type.lower()]

        query_clean = (query or "").strip().lower()
        query_tokens = set(re.findall(r"\w+", query_clean)) if query_clean else set()

        # Expand query tokens with synonyms
        expanded_tokens = set(query_tokens)
        for token in query_tokens:
            if token in SYNONYMS:
                expanded_tokens.update(SYNONYMS[token])

        results = []
        for scheme in all_schemes:
            relevance_score, matched_aspects = self._calculate_relevance(scheme, query_clean, expanded_tokens)

            # Profile compatibility
            is_eligible = True
            eligibility_breakdown = {}
            profile_score = 75.0  # neutral default if no profile

            if profile and (profile.company_name or float(profile.annual_turnover or 0) > 0 or profile.sector):
                is_eligible, eligibility_breakdown = eligibility_engine.check_eligibility(profile, scheme)
                # Compute eligibility score
                passed_tests = sum(1 for k, v in eligibility_breakdown.items() if v.get("status", False))
                total_tests = max(1, len(eligibility_breakdown))
                base_profile_score = (passed_tests / total_tests) * 100.0
                if is_eligible:
                    profile_score = max(70.0, base_profile_score)
                else:
                    profile_score = min(50.0, base_profile_score * 0.6)

            # Combine scores
            if query_clean:
                # If query provided, 65% relevance to query + 35% profile compatibility
                final_score = (relevance_score * 0.65) + (profile_score * 0.35)
                # Boost if top relevance match
                if relevance_score >= 80:
                    final_score = max(final_score, relevance_score * 0.9)
            else:
                # If no query, use profile compatibility
                final_score = profile_score

            final_score = round(min(max(final_score, 10.0), 99.0), 1)

            # Generate dynamic AI match reason
            reason = self._generate_match_reason(scheme, final_score, matched_aspects, is_eligible, profile)

            results.append(
                RecommendationOut(
                    id=None,
                    user_id=profile.id if profile else None,
                    scheme_id=scheme.id,
                    scheme=SchemeOut.model_validate(scheme),
                    match_score=Decimal(str(final_score)),
                    match_percentage=final_score,
                    is_eligible=is_eligible,
                    eligibility_reasons=eligibility_breakdown,
                    recommendation_reason=reason,
                    status="Viewed",
                    created_at=None
                )
            )

        # Sort descending by match_score
        results.sort(key=lambda x: float(x.match_score), reverse=True)
        return results[:limit]

    def _calculate_relevance(self, scheme: Scheme, raw_query: str, tokens: set) -> tuple[float, List[str]]:
        if not raw_query or not tokens:
            return 80.0, ["General MSME Scheme"]

        score = 0.0
        matched_aspects = []

        name_lower = (scheme.name or "").lower()
        desc_lower = (scheme.description or "").lower()
        ministry_lower = (scheme.ministry or "").lower()
        funding_lower = (scheme.funding_type or "").lower()
        rules = scheme.eligibility_rules or {}

        # 1. Exact phrase match in Name or Description
        if raw_query in name_lower:
            score += 45.0
            matched_aspects.append(f"Title match '{raw_query}'")
        elif raw_query in desc_lower:
            score += 25.0
            matched_aspects.append(f"Key phrase in scheme guidelines")

        # 2. Token overlap in Scheme Name (Weight: 35)
        name_tokens = set(re.findall(r"\w+", name_lower))
        name_overlap = tokens.intersection(name_tokens)
        if name_overlap:
            token_ratio = len(name_overlap) / max(1, len(tokens))
            score += min(35.0, token_ratio * 35.0)
            matched_aspects.append(f"Matching title terms: {', '.join(list(name_overlap)[:3])}")

        # 3. Token overlap in Description (Weight: 25)
        desc_tokens = set(re.findall(r"\w+", desc_lower))
        desc_overlap = tokens.intersection(desc_tokens)
        if desc_overlap:
            desc_ratio = len(desc_overlap) / max(1, len(tokens))
            score += min(25.0, desc_ratio * 25.0)
            if not name_overlap:
                matched_aspects.append(f"Keyword match in description")

        # 4. Funding Type Match (Weight: 15)
        if funding_lower and any(t == funding_lower for t in tokens):
            score += 15.0
            matched_aspects.append(f"Funding Type: {scheme.funding_type}")

        # 5. Sector Match (Weight: 15)
        allowed_sectors = [s.lower() for s in rules.get("allowed_sectors", [])]
        for sec in allowed_sectors:
            if any(t in sec for t in tokens) or sec in raw_query:
                score += 15.0
                matched_aspects.append(f"Sector: {sec.title()}")
                break

        # 6. Demographics Target Match (Weight: 15)
        allowed_owners = [o.lower() for o in rules.get("allowed_owner_categories", [])]
        if any(t in ["women", "female"] for t in tokens) and "female" in allowed_owners:
            score += 15.0
            matched_aspects.append("Special Women Entrepreneur Benefit")
        if any(t in ["sc", "st", "dalit"] for t in tokens) and any(o in ["sc", "st"] for o in allowed_owners):
            score += 15.0
            matched_aspects.append("SC/ST Entrepreneur Incentive")

        # 7. Ministry Match
        if ministry_lower and any(t in ministry_lower for t in tokens):
            score += 10.0

        # Normalize score between 15% and 98%
        final_relevance = min(max(score, 15.0), 98.0)
        return round(final_relevance, 1), matched_aspects

    def _generate_match_reason(
        self,
        scheme: Scheme,
        score: float,
        aspects: List[str],
        is_eligible: bool,
        profile: Optional[BusinessProfile]
    ) -> str:
        prefix = f"{int(round(score))}% Match"
        if score >= 85:
            quality = "Top Match"
        elif score >= 70:
            quality = "High Match"
        elif score >= 50:
            quality = "Compatible Match"
        else:
            quality = "Moderate Match"

        aspect_text = " · ".join(aspects[:2]) if aspects else (scheme.funding_type or "MSME Scheme")
        
        if is_eligible:
            return f"✨ {prefix} ({quality}): {aspect_text}. Your business profile meets core criteria."
        else:
            return f"ℹ️ {prefix} ({quality}): {aspect_text}. Review eligibility criteria for specific parameter limits."

ai_search_service = AISearchService()
