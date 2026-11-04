import re
import hashlib
from decimal import Decimal
from typing import Dict, Any, List, Tuple, Optional
from app.models import BusinessProfile, Scheme
from app.services.eligibility_engine import eligibility_engine

# High-signal domain keywords for matching broad MSME schemes to enterprise sectors
SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "manufacturing": [
        "manufactur", "production", "machinery", "plant", "factory", "industrial",
        "fabrication", "processing", "assembly", "hardware", "engineering",
        "quality", "technology upgradation", "zero defect", "zed", "lean", "automation",
        "capital goods", "cluster"
    ],
    "it": [
        "technology", "software", "digital", "it", "electronics", "telecom",
        "cyber", "ai", "hardware", "incubator", "innovation", "startup", "data",
        "information technology", "computer", "cloud", "fintech", "edtech"
    ],
    "textiles": [
        "textile", "handloom", "khadi", "weaving", "fabric", "apparel",
        "garment", "spinning", "coir", "silk", "wool", "yarn", "fashion",
        "embroidery", "dyeing", "craft"
    ],
    "agriculture": [
        "agriculture", "agri", "farming", "crop", "horticulture", "food",
        "processing", "rural", "dairy", "fisheries", "cold chain", "organic",
        "grain", "agro", "seed", "cultivation", "harvest", "soil", "irrigation"
    ],
    "food processing": [
        "food", "processing", "cold chain", "agro", "horticulture", "dairy",
        "fruit", "grain", "beverage", "meat", "poultry", "bakery", "packaging",
        "canning", "preservation"
    ],
    "chemicals": [
        "chemical", "fertilizer", "pharma", "biotech", "plastic", "rubber",
        "paint", "dye", "petrochemical", "formulation", "laboratory", "polymer"
    ],
    "logistics": [
        "logistics", "transport", "warehouse", "freight", "cargo", "supply chain",
        "vehicle", "fleet", "shipping", "distribution", "cold storage"
    ],
    "retail": [
        "retail", "trade", "commerce", "store", "market", "marketing", "vendor",
        "distribution", "wholesaler", "shop", "e-commerce", "marketplace"
    ],
    "automotive": [
        "automotive", "vehicle", "auto", "electric vehicle", "ev", "component",
        "motor", "engine", "ancillary", "battery", "mobility"
    ],
}


