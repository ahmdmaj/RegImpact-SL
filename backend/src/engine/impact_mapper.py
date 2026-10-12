"""Component [H]: The Impact and Action Mapper for RegImpact-SL.

Deterministically maps applicable regulatory obligations to:
- Affected business activities
- Affected documents and records
- Operational action items / compliance checklists
- Timeline notes
"""

from typing import Any, Dict, List, Optional, Union
from backend.src.models.domain import (
    BusinessImpact,
    EvaluationResult,
    OutcomeStatus,
    Rule,
)

# Supported bounded obligation types per Section 8.3 [H]
SUPPORTED_OBLIGATION_TYPES = [
    "labelling",
    "registration",
    "licensing",
    "documentation",
    "reporting",
    "process",
]

# Bounded mapping vocabulary defining activities, documents, and action templates
OBLIGATION_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "labelling": {
        "affected_activities": [
            "Product packaging design and retail artwork finalisation",
            "Packaging line printing, batch coding, and label application",
            "Finished product quality inspection and regulatory compliance verification",
        ],
        "affected_documents": [
            "Retail product packaging artwork and label specifications",
            "Nutritional information panels and ingredient declaration sheets",
            "Batch coding, manufacturing date, and expiry date records",
            "Trilingual label translation records (Sinhala, Tamil, English)",
        ],
        "action_templates": [
            "Update product packaging artwork to incorporate mandatory declarations required under {instrument} ({clause}).",
            "Ensure packaging displays required trilingual text (Sinhala, Tamil, English) adhering to prescribed font dimensions.",
            "Verify batch coding, net content, manufacturer name, and expiry date format on production line.",
            "Conduct pre-market label compliance audit against Food Control Administration Unit (FCAU) guidelines.",
            "Audit current label stock inventory and plan transition to compliant packaging before deadline.",
        ],
    },
    "registration": {
        "affected_activities": [
            "Industrial registration and formal business establishment operations",
            "Production capacity declaration and factory layout documentation",
            "Liaison with municipal and regional industrial registration bodies",
        ],
        "affected_documents": [
            "Ministry of Industry / Regional Industry Department registration certificate",
            "Business Registration (BR) certificate from Divisional Secretariat / Registrar of Companies",
            "Premises lease agreement or property title deed",
            "Factory machinery inventory and installed production capacity schedule",
        ],
        "action_templates": [
            "Prepare and submit industrial manufacturing registration application to {authority} under {instrument}.",
            "Compile certified copies of Business Registration (BR), premises layout, and equipment list.",
            "Display current manufacturing registration certificate on the factory premises.",
            "Notify {authority} in writing regarding any changes to manufacturing capacity, premises, or operations.",
        ],
    },
    "licensing": {
        "affected_activities": [
            "Manufacturing premises operations and environmental pollution controls",
            "Waste disposal, effluent treatment, and emission management",
            "Local authority trade licensing inspections and public health clearances",
        ],
        "affected_documents": [
            "Central Environmental Authority (CEA) Environmental Protection Licence (EPL)",
            "Local Authority (Pradeshiya Sabha / Municipal Council) trade licence",
            "Public Health Inspector (PHI) food establishment inspection report",
            "Waste management and effluent discharge lab test reports",
        ],
        "action_templates": [
            "Submit application for licence renewal or issuance to {authority} under {clause}.",
            "Schedule and facilitate on-site inspection by statutory officers ({authority} / PHI).",
            "Implement prescribed environmental or sanitary pollution mitigation measures at facility.",
            "Maintain valid operating licence and adhere to all schedule conditions stipulated by {authority}.",
        ],
    },
    "documentation": {
        "affected_activities": [
            "Raw ingredient procurement, receipt verification, and supplier qualification",
            "Standard Operating Procedures (SOP) administration and recordkeeping",
            "Food safety, sanitation, and hygiene documentation maintenance",
        ],
        "affected_documents": [
            "Raw material batch receipts, supplier invoices, and Certificates of Analysis (CoA)",
            "Food handler medical fitness certificates and annual health screening reports",
            "Facility cleaning, equipment sanitation, and pest control logbooks",
            "Traceability log sheets linking raw ingredient lots to finished product batches",
        ],
        "action_templates": [
            "Establish and maintain verified documentation required by {instrument} ({clause}).",
            "Implement standardized batch log sheets for raw ingredient sourcing, lot numbers, and processing dates.",
            "Archive all production and compliance records on site for the mandatory statutory retention period.",
            "Ensure food handler medical screening records and sanitation logs are kept up to date.",
        ],
    },
    "reporting": {
        "affected_activities": [
            "Statutory compliance monitoring, periodic return collation, and filing",
            "Annual production volume, raw material consumption, and waste data logging",
            "Regulatory liaison and mandatory incident notification",
        ],
        "affected_documents": [
            "Statutory periodic compliance returns and annual reporting filings",
            "Production volume, capacity utilisation, and raw material balance sheets",
            "Waste disposal manifests and emission monitoring returns",
            "Official acknowledgment receipts of submitted regulatory filings",
        ],
        "action_templates": [
            "Prepare and submit periodic compliance returns to {authority} as mandated by {instrument}.",
            "Compile verified operational metrics (production output, employee count, resource usage) for statutory filing.",
            "Retain signed copies and official acknowledgment receipts of all filed reports for regulatory audit.",
            "Establish scheduled review alerts to ensure timely submission of recurring filings to {authority}.",
        ],
    },
    "process": {
        "affected_activities": [
            "Food processing line operations, recipe formulation, and temperature controls",
            "Good Manufacturing Practices (GMP) and sanitary hazard control protocols",
            "Measuring instrument calibration and critical control point (CCP) logging",
        ],
        "affected_documents": [
            "Standard Operating Procedures (SOPs) for processing, handling, and storage",
            "Critical Control Point (CCP) and temperature monitoring records",
            "Equipment calibration logs and preventive maintenance schedules",
            "Staff hygiene training logs and sanitation checklists",
        ],
        "action_templates": [
            "Calibrate manufacturing process parameters to satisfy the standard stipulated in {clause}.",
            "Implement Good Manufacturing Practices (GMP) controls for sanitary handling and contamination prevention.",
            "Calibrate and verify measuring equipment (thermometers, weighing scales) and log results in daily registers.",
            "Train production line personnel on updated operational standards mandated by {instrument}.",
        ],
    },
}


