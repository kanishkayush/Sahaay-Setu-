import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# --- Models ---
class UserProfile(BaseModel):
    language: str = "en"
    intent: Optional[str] = None
    purpose: Optional[str] = None
    category: Optional[str] = None
    requested_loan_amount_inr: Optional[float] = Field(default=None, ge=0)
    project_cost_inr: Optional[float] = Field(default=None, ge=0)
    course_cost_inr: Optional[float] = Field(default=None, ge=0)
    family_income_inr: Optional[float] = Field(default=None, ge=0)
    education_status: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    beneficiary_category_verified: Optional[bool] = None

class EvaluationCheck(BaseModel):
    check: str
    status: str
    user_value: Any = None
    scheme_limit: Any = None
    reason_code: str

class SchemeEvaluationResult(BaseModel):
    scheme_id: str
    scheme_name: str
    eligibility_status: str
    checks: List[EvaluationCheck] = []
    financial_assessment: Dict[str, Any] = {}
    reason_codes: List[str] = []
    missing_information: List[str] = []
    manual_verification_required: bool = False

class EngineSummary(BaseModel):
    eligible_count: int = 0
    potentially_eligible_count: int = 0
    manual_verification_count: int = 0
    not_eligible_count: int = 0

class EvaluateAllResponse(BaseModel):
    user_profile_summary: Dict[str, Any]
    evaluated_schemes: List[SchemeEvaluationResult]
    summary: EngineSummary

# --- Engine Logic ---
PURPOSE_ALIASES = {
    "dairy_business": "dairy",
    "milk_business": "dairy",
    "small_shop": "small_retail",
    "shop": "small_retail",
    "college": "education",
    "btech": "engineering_education",
    "mtech": "engineering_education"
}

