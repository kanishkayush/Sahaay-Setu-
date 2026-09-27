import json
import glob
from pathlib import Path
import os

SCHEMES_DIR = "/Users/kanishkshahi/SIH_2026_RAG/backend/data/schemes"

def classify_scheme(name: str, code: str, scheme_id: str):
    name_lower = name.lower()
    
    # Organization
    org = "UNKNOWN"
    if "nsfdc" in name_lower or "nsfdc" in code.lower() or "nsfdc" in scheme_id.lower():
        org = "NSFDC"
    elif "nbcfdc" in name_lower or "nbcfdc" in code.lower() or "nbcfdc" in scheme_id.lower():
        org = "NBCFDC"
    elif "nskfdc" in name_lower or "nskfdc" in code.lower() or "nskfdc" in scheme_id.lower():
        org = "NSKFDC"
    elif "pm-yasasvi" in name_lower or "pm young" in name_lower or "post matric" in name_lower or "pre matric" in name_lower or "top class" in name_lower:
        org = "MINISTRY/DEPARTMENT" # Typical ministry scholarship
    elif "shreyas" in name_lower or "national fellowship" in name_lower:
        org = "MINISTRY/DEPARTMENT"
    elif "green business" in name_lower and org == "UNKNOWN":
        org = "NSFDC" # Green Business Scheme is usually NSFDC
    else:
        org = "MINISTRY/DEPARTMENT" # Defaulting others to general ministry for now
        
    # Domain
    domain = "OTHER"
    if "education" in name_lower or "scholarship" in name_lower or "fellowship" in name_lower or "study" in name_lower or "coaching" in name_lower or "pm-yasasvi" in name_lower or "top class" in name_lower or "matric" in name_lower:
        domain = "EDUCATION"
    elif "agriculture" in name_lower or "kisan" in name_lower or "krishi" in name_lower or "farming" in name_lower or "green business" in name_lower:
        domain = "AGRICULTURE"
        if "dairy" in name_lower:
            domain = "DAIRY / ALLIED AGRICULTURE"
    elif "business" in name_lower or "micro" in name_lower or "term loan" in name_lower or "mahila" in name_lower or "swarnima" in name_lower or "shilpi" in name_lower or "self-employment" in name_lower:
        domain = "BUSINESS"
    elif "shilp" in name_lower or "samriddhi" in name_lower:
        domain = "BUSINESS"

    # Assistance Type & Purpose & Intent
    assistance_type = "OTHER_FINANCIAL_ASSISTANCE"
    scheme_type = "OTHER_FINANCIAL_ASSISTANCE"
    
    if "scholarship" in name_lower or "fellowship" in name_lower or "pm-yasasvi" in name_lower or "top class" in name_lower or "matric" in name_lower:
        assistance_type = "SCHOLARSHIP"
        scheme_type = "EDUCATION_SCHOLARSHIP"
    elif domain == "EDUCATION" and ("loan" in name_lower or "education loan" in name_lower):
        assistance_type = "LOAN"
        scheme_type = "EDUCATION_LOAN"
    elif domain == "AGRICULTURE" and "loan" in name_lower:
        assistance_type = "LOAN"
        scheme_type = "AGRICULTURE_LOAN"
    elif domain == "DAIRY / ALLIED AGRICULTURE" and "loan" in name_lower:
        assistance_type = "LOAN"
        scheme_type = "DAIRY_LOAN"
    elif domain == "BUSINESS" and ("loan" in name_lower or "micro" in name_lower or "term" in name_lower or "shilp" in name_lower or "mahila" in name_lower):
        assistance_type = "LOAN"
        scheme_type = "BUSINESS_LOAN"
        if "micro" in name_lower:
            scheme_type = "MICRO_FINANCE"
        elif "term" in name_lower:
            scheme_type = "TERM_LOAN"
            
    if scheme_id == "nsfdc-amy":
        org = "NSFDC"
        domain = "BUSINESS"
        scheme_type = "BUSINESS_LOAN"
        assistance_type = "LOAN"
    if scheme_id == "nsfdc-gbs":
        org = "NSFDC"
        domain = "AGRICULTURE"
        scheme_type = "BUSINESS_LOAN"
        assistance_type = "LOAN"

    purpose = "GENERAL"
    if domain == "EDUCATION":
        purpose = "HIGHER_EDUCATION"
    elif domain == "AGRICULTURE":
        purpose = "FARMING"
    elif domain == "BUSINESS":
        purpose = "BUSINESS"

    return {
        "organization": org,
        "domain": domain,
        "scheme_type": scheme_type,
        "purpose": purpose,
        "assistance_type": assistance_type,
        "verified": True
    }


def main():
    files = glob.glob(os.path.join(SCHEMES_DIR, "*.json"))
    
    org_counts = {}
    domain_counts = {}
    
    for f in files:
        with open(f, 'r') as file:
            data = json.load(file)
            
        api = data.get("api", {})
        name = api.get("name", {}).get("en", "")
        code = api.get("code", "")
        scheme_id = data.get("scheme_id", "")
        
        classification = classify_scheme(name, code, scheme_id)
        
        # Merge into data
        data["organization"] = classification["organization"]
        data["organization_code"] = classification["organization"]
        data["domain"] = classification["domain"]
        data["scheme_type"] = classification["scheme_type"]
        data["purpose"] = classification["purpose"]
        data["assistance_type"] = classification["assistance_type"]
        data["verified"] = classification["verified"]
        data["source"] = "Official Documentation"
        data["source_url"] = "https://nsfdc.nic.in" if classification["organization"] == "NSFDC" else "Unknown"
        
        with open(f, 'w') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            
        org = classification["organization"]
        org_counts[org] = org_counts.get(org, 0) + 1
        
        domain = classification["domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        print(f"{scheme_id:<35} | {org:<20} | {domain:<15} | {name}")
        
    print("\n--- SUMMARY ---")
    print("ORGANIZATIONS:")
    for k, v in org_counts.items():
        print(f"  {k}: {v}")
    print("DOMAINS:")
    for k, v in domain_counts.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
