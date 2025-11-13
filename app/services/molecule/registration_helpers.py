from collections import defaultdict



def _name_key(name: str | None) -> str:
    """
    Normalization key for names / synonyms, consistent with get_molecule_by_name_exact:
    - strip
    - lower
    - remove all spaces
    """
    if not name:
        return ""
    return name.strip().lower().replace(" ", "")


def _split_synonyms_csv(csv: str | None) -> list[str]:
    if not csv:
        return []
    return [s.strip() for s in csv.split(",") if s and s.strip()]
