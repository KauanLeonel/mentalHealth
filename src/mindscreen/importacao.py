"""Descoberta e leitura não destrutiva de arquivos públicos NSCH."""

from dataclasses import dataclass
from pathlib import Path
import re


YEARS = tuple(range(2020, 2025))
FORMATS = {".dta", ".sas7bdat", ".csv"}


@dataclass(frozen=True)
class Candidate:
    path: Path
    year: int | None
    topical_hint: bool
    enhanced_hint: bool


def discover(raw_dir: Path) -> list[Candidate]:
    """Localiza arquivos suportados recursivamente; indícios não são validação."""
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        return []
    result = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in FORMATS:
            continue
        relative = str(path.relative_to(raw_dir)).lower()
        years = {int(x) for x in re.findall(r"(?<!\d)(202[0-4])(?!\d)", relative)}
        name = path.stem.lower()
        result.append(Candidate(path, next(iter(years)) if len(years) == 1 else None,
                                "topical" in name and "screener" not in name,
                                bool(re.search(r"enhanced|(?:^|[_-])202[0-4]e(?:[_-]|$)", name))))
    return result


def read_file(path: Path):
    """Retorna dados e metadados pyreadstat preservando códigos especiais suportados."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in {".dta", ".sas7bdat"}:
        raise ValueError(f"Formato não suportado: {path.suffix}")
    import pyreadstat
    if suffix == ".dta":
        return pyreadstat.read_dta(str(path), user_missing=True, apply_value_formats=False)
    if suffix == ".sas7bdat":
        return pyreadstat.read_sas7bdat(str(path), user_missing=True)
