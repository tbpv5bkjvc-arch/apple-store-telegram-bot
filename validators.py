import re

def normalize_kz_phone(phone: str) -> str | None:
    cleaned = re.sub(r"[\s()\-]", "", phone.strip())
    if re.fullmatch(r"\+7\d{10}", cleaned):
        return cleaned
    if re.fullmatch(r"8\d{10}", cleaned):
        return "+7" + cleaned[1:]
    if re.fullmatch(r"7\d{10}", cleaned):
        return "+" + cleaned
    return None

def check_kz_phone(phone: str) -> bool:
    return bool(normalize_kz_phone(phone))
