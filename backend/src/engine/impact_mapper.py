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
            "Establish and maintain verified documentation required by {authority} under {instrument} ({clause}).",
            "Implement standardized batch log sheets for raw ingredient sourcing, lot numbers, and processing dates.",
            "Archive all production and compliance records on site for statutory inspection by {authority}.",
            "Ensure food handler medical screening records and sanitation logs are kept up to date for regulatory review.",
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
            "Calibrate manufacturing process parameters to satisfy the standard stipulated in {clause} enforced by {authority}.",
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


# Statutory descriptions for B2B mandatory disclosures under Gazette No. 2494/47 Regulation 3 Proviso (b)
B2B_STATUTORY_DISCLOSURE_DESCRIPTIONS: Dict[str, str] = {
    "common_name": "Common name (in either of the three languages)",
    "common_name_in_either_of_three_languages": "Common name (in either of the three languages)",
    "trade_name": "Trade name (if applicable)",
    "trade_name_if_applicable": "Trade name (if applicable)",
    "net_contents": "Net contents",
    "date_of_manufacture": "Date of manufacture",
    "date_of_expiry": "Date of expiry",
    "batch_number": "Batch number",
    "manufacturer_details": "Manufacturer's name and address",
    "manufacturer_name_and_address": "Manufacturer's name and address",
    "distributor_details": "Distributor's name and address",
    "distributor_name_and_address": "Distributor's name and address",
    "country_of_origin": "Country of origin in the case of imported foods",
    "country_of_origin_if_imported": "Country of origin in the case of imported foods",
    "ingredients_list": "A complete list of ingredients",
    "complete_list_of_ingredients": "A complete list of ingredients",
    "not_for_retail_sale_statement": "Conspicuous bold 'Not for retail sale' statement in a font size of not less than 3 mm",
    "statement_not_for_retail_sale_conspicuous_bold_gte_3mm": "Conspicuous bold 'Not for retail sale' statement in a font size of not less than 3 mm",
}


def map_impact(
    rule: Union[Rule, Dict[str, Any]],
    evaluation_result: Optional[EvaluationResult] = None,
) -> Optional[BusinessImpact]:
    """Deterministically map an applicable rule to affected activities, documents, and action items.
    
    Returns BusinessImpact ONLY when evaluation_result is None or evaluation_result.status == OutcomeStatus.APPLICABLE.
    Returns None for NOT_APPLICABLE, CONDITIONAL_MISSING_DATA, or UNSUPPORTED.
    """
    # 1. Guard against non-applicable outcomes (prevent false positives)
    if evaluation_result is not None and evaluation_result.status != OutcomeStatus.APPLICABLE:
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
        rule_id = str(rule.get("rule_id", ""))
        disclosures = obligation.get("disclosures")
    else:
        ob_type_raw = str(rule.obligation.type).strip().lower()
        ob_text = rule.obligation.text
        impact_cats = rule.obligation.impact_categories or []
        authority = rule.source.authority
        instrument = rule.source.instrument
        clause = rule.source.clause
        rule_id = str(rule.rule_id)
        disclosures = rule.obligation.disclosures

    # 3. Detect B2B labelling obligation vs generic retail labelling
    is_b2b = (
        bool(disclosures)
        or "b2b_compliance" in impact_cats
        or "b2b" in rule_id.lower()
        or "proviso (b)" in clause.lower()
    )

    if is_b2b and "labelling" in ob_type_raw:
        # B2B specific mapping (Regulation 3 Proviso (b))
        norm_type = "labelling"
        affected_activities = [
            "B2B product packaging design and bulk container specification",
            "Packaging line printing, batch coding, and supplementary label application",
            "B2B finished goods regulatory compliance verification and dispatch inspection",
        ]
        affected_documents = [
            "Business-to-business product packaging specifications and label artwork",
            "Batch coding, manufacturing date, and expiry date records",
            "Manufacturer and distributor identification and address records",
            "Ingredient declaration and country of origin documentation (imported foods)",
            "Supplementary label specifications for 'Not for retail sale' marking (font size >= 3 mm)",
        ]

        action_items: List[str] = []
        if ob_text:
            action_items.append(f"Fulfill specific requirement: {ob_text}")

        # Core statutory B2B exemption condition notice
        action_items.append(
            f"Ensure packaging complies with B2B exemption under {instrument} ({clause}): "
            "product is exempt from general retail labelling requirements but must satisfy mandatory B2B disclosures and marking."
        )

        # Mandatory marking item
        action_items.append(
            f"Print on label or affix through supplementary label the statement 'Not for retail sale' "
            f"clearly and conspicuously in bold type and font size of not less than 3 mm ({clause})."
        )

        # Single-language common name (explicitly NOT trilingual)
        action_items.append(
            f"Ensure packaging displays common name in either of the three languages (Sinhala, Tamil, or English) per {clause}."
        )

        # Surface specific mandatory disclosures with verified statutory wording
        if disclosures:
            for d in disclosures:
                if d in ("not_for_retail_sale_statement", "statement_not_for_retail_sale_conspicuous_bold_gte_3mm"):
                    continue
                desc = B2B_STATUTORY_DISCLOSURE_DESCRIPTIONS.get(d, d.replace("_", " ").title())
                action_items.append(f"Mandatory B2B disclosure: {desc}.")

        action_items.append(
            f"Verify batch coding, net contents, manufacturer name and address, and expiry date format on production line ({authority})."
        )
        action_items.append(
            "Audit current B2B packaging inventory and plan transition to compliant labels before deadline."
        )

        # Incorporate extra impact categories if specified in rule
        for cat in impact_cats:
            cat_clean = cat.strip().replace("_", " ").title()
            extra_act = f"{cat_clean} management and review"
            if extra_act not in affected_activities:
                affected_activities.append(extra_act)

        timeline_note = compute_timeline_note(rule, evaluation_result)

        return BusinessImpact(
            obligation_type=norm_type,
            affected_activities=affected_activities,
            affected_documents=affected_documents,
            action_items=action_items,
            timeline_note=timeline_note,
        )

    # 4. Standard mapping for general obligation types
    norm_type = "process"
    for supported in SUPPORTED_OBLIGATION_TYPES:
        if supported in ob_type_raw:
            norm_type = supported
            break

    mapping_entry = OBLIGATION_MAPPINGS.get(norm_type, OBLIGATION_MAPPINGS["process"])

    # 5. Compile affected activities & documents
    affected_activities = list(mapping_entry["affected_activities"])
    affected_documents = list(mapping_entry["affected_documents"])

    # Incorporate extra impact categories if specified in rule
    for cat in impact_cats:
        cat_clean = cat.strip().replace("_", " ").title()
        extra_act = f"{cat_clean} management and review"
        if extra_act not in affected_activities:
            affected_activities.append(extra_act)

    # 6. Parameterize action item templates
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

    # 7. Compute timeline note
    timeline_note = compute_timeline_note(rule, evaluation_result)

    return BusinessImpact(
        obligation_type=norm_type,
        affected_activities=affected_activities,
        affected_documents=affected_documents,
        action_items=action_items,
        timeline_note=timeline_note,
    )
