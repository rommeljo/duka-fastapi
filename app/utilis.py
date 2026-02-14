def normalize_ke_phone(phone: str) -> str:
    p = (phone or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0") and len(p) == 10:
        p = "254" + p[1:]
    if p.startswith("7") and len(p) == 9:
        p = "254" + p
    return p