def get_supported_obligation_types() -> List[str]:
    """Return the list of bounded obligation types supported by the mapper."""
    return list(SUPPORTED_OBLIGATION_TYPES)


def compute_timeline_note(
    rule: Union[Rule, Dict[str, Any]],
    evaluation_result: EvaluationResult,
) -> Optional[str]:
    """Compute timeline and compliance note based on temporal validity."""
    if isinstance(rule, dict):
        validity = rule.get("validity", {})
        commences = validity.get("commences")
        transition_until = validity.get("transition_until")
    else:
        commences = rule.validity.commences
        transition_until = rule.validity.transition_until

    if evaluation_result.temporal_status == "IN_TRANSITION" and transition_until:
        return f"Transition period active: Mandatory compliance deadline is {transition_until}."
    elif transition_until:
        return f"Transition period granted until {transition_until}."
    elif commences:
        return f"Immediate compliance required (in force since {commences})."
    return None


def map_impact(
    rule: Union[Rule, Dict[str, Any]],
    evaluation_result: EvaluationResult,
) -> Optional[BusinessImpact]:
    """Deterministically map an applicable rule to affected activities, documents, and action items.
    
    Returns BusinessImpact ONLY when evaluation_result.status == OutcomeStatus.APPLICABLE.
    Returns None for NOT_APPLICABLE, CONDITIONAL_MISSING_DATA, or UNSUPPORTED.
    """
    # 1. Guard against non-applicable outcomes (prevent false positives)
    if evaluation_result.status != OutcomeStatus.APPLICABLE:
        return None

    # 2. Extract rule metadata
    if isinstance(rule, dict):
        obligation = rule.get("obligation", {})
        ob_type_raw = str(obligation.get("type", "process")).strip().lower()
        ob_text = obligation.get("text", "")
        impact_cats = obligation.get("impact_categories", []) or []
        source = rule.get("source", {})
        authority = source.get("authority", "Regulatory Authority")
        instrument = source.get("instrument", "Applicable Regulation")
        clause = source.get("clause", "Stipulated Clause")
    else:
        ob_type_raw = str(rule.obligation.type).strip().lower()
        ob_text = rule.obligation.text
        impact_cats = rule.obligation.impact_categories or []
        authority = rule.source.authority
        instrument = rule.source.instrument
        clause = rule.source.clause

    # 3. Resolve obligation category from bounded vocabulary
    norm_type = "process"
    for supported in SUPPORTED_OBLIGATION_TYPES:
        if supported in ob_type_raw:
            norm_type = supported
            break

    mapping_entry = OBLIGATION_MAPPINGS.get(norm_type, OBLIGATION_MAPPINGS["process"])

    # 4. Compile affected activities & documents
    affected_activities = list(mapping_entry["affected_activities"])
    affected_documents = list(mapping_entry["affected_documents"])

    # Incorporate extra impact categories if specified in rule
    for cat in impact_cats:
        cat_clean = cat.strip().replace("_", " ").title()
        extra_act = f"{cat_clean} management and review"
        if extra_act not in affected_activities:
            affected_activities.append(extra_act)

    # 5. Parameterize action item templates
    action_items: List[str] = []
    for template in mapping_entry["action_templates"]:
        formatted = template.format(
            authority=authority,
            instrument=instrument,
            clause=clause,
            obligation_text=ob_text,
        )
        action_items.append(formatted)

    # Append specific obligation requirement as direct action if available
    if ob_text:
        direct_action = f"Fulfill specific requirement: {ob_text}"
        if direct_action not in action_items:
            action_items.insert(0, direct_action)

    # 6. Compute timeline note
    timeline_note = compute_timeline_note(rule, evaluation_result)

    return BusinessImpact(
        obligation_type=norm_type,
        affected_activities=affected_activities,
        affected_documents=affected_documents,
        action_items=action_items,
        timeline_note=timeline_note,
    )
