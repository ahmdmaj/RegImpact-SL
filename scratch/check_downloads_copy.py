import hashlib

with open(r"C:\Users\HP\Downloads\2494-06_E_1784568259 (1).pdf", "rb") as f:
    d = f.read()

print("Downloads copy SHA256:", hashlib.sha256(d).hexdigest())
