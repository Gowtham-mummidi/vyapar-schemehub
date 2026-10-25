import logging
from typing import Dict, Any, Tuple
from decimal import Decimal
from app.models import BusinessProfile, Scheme

logger = logging.getLogger(__name__)

class EligibilityEngine:
    @staticmethod
    def get_msme_category(turnover: Decimal, investment: Decimal) -> str:
        """
        Classifies the business into Micro, Small, or Medium enterprise category.
        Based on Indian Ministry of MSME criteria:
        - Micro: Investment <= 1 Crore AND Turnover <= 5 Crore
        - Small: Investment <= 10 Crore AND Turnover <= 50 Crore
        - Medium: Investment <= 50 Crore AND Turnover <= 250 Crore
        """
        # Convert inputs to float for calculation
        t = float(turnover)
        inv = float(investment)
        
        # Check Micro limits
        if inv <= 10_000_000 and t <= 50_000_000:
            return "Micro"
        # Check Small limits
        elif inv <= 100_000_000 and t <= 500_000_000:
            return "Small"
        # Check Medium limits
        elif inv <= 500_000_000 and t <= 2_500_000_000:
            return "Medium"
        else:
            return "Large"  # Exceeds MSME definitions

    def check_eligibility(self, profile: BusinessProfile, scheme: Scheme) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates the eligibility of a BusinessProfile against a Scheme.
        Returns:
            Tuple[is_eligible (bool), eligibility_breakdown (dict)]
        """
        rules = scheme.eligibility_rules or {}
        breakdown = {}
        is_eligible = True
        
        # 1. Evaluate MSME classification category
        msme_cat = self.get_msme_category(profile.annual_turnover, profile.investment_in_plant_machinery)
        breakdown["msme_category"] = {
            "current_value": msme_cat,
            "required_values": rules.get("msme_categories"),
            "status": True
        }
        if rules.get("msme_categories"):
            status = msme_cat in rules["msme_categories"]
            breakdown["msme_category"]["status"] = status
            if not status:
                is_eligible = False

        # 2. Evaluate turnover limit
        turnover_limit = rules.get("max_turnover")
        breakdown["turnover"] = {
            "current_value": float(profile.annual_turnover),
            "limit": turnover_limit,
            "status": True
        }
        if turnover_limit is not None:
            status = float(profile.annual_turnover) <= float(turnover_limit)
            breakdown["turnover"]["status"] = status
            if not status:
                is_eligible = False

        # 3. Evaluate investment limit
        investment_limit = rules.get("max_investment")
        breakdown["investment"] = {
            "current_value": float(profile.investment_in_plant_machinery),
            "limit": investment_limit,
            "status": True
        }
        if investment_limit is not None:
            status = float(profile.investment_in_plant_machinery) <= float(investment_limit)
            breakdown["investment"]["status"] = status
            if not status:
                is_eligible = False

        # 4. Evaluate Business Age
        min_age = rules.get("min_business_age")
        max_age = rules.get("max_business_age")
        breakdown["business_age"] = {
            "current_value": profile.business_age_years,
            "min_required": min_age,
            "max_required": max_age,
            "status": True
        }
        if min_age is not None:
            if profile.business_age_years < int(min_age):
                breakdown["business_age"]["status"] = False
                is_eligible = False
        if max_age is not None:
            if profile.business_age_years > int(max_age):
                breakdown["business_age"]["status"] = False
                is_eligible = False

        # 5. Evaluate Location (State Specific)
        allowed_states = rules.get("allowed_states")
        breakdown["state"] = {
            "current_value": profile.state,
            "allowed_values": allowed_states,
            "status": True
        }
        if allowed_states and len(allowed_states) > 0:
            # "Central" / empty or matching user state
            status = (profile.state in allowed_states) or ("All" in allowed_states)
            breakdown["state"]["status"] = status
            if not status:
                is_eligible = False

        # 6. Evaluate Sectors
        allowed_sectors = rules.get("allowed_sectors")
        breakdown["sector"] = {
            "current_value": profile.sector,
            "allowed_values": allowed_sectors,
            "status": True
        }
        if allowed_sectors and len(allowed_sectors) > 0:
            status = (profile.sector in allowed_sectors) or ("All" in allowed_sectors)
            breakdown["sector"]["status"] = status
            if not status:
                is_eligible = False

        # 7. Evaluate Owner Categories (Gender, Social Category, Minority)
        allowed_owners = rules.get("allowed_owner_categories")  # SC, ST, Female, Minority
        breakdown["owner_demographics"] = {
            "gender": profile.gender_of_owner,
            "social_category": profile.social_category,
            "minority": profile.is_minority_owned,
            "allowed": allowed_owners,
            "status": True
        }
        if allowed_owners and len(allowed_owners) > 0:
            # Check if any owner demographics criteria matches the preference list
            matches_gender = "Female" in allowed_owners and profile.gender_of_owner == "Female"
            matches_social = profile.social_category in allowed_owners
            matches_minority = "Minority" in allowed_owners and profile.is_minority_owned
            
            # If the rule is restrictive (only for specific sections), check match
            status = matches_gender or matches_social or matches_minority or ("General" in allowed_owners) or ("All" in allowed_owners)
            breakdown["owner_demographics"]["status"] = status
            if not status:
                is_eligible = False

        # 8. Evaluate Registrations Needed
        req_regs = rules.get("required_registrations")
        user_regs = profile.registrations or {}
        breakdown["registrations"] = {
            "current_value": user_regs,
            "required_values": req_regs,
            "status": True
        }
        if req_regs and len(req_regs) > 0:
            missing_regs = []
            for r in req_regs:
                if not user_regs.get(r.lower(), False):
                    missing_regs.append(r)
            if missing_regs:
                breakdown["registrations"]["status"] = False
                breakdown["registrations"]["missing"] = missing_regs
                is_eligible = False

        return is_eligible, breakdown

# Singleton instance
eligibility_engine = EligibilityEngine()
