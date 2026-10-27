import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.src.db.session import session_scope
from backend.src.db.models import ClauseORM
from backend.src.engine.verifier import normalize_text, RuleVerifier
from backend.src.models.domain import Rule, Source, Validity, AppliesIf, Condition, Obligation, Verification

with session_scope() as session:
    c = session.get(ClauseORM, ("CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV", 1))
    print("Raw clause text:\n", repr(c.text))
    print("\nNormalized clause text:\n", normalize_text(c.text))
    
    quote1 = "“(iv) fish, molluscs, crustaceans and echinoderms;”."
    print("\nquote1 in clause text:", normalize_text(quote1).lower() in normalize_text(c.text).lower())
    
    quote2 = "(1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:-\n“(iv) fish, molluscs, crustaceans and echinoderms;”."
    print("quote2 in clause text:", normalize_text(quote2).lower() in normalize_text(c.text).lower())

    quote3 = "“(iv) fish, molluscs, crustaceans and echinoderms;”"
    print("quote3 in clause text:", normalize_text(quote3).lower() in normalize_text(c.text).lower())
