import pymupdf

doc = pymupdf.open("/app/backend/data/raw_sources/2494-47_E.pdf")
p1_text = doc[0].get_text()
p2_text = doc[1].get_text()

reg3_start_in_p1 = p1_text.find("3.\nA person shall not import")
print(f"Reg 3 in Page 1: start={reg3_start_in_p1}, text len={len(p1_text)}")
if reg3_start_in_p1 != -1:
    print("Page 1 snippet:\n", repr(p1_text[reg3_start_in_p1:reg3_start_in_p1+250]))

reg3_continuation_in_p2 = p2_text.find("Provided, that these regulations shall not apply to-")
print(f"Reg 3 in Page 2: start={reg3_continuation_in_p2}, text len={len(p2_text)}")
reg4_start_in_p2 = p2_text.find("4. (1)")
print(f"Reg 4 in Page 2: start={reg4_start_in_p2}")
if reg3_continuation_in_p2 != -1 and reg4_start_in_p2 != -1:
    print("Page 2 snippet:\n", repr(p2_text[reg3_continuation_in_p2:reg4_start_in_p2]))