def load_scheme(scheme_id: str) -> dict:
    base_dir = Path(__file__).parent.parent
    scheme_path = base_dir / "data" / "schemes" / f"{scheme_id}.json"
    if not scheme_path.exists():
        name_only = scheme_id.replace("NSFDC_", "")
        scheme_path = base_dir / "data" / "schemes" / f"{name_only}.json"
        if not scheme_path.exists():
            raise FileNotFoundError(f"Configuration for scheme {scheme_id} not found at {scheme_path}")
    with open(scheme_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _update_status(current_status: str, check_status: str) -> str:
    # Precedence: not_eligible > manual_verification_required > potentially_eligible > eligible
    precedence = {
        "eligible": 1,
        "potentially_eligible": 2,
        "manual_verification_required": 3,
        "not_eligible": 4
    }
    
    current_weight = precedence.get(current_status, 1)
    check_weight = precedence.get(check_status, 1)
    
    if check_weight > current_weight:
        return check_status
    return current_status

def check_beneficiary_category(user_profile: UserProfile, scheme: dict, result: SchemeEvaluationResult):
    if user_profile.beneficiary_category_verified is None:
        result.checks.append(EvaluationCheck(
            check="beneficiary_category",
            status="potentially_eligible",
            reason_code="BENEFICIARY_CATEGORY_UNVERIFIED"
        ))
        result.missing_information.append("beneficiary_category_verified")
        return "potentially_eligible"
    
    if user_profile.beneficiary_category_verified:
        result.checks.append(EvaluationCheck(
            check="beneficiary_category",
            status="eligible",
            user_value=True,
            scheme_limit=True,
            reason_code="BENEFICIARY_CATEGORY_VERIFIED"
        ))
        return "eligible"
    else:
        result.checks.append(EvaluationCheck(
            check="beneficiary_category",
            status="not_eligible",
            user_value=False,
            scheme_limit=True,
            reason_code="BENEFICIARY_CATEGORY_MISMATCH"
        ))
        return "not_eligible"

def check_income_eligibility(user_profile: UserProfile, scheme: dict, result: SchemeEvaluationResult):
    income_param = scheme.get("parameters", {}).get("maximum_family_income_inr", {})
    limit = income_param.get("current_value")
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    if limit is None:
        limit = api.get("maxAnnualFamilyIncome")
    
    if limit is None:
        return "eligible"
        
    user_income = user_profile.family_income_inr
    if user_income is None:
        result.checks.append(EvaluationCheck(
            check="family_income",
            status="potentially_eligible",
            scheme_limit=limit,
            reason_code="INCOME_INFORMATION_MISSING"
        ))
        result.missing_information.append("family_income_inr")
        return "potentially_eligible"
        
    if user_income <= limit:
        result.checks.append(EvaluationCheck(
            check="family_income",
            status="eligible",
            user_value=user_income,
            scheme_limit=limit,
            reason_code="INCOME_WITHIN_LIMIT"
        ))
        return "eligible"
    else:
        result.checks.append(EvaluationCheck(
            check="family_income",
            status="not_eligible",
            user_value=user_income,
            scheme_limit=limit,
            reason_code="INCOME_EXCEEDS_LIMIT"
        ))
        return "not_eligible"

def check_purpose_match(user_profile: UserProfile, scheme: dict, result: SchemeEvaluationResult):
    eligible_purposes = scheme.get("parameters", {}).get("eligible_purposes", [])
    if not eligible_purposes:
        eligible_purposes = [
            str(value).lower()
            for value in (
                list(scheme.get("supported_purposes") or [])
                + list(scheme.get("supported_domains") or [])
            )
        ]
    if not eligible_purposes:
        return "eligible"
        
    user_purpose = user_profile.purpose
    if user_purpose is None:
        result.checks.append(EvaluationCheck(
            check="purpose",
            status="potentially_eligible",
            reason_code="PURPOSE_INFORMATION_MISSING"
        ))
        result.missing_information.append("purpose")
        return "potentially_eligible"
        
    normalized_purpose = PURPOSE_ALIASES.get(user_purpose.lower(), user_purpose.lower())
    
    if normalized_purpose in eligible_purposes:
        result.checks.append(EvaluationCheck(
            check="purpose",
            status="eligible",
            user_value=normalized_purpose,
            reason_code="PURPOSE_MATCH"
        ))
        return "eligible"
        
    # Check bounds
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    scheme_category = str(
        scheme.get("domain") or api.get("officialCategory") or scheme.get("category") or ""
    )
    is_edu_purpose = "education" in normalized_purpose or "tech" in normalized_purpose or "college" in normalized_purpose
    is_edu_scheme = "education" in scheme_category.lower()
    
    if is_edu_purpose and not is_edu_scheme:
        result.checks.append(EvaluationCheck(
            check="purpose",
            status="not_eligible",
            user_value=normalized_purpose,
            reason_code="PURPOSE_NOT_SUPPORTED"
        ))
        return "not_eligible"
    elif not is_edu_purpose and is_edu_scheme:
        result.checks.append(EvaluationCheck(
            check="purpose",
            status="not_eligible",
            user_value=normalized_purpose,
            reason_code="PURPOSE_NOT_SUPPORTED"
        ))
        return "not_eligible"
        
    result.checks.append(EvaluationCheck(
        check="purpose",
        status="potentially_eligible",
        user_value=normalized_purpose,
        reason_code="PURPOSE_AMBIGUOUS"
    ))
    return "potentially_eligible"

def check_cost_limits(user_profile: UserProfile, scheme: dict, result: SchemeEvaluationResult):
    params = scheme.get("parameters", {})
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    
    if "cost_limits" in params:
        cost_limits = params["cost_limits"]
        if cost_limits.get("cost_type") == "course_cost":
            user_cost = user_profile.course_cost_inr
            min_limit = cost_limits.get("minimum_inr")
            max_limit = cost_limits.get("maximum_inr")
            
            if user_cost is None:
                result.checks.append(EvaluationCheck(
                    check="course_cost",
                    status="potentially_eligible",
                    reason_code="COURSE_COST_INFORMATION_MISSING"
                ))
                result.missing_information.append("course_cost_inr")
                return "potentially_eligible"
                
            if min_limit is None and max_limit is None:
                result.checks.append(EvaluationCheck(
                    check="course_cost",
                    status="eligible",
                    user_value=user_cost,
                    reason_code="COURSE_COST_WITHIN_LIMIT"
                ))
                return "eligible"
                
            if max_limit and user_cost > max_limit:
                result.checks.append(EvaluationCheck(
                    check="course_cost",
                    status="not_eligible",
                    user_value=user_cost,
                    scheme_limit=max_limit,
                    reason_code="COURSE_COST_EXCEEDS_LIMIT"
                ))
                return "not_eligible"
                
            if min_limit and user_cost < min_limit:
                result.checks.append(EvaluationCheck(
                    check="course_cost",
                    status="not_eligible",
                    user_value=user_cost,
                    scheme_limit=min_limit,
                    reason_code="COURSE_COST_BELOW_MINIMUM"
                ))
                return "not_eligible"
                
            result.checks.append(EvaluationCheck(
                check="course_cost",
                status="eligible",
                user_value=user_cost,
                reason_code="COURSE_COST_WITHIN_LIMIT"
            ))
            return "eligible"
            
    min_cost = params.get("minimum_project_cost_inr")
    max_cost = params.get("maximum_project_cost_inr")
    if min_cost is None or max_cost is None:
        for rule in api.get("eligibilityRules") or []:
            if not isinstance(rule, dict) or str(rule.get("field")) != "projectCost":
                continue
            value = rule.get("value")
            if rule.get("operator") == "between" and isinstance(value, list) and len(value) == 2:
                min_cost = value[0] if min_cost is None else min_cost
                max_cost = value[1] if max_cost is None else max_cost
            elif rule.get("operator") == "lte" and max_cost is None:
                max_cost = value
    if str(scheme.get("domain") or "").upper() == "EDUCATION":
        user_cost = user_profile.course_cost_inr
        if max_cost is None:
            max_cost = api.get("maxLoanAmount")
    else:
        user_cost = user_profile.project_cost_inr
    
    if user_cost is None:
        result.checks.append(EvaluationCheck(
            check="project_cost",
            status="potentially_eligible",
            reason_code="PROJECT_COST_INFORMATION_MISSING"
        ))
        result.missing_information.append("project_cost_inr")
        return "potentially_eligible"
        
    if min_cost is None and max_cost is None:
        result.checks.append(EvaluationCheck(
            check="project_cost",
            status="eligible",
            user_value=user_cost,
            reason_code="PROJECT_COST_WITHIN_LIMIT"
        ))
        return "eligible"
        
    if max_cost and user_cost > max_cost:
        result.checks.append(EvaluationCheck(
            check="project_cost",
            status="not_eligible",
            user_value=user_cost,
            scheme_limit=max_cost,
            reason_code="PROJECT_COST_EXCEEDS_LIMIT"
        ))
        return "not_eligible"
        
    if min_cost and user_cost < min_cost:
        result.checks.append(EvaluationCheck(
            check="project_cost",
            status="not_eligible",
            user_value=user_cost,
            scheme_limit=min_cost,
            reason_code="PROJECT_COST_BELOW_MINIMUM"
        ))
        return "not_eligible"
        
    result.checks.append(EvaluationCheck(
        check="project_cost",
        status="eligible",
        user_value=user_cost,
        reason_code="PROJECT_COST_WITHIN_LIMIT"
    ))
    return "eligible"

def check_financing_and_loan_limits(user_profile: UserProfile, scheme: dict, result: SchemeEvaluationResult):
    params = scheme.get("parameters", {})
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    req_loan = user_profile.requested_loan_amount_inr
    
    max_loan_param = params.get("maximum_loan_amount_inr", {})
    max_fin_param = params.get("maximum_financing_percentage", {})
    
    max_loan_val = None
    if isinstance(max_loan_param, dict):
        max_loan_val = max_loan_param.get("current_value")
    elif isinstance(max_loan_param, (int, float)):
        max_loan_val = max_loan_param
    if max_loan_val is None:
        max_loan_val = api.get("maxLoanAmount")
        
    max_fin_val = None
    if isinstance(max_fin_param, dict):
        max_fin_val = max_fin_param.get("current_value")
    elif isinstance(max_fin_param, (int, float)):
        max_fin_val = max_fin_param
    if max_fin_val is None and api.get("fundingSharePct") is not None:
        max_fin_val = float(api["fundingSharePct"]) * 100.0

    needs_manual_verification = False
    verification_parameters = []
    
    if isinstance(max_loan_param, dict) and max_loan_param.get("status") == "verification_required":
        needs_manual_verification = True
        verification_parameters.append("maximum_loan_amount_inr")
        if "derived_values" in max_loan_param:
            result.financial_assessment["financing_scenarios"] = max_loan_param.get("derived_values", {})
            
    if isinstance(max_fin_param, dict) and max_fin_param.get("status") == "verification_required":
        needs_manual_verification = True
        verification_parameters.append("maximum_financing_percentage")
        
    if verification_parameters:
        result.financial_assessment["verification_required_parameters"] = verification_parameters
    
    if req_loan is None:
        result.checks.append(EvaluationCheck(
            check="requested_loan",
            status="potentially_eligible",
            reason_code="REQUESTED_AMOUNT_MISSING"
        ))
        result.missing_information.append("requested_loan_amount_inr")
        if needs_manual_verification:
            return "manual_verification_required"
        return "potentially_eligible"

    is_edu = str(scheme.get("domain") or "").upper() == "EDUCATION"
    cost = user_profile.course_cost_inr if is_edu else user_profile.project_cost_inr
    
    max_possible_fin = None
    cost_based_fin = None
    
    if max_fin_val is not None and cost is not None:
        cost_based_fin = cost * (max_fin_val / 100.0)
        
    limits_to_check = [req_loan]
    if max_loan_val is not None:
        limits_to_check.append(max_loan_val)
    if cost_based_fin is not None:
        limits_to_check.append(cost_based_fin)
        
    if limits_to_check:
        max_possible_fin = min(limits_to_check)
        
    result.financial_assessment["requested_loan_amount_inr"] = req_loan
    if max_loan_val is not None:
        result.financial_assessment["maximum_scheme_loan_amount_inr"] = max_loan_val
    if cost_based_fin is not None:
        result.financial_assessment["cost_based_financing_limit_inr"] = cost_based_fin
    if max_possible_fin is not None:
        result.financial_assessment["maximum_possible_financing_inr"] = max_possible_fin

    status = "eligible"
    
    if max_loan_val is not None and req_loan > max_loan_val:
        result.checks.append(EvaluationCheck(
            check="requested_loan",
            status="manual_verification_required",
            user_value=req_loan,
            scheme_limit=max_loan_val,
            reason_code="REQUESTED_AMOUNT_EXCEEDS_SCHEME_LIMIT"
        ))
        status = "manual_verification_required"
    elif max_possible_fin is not None and req_loan > max_possible_fin:
        result.checks.append(EvaluationCheck(
            check="requested_loan",
            status="manual_verification_required",
            user_value=req_loan,
            scheme_limit=max_possible_fin,
            reason_code="REQUESTED_AMOUNT_EXCEEDS_DETERMINISTIC_FINANCING_LIMIT"
        ))
        status = "manual_verification_required"
    else:
        result.checks.append(EvaluationCheck(
            check="requested_loan",
            status="eligible",
            user_value=req_loan,
            reason_code="REQUESTED_AMOUNT_WITHIN_LIMIT"
        ))
        
    if needs_manual_verification:
        result.checks.append(EvaluationCheck(
            check="scheme_parameter_verification",
            status="manual_verification_required",
            reason_code="SCHEME_PARAMETER_VERIFICATION_REQUIRED"
        ))
        status = "manual_verification_required"
        
    return status

def check_education_status(user_profile: UserProfile, scheme: dict, result: SchemeEvaluationResult):
    is_edu = str(scheme.get("domain") or "").upper() == "EDUCATION"
    if not is_edu:
        return "eligible"
        
    if user_profile.education_status is None:
        result.checks.append(EvaluationCheck(
            check="education_status",
            status="potentially_eligible",
            reason_code="EDUCATION_STATUS_MISSING"
        ))
        result.missing_information.append("education_status")
        return "potentially_eligible"
        
    if user_profile.education_status == "admission_secured":
        result.checks.append(EvaluationCheck(
            check="education_status",
            status="eligible",
            user_value=user_profile.education_status,
            reason_code="EDUCATION_STATUS_VERIFIED"
        ))
        return "eligible"
        
    result.checks.append(EvaluationCheck(
        check="education_status",
        status="manual_verification_required",
        user_value=user_profile.education_status,
        reason_code="EDUCATION_REQUIREMENT_PENDING_VERIFICATION"
    ))
    return "manual_verification_required"


def _get_scheme_name(scheme: dict) -> str:
    """Extract scheme name from either flat or nested api.name structure.
    Handles both plain strings and multilingual dicts like {"en": "...", "hi": "..."}.
    """
    def _extract_name(name_val):
        if isinstance(name_val, str):
            return name_val
        if isinstance(name_val, dict):
            # Prefer English, then any available language
            for lang in ("en", "hi", "mr", "bn", "ta", "te"):
                if lang in name_val:
                    return name_val[lang]
            values = list(name_val.values())
            if values:
                return str(values[0])
        return None

    # Try top-level name first
    top_name = _extract_name(scheme.get("name"))
    if top_name:
        return top_name
    # Try api.name
    api = scheme.get("api", {})
    if isinstance(api, dict):
        api_name = _extract_name(api.get("name"))
        if api_name:
            return api_name
    return scheme.get("scheme_id", "Unknown Scheme")


def evaluate_scheme(scheme: dict, user_profile: UserProfile) -> SchemeEvaluationResult:
    result = SchemeEvaluationResult(
        scheme_id=scheme["scheme_id"],
        scheme_name=_get_scheme_name(scheme),
        eligibility_status="eligible"
    )
    
    checks = [
        check_beneficiary_category,
        check_income_eligibility,
        check_purpose_match,
        check_cost_limits,
        check_financing_and_loan_limits,
        check_education_status
    ]
    
    overall_status = "eligible"
    
    for check_func in checks:
        status = check_func(user_profile, scheme, result)
        overall_status = _update_status(overall_status, status)
            
    result.eligibility_status = overall_status
    if overall_status == "manual_verification_required":
        result.manual_verification_required = True
        
    result.reason_codes = [check.reason_code for check in result.checks]
    return result

def evaluate_all_schemes(
    user_profile_dict: dict,
    organization: str | None = None,
) -> EvaluateAllResponse:
    """Evaluate catalogue schemes. If organization is set, only that org is included."""
    profile = UserProfile(**user_profile_dict)
    
    base_dir = Path(__file__).parent.parent
    schemes_dir = base_dir / "data" / "schemes"
    schemes_to_eval = [p.stem for p in schemes_dir.glob("*.json")]
    
    evaluated = []
    
    for sid in schemes_to_eval:
        try:
            scheme_data = load_scheme(sid)
            if organization is not None and scheme_data.get("organization") != organization:
                continue
            res = evaluate_scheme(scheme_data, profile)
            evaluated.append(res)
        except Exception as e:
            # Skip invalid/unparseable schemes
            print(f"Error evaluating scheme {sid}: {e}")
            continue
            
    summary = EngineSummary()
    for res in evaluated:
        if res.eligibility_status == "eligible":
            summary.eligible_count += 1
        elif res.eligibility_status == "potentially_eligible":
            summary.potentially_eligible_count += 1
        elif res.eligibility_status == "manual_verification_required":
            summary.manual_verification_count += 1
        elif res.eligibility_status == "not_eligible":
            summary.not_eligible_count += 1
            
    return EvaluateAllResponse(
        user_profile_summary={
            "purpose": profile.purpose,
            "requested_loan_amount_inr": profile.requested_loan_amount_inr,
            "project_cost_inr": profile.project_cost_inr,
            "course_cost_inr": profile.course_cost_inr,
            "family_income_inr": profile.family_income_inr
        },
        evaluated_schemes=evaluated,
        summary=summary
    )
