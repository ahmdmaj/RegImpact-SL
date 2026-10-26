import sys
import json
import logging
from pathlib import Path
from datetime import date

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    ClauseORM,
    RuleORM,
    HumanReviewAuditORM,
)
from backend.src.models.domain import (
    Rule,
    Source,
    Validity,
    AppliesIf,
    Condition,
    Obligation,
    Verification,
)

from backend.src.engine.verifier import RuleVerifier
from backend.src.extraction.embedding_client import SentenceTransformerEmbeddingClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOC_SUGAR = "doc_15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b"
DOC_PRESERVATIVE = "doc_3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f"
DOC_FLAVOURING = "doc_b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a"

def main():
    verifier = RuleVerifier()
    emb_client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    
    with session_scope() as db:
        # 1. UPDATE SOURCE DOCUMENT METADATA
        d_sugar = db.get(SourceDocumentORM, DOC_SUGAR)
        if d_sugar:
            d_sugar.title = "The Sri Lanka Gazette Extraordinary No. 2494/06 (Food Colour Coding for Sugar Levels Amendment)"
            d_sugar.authority = "Minister of Health and Mass Media"
            d_sugar.gazette_no = "2494/06"
            d_sugar.publication_date = date(2026, 6, 23)
            d_sugar.source_url = "http://www.documents.gov.lk"
            logger.info("Updated metadata for Sugar Amendment Gazette 2494/06")

        d_pres = db.get(SourceDocumentORM, DOC_PRESERVATIVE)
        if d_pres:
            d_pres.title = "The Sri Lanka Gazette Extraordinary No. 2113/16 (Food Preservatives Regulations 2019)"
            d_pres.authority = "Minister of Health, Nutrition and Indigenous Medicine"
            d_pres.gazette_no = "2113/16"
            d_pres.publication_date = date(2019, 3, 5)
            d_pres.source_url = "http://www.documents.gov.lk"
            logger.info("Updated metadata for Food Preservatives Gazette 2113/16")

        d_flav = db.get(SourceDocumentORM, DOC_FLAVOURING)
        if d_flav:
            d_flav.title = "The Sri Lanka Gazette Extraordinary No. 1795/51 (Food Flavouring Substances and Flavour Enhancers Regulations 2013)"
            d_flav.authority = "Minister of Health"
            d_flav.gazette_no = "1795/51"
            d_flav.publication_date = date(2013, 2, 1)
            d_flav.source_url = "http://www.documents.gov.lk"
            logger.info("Updated metadata for Food Flavouring Gazette 1795/51")

        # 2. DEFINITIONS OF OPERATIVE CLAUSES
        new_clauses = [
            # SUGAR AMENDMENT (Gazette 2494/06)
            {
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-3-1",
                "document_id": DOC_SUGAR,
                "clause_number": "Regulation 3(1)",
                "start_page": 1,
                "end_page": 2,
                "valid_from": date(2026, 6, 23),
                "text": (
                    "“(1) Where any food referred to in these regulations contains any amount of sugar specified in Column "
                    "I of the Schedule hereto, the label of such container or the package which contains such food shall have the "
                    "corresponding logo (hereinafter referred to as “the logo”) specified in Column III of the Schedule hereto in "
                    "the corresponding colour specified in Column II of the Schedule hereto: "
                    "Provided however, when there is a space constraint in the total printable area with respect to glass "
                    "bottles which contain such food in using the logo specified in Column III of the Schedule hereto, the logo "
                    "specified in Column IV of the said Schedule may be used in the corresponding colour specified in Column "
                    "II of the such Schedule.”;"
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-3-3",
                "document_id": DOC_SUGAR,
                "clause_number": "Regulation 3(3)",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2026, 6, 23),
                "text": (
                    "“(3) The logo specified in Column IV of the Schedule hereto shall be prepared, designed and displayed "
                    "in accordance with the following requirements: - "
                    "(a) the diameter of the inner circle of the logo shall be not less than 1cm; "
                    "(b) a description of the “sugar” content in such food shall be displayed within the logo in Sinhala, "
                    "Tamil and English languages respectively in bold black in the white outer circle and shall be of "
                    "minimum 1.5 mm font size; and "
                    "(c) a numeric description of the sugar content in such food shall be provided in the white outer circle "
                    "of the logo as shown in Column IV of the Schedule hereto and shall be of minimum 1.5 mm font "
                    "size in bold black.”;"
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-6-GA",
                "document_id": DOC_SUGAR,
                "clause_number": "Regulation 6(ga)",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2026, 6, 23),
                "text": (
                    "(3) in regulation 6 thereof, by the insertion immediately after paragraph (g) thereof, of the following paragraph: - "
                    "“(ga) business to business food products;”; "
                    "(4) in regulation 8 thereof, by the insertion immediately after the definition of the expression “amber” of the following definition: - "
                    "“business to business food products” means food products which are not offered for direct sale to the consumer for direct consumption but which are only used for further food processing, preparation or resale;"
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-SCHEDULE",
                "document_id": DOC_SUGAR,
                "clause_number": "Schedule (Regulation 3)",
                "start_page": 2,
                "end_page": 3,
                "valid_from": date(2026, 6, 23),
                "text": (
                    "SCHEDULE (Regulation 3) "
                    "Column I Sugar content | Column II Colour | Column III Logo | Column IV Logo\n"
                    "1. More than 8.0 g/100 ml | Red | Logo with Sugar in Sinhala, Tamil, English\n"
                    "2. 2.5g to 8.0 g/100 ml | Amber | Logo with Sugar in Sinhala, Tamil, English\n"
                    "3. Less than 2.5 g/100 ml | Green | Logo with Sugar in Sinhala, Tamil, English"
                )
            },

            # PRESERVATIVES REGULATIONS (Gazette 2113/16)
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-1",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Regulation 1",
                "start_page": 1,
                "end_page": 1,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "1. These Regulations may be cited as the Food (Preservatives) Regulation, 2019, "
                    "and shall come into operation from 01.01.2020."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-2",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Regulation 2",
                "start_page": 1,
                "end_page": 2,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "2. No person shall manufacture, import, store, transport, sell, offer for sale, distribute, use or advertise - "
                    "(a) any food preservative other than the preservatives specified in Schedule I hereto ; "
                    "(b) any food which has in or upon it any preservative, other than those specified in Schedule II hereto."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-3",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Regulation 3",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "3. Any food specified in Column I of Schedule II (hereinafter referred to as a “specified food”) "
                    "may have in or upon it, a preservative of the description specified in the corresponding entry of "
                    "Column II therof (hereinafter referred to as a “permitted preservative”) and the use of such preservative "
                    "shall be in compliance with the proportions set out in the corresponding entry of Column III thereof."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-4",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Regulation 4",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "4. Any specified food may have in or upon it, a mixture of two or more preservatives specified in Schedule II "
                    "hereto, only if the sum total of the preservatives does not exceed one hundred percentage when the quantity of each of such "
                    "preservative present in such food is expressed as a percentage of the maximum quantity of that preservative appropriate to "
                    "the food as specified in that Schedule."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-5",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Regulation 5",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "5. Any compounded food may contain any permitted preservative - "
                    "(a) introduced in the process of preparing such food using one or more specified foods, if the permitted preservative :- "
                    "(i) is present in any specified food used in the compounded food ; and "
                    "(ii) is present in the specified food used, in no greater proportion than the proportion specified in relation to the proportion specified in Column III of Schedule II. "
                    "(b) if the compounded food is a specified food and does not contain any permitted preservatives in any greater proportion than is specified in Column III thereto."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-8",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Regulation 8",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "8. The label on every container or package of food, to which a permitted preservative as specified in these regulations "
                    "has been added, shall have a declaration as set out in the Food (Labelling and Advertising) Regulation 2005 published in the "
                    "Gazette Extraordinary No. 1376/9 of January 19, 2005 as amended from time to time or replaced."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-SCHEDULE-I",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Schedule I",
                "start_page": 3,
                "end_page": 3,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "SCHEDULE I Permitted Preservatives "
                    "1. Sorbic acid INS 200 (Sodium sorbate 201, Potassium sorbate 202, Calcium sorbate 203)\n"
                    "2. Benzoic acid INS 210 (Sodium benzoate 211, Potassium benzoate 212, Calcium benzoate 213)\n"
                    "3. Sulphur dioxide INS 220 (Sodium sulphite 221, Sodium metabisulphite 223, Potassium metabisulphite 224)\n"
                    "4. Orthophenylphenol INS 231 (Sodium orthophenylphenate 232)\n"
                    "5. Nisin INS 234\n"
                    "6. Potassium nitrite INS 249, Sodium nitrite INS 250\n"
                    "7. Propionic acid INS 280 (Sodium propionate 281, Calcium propionate 282, Potassium propionate 283)"
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-SCHEDULE-II-FRUIT",
                "document_id": DOC_PRESERVATIVE,
                "clause_number": "Schedule II Item 3.1",
                "start_page": 5,
                "end_page": 5,
                "valid_from": date(2020, 1, 1),
                "text": (
                    "SCHEDULE II Articles of Food which may contain permitted preservatives. "
                    "3.1 Fruits and fruit products: "
                    "(f) Fruit based spreads e.g. chutney: Sorbates 300 mg/kg, Propionates GMP; "
                    "(g) Fruit preparations including pulp, puree, fruit topping: Sorbates 1000 mg/kg, Sulphites 100 mg/kg, Propionates GMP; "
                    "(h) Jams, Jellies, marmalades: Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP; "
                    "(i) Jams, Jellies and marmalades low in sugar or sugar free: Sorbates 500 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP."
                )
            },

            # FLAVOURINGS REGULATIONS (Gazette 1795/51)
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-1",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Regulation 1",
                "start_page": 1,
                "end_page": 1,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "1. These regulations may be cited as the Food (Flavouring Substances and Flavour Enhancers) "
                    "Regulations 2013 and shall come into force from 01st July 2014."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-6",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Regulation 6",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "6. The following may be used as flavour enhancers in food : "
                    "(a) Monosodium glutamate - INS 621 "
                    "(b) Disodium 5’ – guanylate - INS 627 "
                    "(c) Disodium 5’ – inosinate - INS 631"
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-7",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Regulation 7",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "7. Flavour enhancers – "
                    "(i) may be added to foods subject to observance of Good Manufacturing Practices (GMP) and where the label carries clearly a declaration as to the particular substance or substances used ; "
                    "(ii) shall not be added to any food for infants or young children below three years of age; and "
                    "(iii) shall not be used in the foods specified in Schedule III hereto."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-8",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Regulation 8",
                "start_page": 2,
                "end_page": 2,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "8. (1) Labelling of an article of food containing either a flavouring substance or a flavour enhancer shall be in compliance with the provisions of the Food (Labelling and Advertising) Regulations - 2005 published in Gazette Extraordinary No. 1376/9 of January 19, 2005 as may be amended or replaced subsequently. "
                    "(2) The label printed on or attached to the package of food containing – (d) any flavour enhancer or enhancers as an ingredient, shall include the words ‘‘flavour enhancer used’’ or ‘‘flavour enhancers used’’ as the case may be, along with the common name or names and the INS number or numbers, as the case may be. "
                    "(3) The label printed on or attached to the package of food shall not describe any nature - identical flavours in conjunction with any food as ‘‘natural flavours’’. "
                    "(4) No declaration shall be made on the label printed on or attached to the package of food, of the absence of any single flavour enhancer when the food contains any other flavour enhancer or enhancers."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-I",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Schedule I",
                "start_page": 4,
                "end_page": 4,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "Regulation 3 SCHEDULE - I Flavouring substances prohibited to be used in food: "
                    "(1) Aloin, (2) Berberine, (3) Beta-Azarone and cinnamyl anthracillate, (4) Cade oil, (5) Calamus oil, "
                    "(6) Cocaine, (7) Coumarin, (8) Diethylene glycol, (9) Diethylene glycol monoethyl ether, (10) Estragole, "
                    "(11) Eugenyl methyl ether, (12) Hypericine, (13) Nitrobenzene, (14) Pyroligenous acid, "
                    "(15) Saffrole and Isosaffrole, (16) Santonin, (17) Sasafras oil, (18) Thujone, Isothujone, (19) Tonka bean, "
                    "(20) Any other flavouring substance that is injurious or likely to be injurious to health."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-II",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Schedule II",
                "start_page": 5,
                "end_page": 5,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "Regulation 4 and 5 SCHEDULE II Permitted Solvents. "
                    "The following solvents are permitted to be used in flavouring substances : "
                    "1. Diacetin, 2. Diethyl ether, 3. Ethyl acetate, 4. Ethyl alcohol, 5. Glycerol, "
                    "6. Isopropyl alcohol, 7. Propylene glycol, 8. Triacetin, 9. Water."
                )
            },
            {
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-SCHEDULE-III",
                "document_id": DOC_FLAVOURING,
                "clause_number": "Schedule III",
                "start_page": 5,
                "end_page": 5,
                "valid_from": date(2014, 7, 1),
                "text": (
                    "Regulation 7 (iii) SCHEDULE III Foods in which flavour enhancers are prohibited: "
                    "1. Milk and Milk Products, 2. Ice cream and frozen desserts, 3. Fats and oils, 4. Margarine and Fat Spreads, "
                    "5. Fresh, surface treated, peeled or cut fruits and vegetables, 6. Mushrooms and their products, 7. Fruit wines, "
                    "8. All fruit and vegetable products except fruit powders, vegetable powders, instant fruit and vegetable chutney mix (dry), "
                    "9. Vinegar, 10. Food grains, pulses, oil seeds and ground/powdered food grains, 11. Whole, broken or flaked grains including rice, "
                    "12. Edible flours and starches, 13. Sago, 14. Pastas and noodles (only dried products), 15. Malt based foods and milk based foods, "
                    "16. Bakery Products, 17. Fresh meat, poultry and game, 18. Fresh fish and molluscs, crustaceans, "
                    "19. White sugar, brown sugar and syrups, bee honey, 20. Sugar confectionery, 21. Ice - candies, "
                    "22. Culinary herbs, spices, condiment powder and curry powder, 23. Black tea, green tea, coffee, 24. Baking powder, 25. Cocoa butter and Cocoa products."
                )
            }
        ]

        # Insert or update clauses
        inserted_clauses = 0
        updated_clauses = 0
        for c_data in new_clauses:
            existing = db.get(ClauseORM, (c_data["clause_id"], 1))
            if existing:
                existing.clause_number = c_data["clause_number"]
                existing.text = c_data["text"]
                existing.start_page = c_data["start_page"]
                existing.end_page = c_data["end_page"]
                existing.valid_from = c_data["valid_from"]
                existing.is_synthetic = False
                existing.is_compilable = True
                emb = emb_client.embed_text(existing.text)
                existing.embedding = emb
                existing.embedding_verified = True
                existing.embedding_provider = "sentence-transformers"
                existing.embedding_model = "BAAI/bge-base-en-v1.5"
                updated_clauses += 1
            else:
                emb = emb_client.embed_text(c_data["text"])
                new_c = ClauseORM(
                    clause_id=c_data["clause_id"],
                    version_number=1,
                    document_id=c_data["document_id"],
                    clause_number=c_data["clause_number"],
                    text=c_data["text"],
                    start_page=c_data["start_page"],
                    end_page=c_data["end_page"],
                    valid_from=c_data["valid_from"],
                    is_compilable=True,
                    is_synthetic=False,
                    embedding=emb,
                    embedding_verified=True,
                    embedding_provider="sentence-transformers",
                    embedding_model="BAAI/bge-base-en-v1.5",
                )
                db.add(new_c)
                inserted_clauses += 1

        db.flush()
        logger.info("Clauses processed: %d inserted, %d updated.", inserted_clauses, updated_clauses)

        # 3. DEFINE CANDIDATE RULES (Stage 2)
        # All candidate rules are verified with RuleVerifier, validated against verbatim quote_span,
        # and saved with review_status="PENDING_REVIEW"
        candidate_rules = [
            # Rule 1: Sugar Colour Coding - Red Logo (High Sugar)
            {
                "rule_id": "RULE-SUGAR-2494-06-RED",
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-SCHEDULE",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.is_liquid", "op": "eq", "value": True},
                        {"field": "products.sugar_g_per_100ml", "op": "gt", "value": 8.0}
                    ]
                },
                "exceptions": [
                    {"field": "products.is_b2b", "op": "eq", "value": True}
                ],
                "obligation": {
                    "type": "labelling",
                    "description": "Label must bear the corresponding Red logo specifying sugar content more than 8.0 g/100 ml.",
                    "impact_categories": ["packaging", "labelling"]
                },
                "validity": {
                    "published": "2026-06-23",
                    "commences": "2026-06-23",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2494/06",
                    "authority": "Minister of Health and Mass Media",
                    "gazette_no": "2494/06",
                    "clause": "Schedule (Regulation 3)",
                    "page": 2,
                    "quote_span": "1. More than 8.0 g/100 ml | Red | Logo with Sugar in Sinhala, Tamil, English"
                }
            },
            # Rule 2: Sugar Colour Coding - Amber Logo (Medium Sugar)
            {
                "rule_id": "RULE-SUGAR-2494-06-AMBER",
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-SCHEDULE",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.is_liquid", "op": "eq", "value": True},
                        {"field": "products.sugar_g_per_100ml", "op": "gte", "value": 2.5},
                        {"field": "products.sugar_g_per_100ml", "op": "lte", "value": 8.0}
                    ]
                },
                "exceptions": [
                    {"field": "products.is_b2b", "op": "eq", "value": True}
                ],
                "obligation": {
                    "type": "labelling",
                    "description": "Label must bear the corresponding Amber logo specifying sugar content between 2.5g to 8.0 g/100 ml.",
                    "impact_categories": ["packaging", "labelling"]
                },
                "validity": {
                    "published": "2026-06-23",
                    "commences": "2026-06-23",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2494/06",
                    "authority": "Minister of Health and Mass Media",
                    "gazette_no": "2494/06",
                    "clause": "Schedule (Regulation 3)",
                    "page": 3,
                    "quote_span": "2. 2.5g to 8.0 g/100 ml | Amber | Logo with Sugar in Sinhala, Tamil, English"
                }
            },
            # Rule 3: Sugar Colour Coding - Green Logo (Low Sugar)
            {
                "rule_id": "RULE-SUGAR-2494-06-GREEN",
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-SCHEDULE",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.is_liquid", "op": "eq", "value": True},
                        {"field": "products.sugar_g_per_100ml", "op": "lt", "value": 2.5}
                    ]
                },
                "exceptions": [
                    {"field": "products.is_b2b", "op": "eq", "value": True}
                ],
                "obligation": {
                    "type": "labelling",
                    "description": "Label must bear the corresponding Green logo specifying sugar content less than 2.5 g/100 ml.",
                    "impact_categories": ["packaging", "labelling"]
                },
                "validity": {
                    "published": "2026-06-23",
                    "commences": "2026-06-23",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2494/06",
                    "authority": "Minister of Health and Mass Media",
                    "gazette_no": "2494/06",
                    "clause": "Schedule (Regulation 3)",
                    "page": 3,
                    "quote_span": "3. Less than 2.5 g/100 ml | Green | Logo with Sugar in Sinhala, Tamil, English"
                }
            },
            # Rule 4: Glass Bottle Printable Space Constraint Proviso
            {
                "rule_id": "RULE-SUGAR-2494-06-GLASS-PROVISO",
                "clause_id": f"CLAUSE-{DOC_SUGAR.upper()}-REGULATION-3-1",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.package_material", "op": "eq", "value": "glass_bottle"},
                        {"field": "products.printable_area_constrained", "op": "eq", "value": True}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "labelling",
                    "description": "When there is a space constraint in printable area on glass bottles, the compact logo in Column IV may be used in the corresponding colour.",
                    "impact_categories": ["packaging", "labelling"]
                },
                "validity": {
                    "published": "2026-06-23",
                    "commences": "2026-06-23",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2494/06",
                    "authority": "Minister of Health and Mass Media",
                    "gazette_no": "2494/06",
                    "clause": "Regulation 3(1)",
                    "page": 2,
                    "quote_span": "Provided however, when there is a space constraint in the total printable area with respect to glass bottles which contain such food in using the logo specified in Column III of the Schedule hereto, the logo specified in Column IV of the said Schedule may be used in the corresponding colour specified in Column II of the such Schedule."
                }
            },

            # Rule 5: Preservatives - Sum Total Mixture Percentage Constraint (Regulation 4)
            {
                "rule_id": "RULE-PRESERVATIVE-MIXTURE-LIMIT",
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-4",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.has_preservative_mixture", "op": "eq", "value": True}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "formulation",
                    "description": "Sum total of preservatives expressed as percentage of maximum permitted levels in Schedule II must not exceed 100 percentage.",
                    "impact_categories": ["recipe_formulation", "quality_control"]
                },
                "validity": {
                    "published": "2019-03-05",
                    "commences": "2020-01-01",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2113/16",
                    "authority": "Minister of Health, Nutrition and Indigenous Medicine",
                    "gazette_no": "2113/16",
                    "clause": "Regulation 4",
                    "page": 2,
                    "quote_span": "Any specified food may have in or upon it, a mixture of two or more preservatives specified in Schedule II hereto, only if the sum total of the preservatives does not exceed one hundred percentage when the quantity of each of such preservative present in such food is expressed as a percentage of the maximum quantity of that preservative appropriate to the food as specified in that Schedule."
                }
            },
            # Rule 6: Preservatives - Jam/Jelly Permitted Limits (Schedule II Item 3.1(h))
            {
                "rule_id": "RULE-PRESERVATIVE-JAM-JELLY-LIMIT",
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-SCHEDULE-II-FRUIT",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.category", "op": "eq", "value": "jams_jellies_marmalades"}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "formulation",
                    "description": "Permitted preservatives in jams, jellies, marmalades: Sorbates maximum 300 mg/kg, Sulphites maximum 100 mg/kg, or Propionates GMP.",
                    "impact_categories": ["recipe_formulation", "ingredient_specification"]
                },
                "validity": {
                    "published": "2019-03-05",
                    "commences": "2020-01-01",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2113/16",
                    "authority": "Minister of Health, Nutrition and Indigenous Medicine",
                    "gazette_no": "2113/16",
                    "clause": "Schedule II Item 3.1",
                    "page": 5,
                    "quote_span": "(h) Jams, Jellies, marmalades: Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP;"
                }
            },
            # Rule 7: Preservatives - General Mandatory Labelling Declaration (Regulation 8)
            {
                "rule_id": "RULE-PRESERVATIVE-LABEL-DECLARATION",
                "clause_id": f"CLAUSE-{DOC_PRESERVATIVE.upper()}-REGULATION-8",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.contains_preservative", "op": "eq", "value": True}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "labelling",
                    "description": "Container or package of food containing added permitted preservative must carry declaration as set out in Food Labelling Regulations.",
                    "impact_categories": ["packaging", "labelling"]
                },
                "validity": {
                    "published": "2019-03-05",
                    "commences": "2020-01-01",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 2113/16",
                    "authority": "Minister of Health, Nutrition and Indigenous Medicine",
                    "gazette_no": "2113/16",
                    "clause": "Regulation 8",
                    "page": 2,
                    "quote_span": "The label on every container or package of food, to which a permitted preservative as specified in these regulations has been added, shall have a declaration as set out in the Food (Labelling and Advertising) Regulation 2005 published in the Gazette Extraordinary No. 1376/9 of January 19, 2005 as amended from time to time or replaced."
                }
            },

            # Rule 8: Flavourings - Infant Food Flavour Enhancer Prohibition (Regulation 7(ii))
            {
                "rule_id": "RULE-FLAVOUR-INFANT-PROHIBITION",
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-7",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.target_consumer", "op": "eq", "value": "infants_or_young_children_under_3"}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "prohibition",
                    "description": "Flavour enhancers shall not be added to any food for infants or young children below three years of age.",
                    "impact_categories": ["recipe_formulation", "safety_compliance"]
                },
                "validity": {
                    "published": "2013-02-01",
                    "commences": "2014-07-01",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 1795/51",
                    "authority": "Minister of Health",
                    "gazette_no": "1795/51",
                    "clause": "Regulation 7",
                    "page": 2,
                    "quote_span": "(ii) shall not be added to any food for infants or young children below three years of age; and"
                }
            },
            # Rule 9: Flavourings - Schedule III Foods Flavour Enhancer Prohibition (Regulation 7(iii))
            {
                "rule_id": "RULE-FLAVOUR-SCHEDULE-III-PROHIBITION",
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-7",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.category", "op": "eq", "value": "bakery_products"}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "prohibition",
                    "description": "Flavour enhancers shall not be used in the foods specified in Schedule III hereto (including bakery products).",
                    "impact_categories": ["recipe_formulation", "safety_compliance"]
                },
                "validity": {
                    "published": "2013-02-01",
                    "commences": "2014-07-01",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 1795/51",
                    "authority": "Minister of Health",
                    "gazette_no": "1795/51",
                    "clause": "Regulation 7",
                    "page": 2,
                    "quote_span": "(iii) shall not be used in the foods specified in Schedule III hereto."
                }
            },
            # Rule 10: Flavourings - Flavour Enhancer Label Declaration (Regulation 8(2)(d))
            {
                "rule_id": "RULE-FLAVOUR-LABEL-DECLARATION",
                "clause_id": f"CLAUSE-{DOC_FLAVOURING.upper()}-REGULATION-8",
                "clause_version": 1,
                "outcome_type": "STANDARD",
                "applies_if": {
                    "all": [
                        {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                        {"field": "products.contains_flavour_enhancer", "op": "eq", "value": True}
                    ]
                },
                "exceptions": [],
                "obligation": {
                    "type": "labelling",
                    "description": "Label printed on or attached to package of food containing flavour enhancer must include words 'flavour enhancer used' along with common name and INS number.",
                    "impact_categories": ["packaging", "labelling"]
                },
                "validity": {
                    "published": "2013-02-01",
                    "commences": "2014-07-01",
                    "transition_until": None,
                    "superseded_date": None
                },
                "source": {
                    "instrument": "The Sri Lanka Gazette Extraordinary No. 1795/51",
                    "authority": "Minister of Health",
                    "gazette_no": "1795/51",
                    "clause": "Regulation 8",
                    "page": 2,
                    "quote_span": "(d) any flavour enhancer or enhancers as an ingredient, shall include the words ‘‘flavour enhancer used’’ or ‘‘flavour enhancers used’’ as the case may be, along with the common name or names and the INS number or numbers, as the case may be."
                }
            }
        ]

        verified_rules_count = 0
        rejected_rules_count = 0

        for r_dict in candidate_rules:
            # Build Pydantic Rule for verification
            pydantic_rule = Rule(
                rule_id=r_dict["rule_id"],
                source=Source(
                    instrument=r_dict["source"]["instrument"],
                    authority=r_dict["source"]["authority"],
                    gazette_no=r_dict["source"]["gazette_no"],
                    clause=r_dict["source"]["clause"],
                    page=r_dict["source"]["page"],
                    quote_span=r_dict["source"]["quote_span"]
                ),
                validity=Validity(
                    published=r_dict["validity"]["published"],
                    commences=r_dict["validity"]["commences"],
                    transition_until=r_dict["validity"]["transition_until"],
                    superseded_date=r_dict["validity"]["superseded_date"]
                ),
                applies_if=AppliesIf(
                    all=[Condition(**c) for c in r_dict["applies_if"]["all"]]
                ),
                exceptions=[Condition(**e) for e in r_dict["exceptions"]] if r_dict["exceptions"] else None,
                obligation=Obligation(
                    type=r_dict["obligation"]["type"],
                    text=r_dict["obligation"]["description"],
                    impact_categories=r_dict["obligation"]["impact_categories"]
                ),
                verification=Verification(
                    status="pending_review",
                    extraction_model="compiler_phase_3_3",
                    agreement=False,
                )
            )


            # Retrieve clause text from DB for quote verification
            clause_record = db.get(ClauseORM, (r_dict["clause_id"], 1))
            clause_text = clause_record.text if clause_record else ""

            # Run RuleVerifier
            metadata = {
                "published": r_dict["validity"]["published"],
                "commences": r_dict["validity"]["commences"],
            }
            report = verifier.verify(pydantic_rule, source_text=clause_text, metadata=metadata)
            logger.info("Rule %s verification: is_valid=%s, status=%s, issues=%s", r_dict["rule_id"], report.is_valid, report.status, [i.message for i in report.issues])

            if report.is_valid:
                verified_rules_count += 1
                # Insert or update in PostgreSQL as PENDING_REVIEW
                existing_r = db.get(RuleORM, r_dict["rule_id"])
                if existing_r:
                    existing_r.clause_id = r_dict["clause_id"]
                    existing_r.clause_version = r_dict["clause_version"]
                    existing_r.outcome_type = r_dict["outcome_type"]
                    existing_r.review_status = "PENDING_REVIEW"
                    existing_r.applies_if = r_dict["applies_if"]
                    existing_r.exceptions = r_dict["exceptions"]
                    existing_r.obligation = r_dict["obligation"]
                    existing_r.validity = r_dict["validity"]
                    existing_r.source = r_dict["source"]
                    existing_r.is_gold_rule = False
                    existing_r.is_synthetic = False
                else:
                    new_r = RuleORM(
                        rule_id=r_dict["rule_id"],
                        clause_id=r_dict["clause_id"],
                        clause_version=r_dict["clause_version"],
                        outcome_type=r_dict["outcome_type"],
                        review_status="PENDING_REVIEW",
                        applies_if=r_dict["applies_if"],
                        exceptions=r_dict["exceptions"],
                        obligation=r_dict["obligation"],
                        validity=r_dict["validity"],
                        source=r_dict["source"],
                        is_gold_rule=False,
                        is_synthetic=False,
                    )
                    db.add(new_r)
            else:
                rejected_rules_count += 1
                logger.error("Rule %s failed verification!", r_dict["rule_id"])

        db.flush()
        logger.info("Rule processing complete: %d verified into PENDING_REVIEW, %d rejected.", verified_rules_count, rejected_rules_count)

if __name__ == "__main__":
    main()
