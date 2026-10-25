import os
import sys
from dotenv import load_dotenv
from decimal import Decimal

# Add backend root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environmental variables
load_dotenv()

from app.database import SessionLocal
from app.models import Scheme

def seed_schemes():
    db = SessionLocal()
    try:
        # Check if schemes already exist
        count = db.query(Scheme).count()
        if count > 0:
            print(f"Database already contains {count} schemes. Skipping seed.")
            return

        # Try to load schemes from extracted_schemes.json first
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(root_dir, "extracted_schemes.json")
        schemes_to_add = []

        if os.path.exists(json_path):
            import json
            print(f"Loading schemes from {json_path}...")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            seen_names = set()
            for item in data:
                name = item.get("name")
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                
                max_benefit = item.get("max_benefit_amount")
                benefit_dec = Decimal(str(max_benefit)) if max_benefit is not None else Decimal("0.00")
                
                schemes_to_add.append(Scheme(
                    name=name[:255],
                    description=item.get("description", "Government scheme for MSMEs"),
                    ministry=item.get("ministry", "Ministry of MSME, Govt of India")[:255],
                    funding_type=item.get("funding_type", "Subsidy"),
                    max_benefit_amount=benefit_dec,
                    official_link=item.get("official_link"),
                    pdf_storage_path=item.get("pdf_storage_path") or item.get("_source_file"),
                    is_active=True,
                    required_documents=item.get("required_documents", ["Udyam", "PAN"]),
                    eligibility_rules=item.get("eligibility_rules", {})
                ))
            print(f"Prepared {len(schemes_to_add)} schemes from extracted_schemes.json")

        if not schemes_to_add:
            print("Seeding default MSME schemes...")
            schemes_to_add = [
                Scheme(
                    name="Credit Guarantee Fund Trust (CGTMSE)",
                    description="Collateral-free credit facility to enable flow of credit to new and existing micro and small enterprises. Provides credit guarantees for collateral-free loans up to 5 Crore.",
                    ministry="Ministry of MSME, Govt of India",
                    funding_type="Guarantee",
                    max_benefit_amount=Decimal("50000000.00"),
                    official_link="https://www.cgtmse.in/",
                    pdf_storage_path=None,
                    is_active=True,
                    required_documents=["Udyam", "PAN"],
                    eligibility_rules={
                        "max_turnover": 500000000,
                        "max_investment": 100000000,
                        "min_business_age": 0,
                        "allowed_sectors": ["All"],
                        "allowed_states": ["All"],
                        "allowed_owner_categories": ["All"],
                        "required_registrations": ["udyam", "pan"],
                        "msme_categories": ["Micro", "Small"]
                    }
                ),
                Scheme(
                    name="Prime Minister's Employment Generation Programme (PMEGP)",
                    description="Credit-linked subsidy scheme for setting up new micro-enterprises in manufacturing and services sector. Subsidies range up to 35% for SC/ST, women, and minority owners in rural areas.",
                    ministry="Ministry of MSME / KVIC",
                    funding_type="Subsidy",
                    max_benefit_amount=Decimal("5000000.00"),
                    official_link="https://www.kviconline.gov.in/pmegpeportal/pmegphome/",
                    pdf_storage_path=None,
                    is_active=True,
                    required_documents=["Aadhaar", "PAN", "Udyam"],
                    eligibility_rules={
                        "max_turnover": 10000000,
                        "max_investment": 5000000,
                        "min_business_age": 0,
                        "allowed_sectors": ["Manufacturing", "Services"],
                        "allowed_states": ["All"],
                        "allowed_owner_categories": ["SC", "ST", "Female", "OBC", "Minority"],
                        "required_registrations": ["aadhaar", "pan", "udyam"],
                        "msme_categories": ["Micro"]
                    }
                ),
                Scheme(
                    name="Credit Linked Capital Subsidy Scheme (CLCSS)",
                    description="Facilitates technology up-gradation by providing a 15% upfront capital subsidy (up to 15 Lakh) for well-established micro and small enterprises buying modern plant & machinery.",
                    ministry="Ministry of MSME, Govt of India",
                    funding_type="Subsidy",
                    max_benefit_amount=Decimal("1500000.00"),
                    official_link="https://www.kviconline.gov.in/",
                    pdf_storage_path=None,
                    is_active=True,
                    required_documents=["GST", "Udyam"],
                    eligibility_rules={
                        "max_turnover": 500000000,
                        "max_investment": 100000000,
                        "min_business_age": 1,
                        "allowed_sectors": ["Manufacturing"],
                        "allowed_states": ["All"],
                        "allowed_owner_categories": ["All"],
                        "required_registrations": ["gst", "udyam"],
                        "msme_categories": ["Micro", "Small"]
                    }
                )
            ]

        for s in schemes_to_add:
            db.add(s)
        db.commit()
        print(f"SEED SUCCESS: Successfully inserted {len(schemes_to_add)} schemes into the database!")
    except Exception as e:
        db.rollback()
        print(f"SEED FAILED: Error seeding database: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_schemes()
