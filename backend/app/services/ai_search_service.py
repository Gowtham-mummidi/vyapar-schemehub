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
        calculating a meaningful match percentage (0-100%) for each scheme
        based on how specifically the user's business profile satisfies the
        scheme's eligibility rules and targeting criteria.
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
            # Default: no profile data -> low neutral baseline
            profile_score = 40.0

            if profile and (
                profile.company_name or
                float(profile.annual_turnover or 0) > 0 or
                profile.sector or
                profile.state or
                profile.project_title or
                (profile.registrations or {}).get("projects")
            ):
                is_eligible, eligibility_breakdown = eligibility_engine.check_eligibility(profile, scheme)
                profile_score = self._calculate_profile_score(profile, scheme, is_eligible, eligibility_breakdown)

            # Combine scores
            if query_clean:
                # If query provided: 65% relevance to query + 35% profile compatibility
                final_score = (relevance_score * 0.65) + (profile_score * 0.35)
                # Boost if top relevance match
                if relevance_score >= 80:
                    final_score = max(final_score, relevance_score * 0.9)
            else:
                # No query: use profile compatibility score only
                final_score = profile_score

            final_score = round(min(max(final_score, 10.0), 98.0), 1)

            # Generate dynamic AI match reason based on profile analysis
            reason = self._generate_match_reason(
                scheme, final_score, matched_aspects, is_eligible, profile, eligibility_breakdown
            )

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

    def _calculate_profile_score(
        self,
        profile: BusinessProfile,
        scheme: Scheme,
        is_eligible: bool,
        breakdown: Dict[str, Any]
    ) -> float:
        """
        Computes a nuanced profile compatibility score (0-100) that reflects:
        1. Hard eligibility gate  — if ineligible, score is capped low
        2. Specificity bonus      — schemes targeting user's exact sector/state/demographics score higher
        3. Financial fit          — how well turnover/investment fit the scheme's sweet spot
        4. Document readiness     — registrations the user already holds
        5. Broad/general schemes  — these get a moderate baseline, NOT an inflated 99%

        Score bands:
          - Ineligible:                      10–40%
          - Eligible, broad scheme:          45–65%
          - Eligible, some specific matches: 65–80%
          - Eligible, tight profile match:   80–95%
        """
        rules = scheme.eligibility_rules or {}

        # --- Hard gate: ineligible → low score proportional to failures ---
        if not is_eligible:
            if not breakdown:
                return 15.0
            passed = sum(1 for v in breakdown.values() if v.get("status", False))
            total = max(1, len(breakdown))
            return round(min((passed / total) * 40.0, 40.0), 1)

        score = 0.0
        specificity_bonus = 0.0  # tracks how specifically this scheme targets this user

        # 1. MSME category match (up to 20 pts)
        msme_cats = rules.get("msme_categories") or []
        if msme_cats and breakdown.get("msme_category", {}).get("status"):
            score += 20.0
        elif not msme_cats:
            # No restriction means the scheme is broad — moderate credit only
            score += 8.0

        # 2. Sector match (up to 20 pts)
        allowed_sectors = rules.get("allowed_sectors") or []
        if allowed_sectors and "All" not in allowed_sectors:
            if profile.sector and profile.sector in allowed_sectors:
                score += 20.0
                specificity_bonus += 10.0  # Niche sector match — high value signal
            else:
                # Sector rule exists but user doesn't match (still eligible via other pass)
                score += 2.0
        else:
            # No sector restriction = broad scheme baseline
            score += 7.0

        # 3. State/location match (up to 15 pts)
        allowed_states = rules.get("allowed_states") or []
        if allowed_states and "All" not in allowed_states:
            if profile.state and profile.state in allowed_states:
                score += 15.0
                specificity_bonus += 8.0
            else:
                score += 2.0
        else:
            # National scheme — moderate credit
            score += 5.0

        # 4. Owner demographics match (up to 15 pts)
        allowed_owners = rules.get("allowed_owner_categories") or []
        if allowed_owners and "All" not in allowed_owners and "General" not in allowed_owners:
            is_demographic_match = (
                ("Female" in allowed_owners and profile.gender_of_owner == "Female") or
                (profile.social_category in allowed_owners and profile.social_category != "General") or
                ("Minority" in allowed_owners and profile.is_minority_owned)
            )
            if is_demographic_match:
                score += 15.0
                specificity_bonus += 8.0
            else:
                # Scheme is for specific demographics; user doesn't match
                score += 2.0
        else:
            # Open to all — moderate credit
            score += 5.0

        # 5. Financial fit (up to 15 pts): reward being in the scheme's "sweet spot"
        max_turnover = rules.get("max_turnover")
        max_investment = rules.get("max_investment")
        financial_pts = 0.0
        financial_checks = 0

        if max_turnover and float(profile.annual_turnover or 0) > 0:
            ratio = float(profile.annual_turnover) / float(max_turnover)
            # Sweet spot 10%-80% of limit → strong fit
            if 0.10 <= ratio <= 0.80:
                financial_pts += 7.5
            elif ratio < 0.10:
                financial_pts += 3.0  # very small business relative to scheme
            else:
                financial_pts += 1.0  # near/over limit — eligible but not ideal
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

        # 6. Document / registration readiness (up to 10 pts)
        req_regs = rules.get("required_registrations") or []
        user_regs = profile.registrations or {}
        if req_regs:
            matched = sum(1 for r in req_regs if user_regs.get(r.lower(), False))
            readiness = matched / len(req_regs)
            score += round(readiness * 10.0, 1)
        else:
            score += 4.0  # no registration requirements

        # 7. Specificity bonus: schemes that specifically target this user are more valuable
        score += min(specificity_bonus, 15.0)

        # Cap and normalize:
        # - Eligible but very generic scheme → ~44–55%
        # - Some specific matches          → ~65–80%
        # - Tight profile+sector+state+demo match → 85–95%
        return round(min(max(score, 20.0), 95.0), 1)

    def _calculate_relevance(self, scheme: Scheme, raw_query: str, tokens: set) -> tuple[float, List[str]]:
        if not raw_query or not tokens:
            # No search query — return a low neutral score (profile scoring takes over)
            return 50.0, []

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
        profile: Optional[BusinessProfile],
        breakdown: Dict[str, Any] = None
    ) -> str:
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

        # Build a contextual reason from breakdown and profile
        reason_parts = list(aspects[:2]) if aspects else []
        rules = scheme.eligibility_rules or {}

        if breakdown and profile:
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
            reason_parts = [scheme.funding_type or "MSME Scheme"]

        aspect_text = " · ".join(reason_parts[:3])

        if is_eligible:
            return f"✨ {prefix} ({quality}): {aspect_text}."
        else:
            # Indicate which checks failed
            failed = []
            if breakdown:
                for key, val in (breakdown or {}).items():
                    if not val.get("status", True):
                        failed.append(key.replace("_", " ").title())
            if failed:
                return f"ℹ️ {prefix} ({quality}): Review {', '.join(failed[:2])} criteria to qualify."
            return f"ℹ️ {prefix} ({quality}): {aspect_text}. Review eligibility criteria for specific parameter limits."

ai_search_service = AISearchService()