def calculate_comprehensive_match(
    profile: Optional[BusinessProfile],
    scheme: Scheme,
    is_eligible: bool,
    breakdown: Dict[str, Any]
) -> Tuple[float, List[str], str]:
    """
    Computes a realistic, dynamic, profile-driven compatibility score (20.0 to 97.0)
    reflecting real business profile parameters:
    1. Hard eligibility gate
    2. MSME enterprise classification fit (Micro, Small, Medium)
    3. Sector & industry alignment (with deep domain text scanning)
    4. Geographic & state fit (state-specific bonuses vs national availability)
    5. Owner demographics incentives (Women, SC/ST, Minority)
    6. Financial scale & funding proportionality (sweet spot vs turnover/investment)
    7. Project concept & business description semantic overlap
    8. Registrations readiness (Udyam, GST, PAN)
    9. Subtle deterministic tie-breaker so identical broad schemes do not cluster at 45.0%

    Returns:
        Tuple[score: float, aspects: List[str], formatted_reason: str]
    """
    rules = scheme.eligibility_rules or {}
    s_name = scheme.name or ""
    s_desc = scheme.description or ""
    s_min = scheme.ministry or ""
    s_fund = scheme.funding_type or ""
    s_ben = float(scheme.max_benefit_amount or 0.0)
    s_text = f"{s_name} {s_desc} {s_min}".lower()

    # --- 1. Hard Gate: Ineligible Handling ---
    if not is_eligible:
        failed_aspects = []
        if breakdown:
            for key, val in breakdown.items():
                if not val.get("status", True):
                    lbl = key.replace("_", " ").title()
                    failed_aspects.append(lbl)
        
        # Calculate proportional partial score for failed eligibility
        if breakdown:
            passed = sum(1 for v in breakdown.values() if v.get("status", False))
            total = max(1, len(breakdown))
            score = round(15.0 + (passed / total) * 15.0, 1)
        else:
            score = 20.0
            
        fail_msg = f"Review {', '.join(failed_aspects[:2])} criteria" if failed_aspects else "Does not satisfy eligibility criteria"
        reason = f"ℹ️ {int(round(score))}% Match (Ineligible): {fail_msg}."
        return score, failed_aspects, reason

    # --- 2. Eligible Baseline (Starting Points) ---
    score = 20.0
    aspects = []

    # Safe extraction of profile properties
    p_turnover = float(profile.annual_turnover or 0.0) if profile else 0.0
    p_investment = float(profile.investment_in_plant_machinery or 0.0) if profile else 0.0
    p_sector = (profile.sector or "").strip().lower() if profile else ""
    p_industry = (profile.industry_type or "").strip().lower() if profile else ""
    p_state = (profile.state or "").strip().lower() if profile else ""
    p_gender = (profile.gender_of_owner or "").strip().lower() if profile else ""
    p_social = (profile.social_category or "").strip().lower() if profile else ""
    p_minority = bool(profile.is_minority_owned) if profile else False
    p_cname = (profile.company_name or "").strip() if profile else ""

    # MSME Category determination
    if p_investment <= 10_000_000 and p_turnover <= 50_000_000:
        user_cat = "Micro"
    elif p_investment <= 100_000_000 and p_turnover <= 500_000_000:
        user_cat = "Small"
    elif p_investment <= 500_000_000 and p_turnover <= 2_500_000_000:
        user_cat = "Medium"
    else:
        user_cat = "Large"

    # --- 3. MSME Enterprise Category Fit (Up to 12 pts) ---
    allowed_cats = [c.lower() for c in (rules.get("msme_categories") or [])]
    if allowed_cats:
        if user_cat.lower() in allowed_cats:
            score += 12.0
            aspects.append(f"{user_cat} enterprise priority")
        else:
            score += 4.0
    else:
        # Scheme is open to all MSMEs
        if user_cat == "Micro":
            score += 9.5
        elif user_cat == "Small":
            score += 8.5
        else:
            score += 7.5
        aspects.append(f"{user_cat} enterprise eligible")

    # --- 4. Sector & Industry Domain Fit (Up to 18 pts) ---
    allowed_sec = [s.lower() for s in (rules.get("allowed_sectors") or [])]
    is_all_sec = not allowed_sec or "all" in allowed_sec

    if p_sector and not is_all_sec and any(s in p_sector for s in allowed_sec):
        score += 18.0
        aspects.append(f"Targeted {profile.sector} sector scheme")
    elif is_all_sec:
        keywords = SECTOR_KEYWORDS.get(p_sector, [])
        name_lower = s_name.lower()
        desc_lower = s_desc.lower()
        if p_sector and any(k in name_lower for k in keywords):
            score += 14.0
            aspects.append(f"{profile.sector} domain match")
        elif p_sector and any(k in desc_lower for k in keywords):
            score += 10.0
            aspects.append(f"{profile.sector} sector priority")
        elif p_industry and p_industry in desc_lower:
            score += 7.0
            aspects.append(f"{profile.industry_type} industry fit")
        elif p_sector:
            score += 4.5
            aspects.append(f"Open to {profile.sector}")
        else:
            score += 3.0
            aspects.append("Multi-sector eligible")
    else:
        score += 1.0

    # --- 5. State & Geography Alignment (Up to 15 pts) ---
    allowed_states = [st.lower() for st in (rules.get("allowed_states") or [])]
    is_all_states = not allowed_states or "all" in allowed_states

    if p_state and not is_all_states and p_state in allowed_states:
        score += 15.0
        aspects.append(f"State scheme in {profile.state}")
    elif is_all_states:
        if p_state:
            score += 8.0
            aspects.append("Nationwide eligibility")
        else:
            score += 5.0
            aspects.append("National scheme")
    else:
        score += 1.0

    # --- 6. Demographics & Affirmative Incentives (Up to 12 pts) ---
    allowed_owners = [o.lower() for o in (rules.get("allowed_owner_categories") or [])]

    if p_gender == "female" and (
        "female" in allowed_owners or any(w in s_text for w in ["women", "female", "mahila", "stree"])
    ):
        score += 12.0
        aspects.append("Women entrepreneur incentive")
    elif p_social in ["sc", "st"] and (
        p_social in allowed_owners or any(w in s_text for w in ["sc/st", "sc", "st", "tribal", "dalit"])
    ):
        score += 12.0
        aspects.append(f"{profile.social_category} category incentive")
    elif p_minority and ("minority" in allowed_owners or "minority" in s_text):
        score += 12.0
        aspects.append("Minority business benefit")
    else:
        score += 6.0

    # --- 7. Financial Scale & Funding Proportionality (Up to 10 pts) ---
    if s_ben > 0:
        if p_turnover > 0:
            ratio = s_ben / p_turnover
            if 0.05 <= ratio <= 1.5:
                score += 10.0
                aspects.append(f"Fits ₹{s_ben/100000:.1f}L funding tier")
            elif ratio < 0.05:
                score += 5.0
            else:
                score += 6.0
        else:
            if s_ben <= 1_000_000:
                score += 8.0
                aspects.append(f"Seed grant up to ₹{s_ben/100000:.1f}L")
            elif s_ben <= 10_000_000:
                score += 6.0
            else:
                score += 4.0
    else:
        if (s_fund or "").lower() in ["loan", "credit"]:
            score += 8.0
            aspects.append("Credit guarantee support")
        else:
            score += 5.0

    # --- 8. Project Concept & Business Thematic Fit (Up to 14 pts) ---
    # Harvest project texts from profile
    p_title = profile.project_title if profile else ""
    p_desc = profile.project_description if profile else ""
    full_proj = f"{p_title or ''} {p_desc or ''}"

    # Also include projects list from registrations
    if profile:
        regs = profile.registrations or {}
        projs = regs.get("projects", [])
        if isinstance(projs, list):
            for pr in projs:
                if isinstance(pr, dict):
                    full_proj += f" {pr.get('title', '')} {pr.get('description') or pr.get('desc') or ''}"

    full_proj = full_proj.strip().lower()

    if full_proj:
        tokens = [
            w for w in re.findall(r"\w{4,}", full_proj)
            if w not in ["with", "this", "that", "have", "from", "also", "will", "your", "project", "business"]
        ]
        matches = [t for t in tokens if t in s_text]
        if len(matches) >= 3:
            score += 14.0
            aspects.append(f"Project match: {matches[0].title()}")
        elif len(matches) >= 1:
            score += 8.0
            aspects.append(f"Project keyword: {matches[0].title()}")
        else:
            score += 2.0
    elif p_cname and p_cname != "My Business":
        score += 3.0
    else:
        score += 2.0

    # --- 9. Registration Readiness (Up to 4 pts) ---
    if profile:
        regs = profile.registrations or {}
        if regs.get("udyam"):
            score += 4.0
        elif regs.get("gst") or regs.get("pan"):
            score += 2.0
        else:
            score += 1.0
    else:
        score += 1.0

    # --- 10. Deterministic Entropy Tie-Breaker ---
    # Avoids identical score clustering (e.g. 45.0% flat) by applying a tiny scheme-specific pseudo-hash jitter
    scheme_key = str(scheme.id or scheme.name or "scheme")
    h = int(hashlib.md5(scheme_key.encode("utf-8")).hexdigest()[:6], 16)
    jitter = ((h % 31) - 15) * 0.1  # Range: -1.5 to +1.5

    final_score = round(min(max(score + jitter, 25.0), 96.0), 1)

    # --- 11. Formatted Reason & Quality Bracket ---
    if final_score >= 85:
        quality = "Top Match"
    elif final_score >= 70:
        quality = "Strong Match"
    elif final_score >= 55:
        quality = "Good Match"
    elif final_score >= 40:
        quality = "Partial Match"
    else:
        quality = "Low Match"

    if not aspects:
        aspects = [s_fund or "MSME Scheme", "meets core criteria"]

    aspect_str = " · ".join(aspects[:3])
    reason = f"✨ {int(round(final_score))}% Match ({quality}): {aspect_str}."

    return final_score, aspects, reason

