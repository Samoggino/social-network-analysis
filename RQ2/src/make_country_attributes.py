#!/usr/bin/env python3
"""Build processed_data/tables/country_attributes_rq2.csv.

Reconstructed from the project conversation. Geography follows the UN M49
subregions (https://unstats.un.org/unsd/methodology/m49/); languages are broad
families, with more than one group for multilingual countries.

The country list is read from the matrices, so the table always matches the
data actually present. Run from the RQ2 directory:

    python src/make_country_attributes.py
"""
from __future__ import annotations

import csv
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
MATRIX_DIR = ROOT / "processed_data" / "matrices"
OUT_PATH = ROOT / "processed_data" / "tables" / "country_attributes_rq2.csv"

# ISO code: (name, UN M49 subregion, language groups, Eurovision block, notes)
COUNTRIES = {
    "AL": ("Albania", "Southern Europe", ["Albanian"], "Balkan", ""),
    "AM": ("Armenia", "Western Asia", ["Armenian"], "Caucasus", ""),
    "AT": ("Austria", "Western Europe", ["Germanic"], "Western", ""),
    "AU": ("Australia", "Australia and New Zealand", ["Germanic"], "Other", "Invited since 2015"),
    "AZ": ("Azerbaijan", "Western Asia", ["Turkic"], "Caucasus", ""),
    "BA": ("Bosnia and Herzegovina", "Southern Europe", ["Slavic"], "Balkan", "Voter only in this period"),
    "BE": ("Belgium", "Western Europe", ["Germanic", "Romance"], "Western", "Dutch and French"),
    "BG": ("Bulgaria", "Eastern Europe", ["Slavic"], "Balkan", ""),
    "BY": ("Belarus", "Eastern Europe", ["Slavic"], "Eastern", ""),
    "CH": ("Switzerland", "Western Europe", ["Germanic", "Romance"], "Western", "German, French, Italian"),
    "CY": ("Cyprus", "Western Asia", ["Greek"], "Mediterranean", "Greek and Turkish"),
    "CZ": ("Czechia", "Eastern Europe", ["Slavic"], "Eastern", ""),
    "DE": ("Germany", "Western Europe", ["Germanic"], "Big Five", ""),
    "DK": ("Denmark", "Northern Europe", ["Germanic"], "Nordic", ""),
    "EE": ("Estonia", "Northern Europe", ["Uralic"], "Baltic", ""),
    "ES": ("Spain", "Southern Europe", ["Romance"], "Big Five", ""),
    "FI": ("Finland", "Northern Europe", ["Uralic"], "Nordic", "Finnish and Swedish"),
    "FR": ("France", "Western Europe", ["Romance"], "Big Five", ""),
    "GB": ("United Kingdom", "Northern Europe", ["Germanic"], "Big Five", ""),
    "GE": ("Georgia", "Western Asia", ["Kartvelian"], "Caucasus", ""),
    "GR": ("Greece", "Southern Europe", ["Greek"], "Mediterranean", ""),
    "HR": ("Croatia", "Southern Europe", ["Slavic"], "Balkan", ""),
    "HU": ("Hungary", "Eastern Europe", ["Uralic"], "Eastern", ""),
    "IE": ("Ireland", "Northern Europe", ["Germanic"], "Western", "English and Irish"),
    "IL": ("Israel", "Western Asia", ["Semitic"], "Other", ""),
    "IS": ("Iceland", "Northern Europe", ["Germanic"], "Nordic", ""),
    "IT": ("Italy", "Southern Europe", ["Romance"], "Big Five", ""),
    "LT": ("Lithuania", "Northern Europe", ["Baltic"], "Baltic", ""),
    "LU": ("Luxembourg", "Western Europe", ["Germanic", "Romance"], "Western", "Returned in 2024"),
    "LV": ("Latvia", "Northern Europe", ["Baltic"], "Baltic", ""),
    "MD": ("Moldova", "Eastern Europe", ["Romance"], "Eastern", "Romanian"),
    "ME": ("Montenegro", "Southern Europe", ["Slavic"], "Balkan", "Voter only in this period"),
    "MK": ("North Macedonia", "Southern Europe", ["Slavic"], "Balkan", ""),
    "MT": ("Malta", "Southern Europe", ["Semitic", "Romance"], "Mediterranean", "Maltese and English"),
    "NL": ("Netherlands", "Western Europe", ["Germanic"], "Western", ""),
    "NO": ("Norway", "Northern Europe", ["Germanic"], "Nordic", ""),
    "PL": ("Poland", "Eastern Europe", ["Slavic"], "Eastern", ""),
    "PT": ("Portugal", "Southern Europe", ["Romance"], "Western", ""),
    "RO": ("Romania", "Eastern Europe", ["Romance"], "Balkan", ""),
    "RS": ("Serbia", "Southern Europe", ["Slavic"], "Balkan", ""),
    "RU": ("Russia", "Eastern Europe", ["Slavic"], "Eastern", "Excluded from 2022"),
    "SE": ("Sweden", "Northern Europe", ["Germanic"], "Nordic", ""),
    "SI": ("Slovenia", "Southern Europe", ["Slavic"], "Balkan", ""),
    "SM": ("San Marino", "Southern Europe", ["Romance"], "Mediterranean", ""),
    "UA": ("Ukraine", "Eastern Europe", ["Slavic"], "Eastern", ""),
}


def countries_in_matrices() -> set[str]:
    codes: set[str] = set()
    for path in sorted(MATRIX_DIR.glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle))
        codes |= set(header[1:])
    return codes


def main() -> None:
    codes = countries_in_matrices()

    missing = sorted(codes - set(COUNTRIES))
    if missing:
        raise SystemExit(f"Missing classifications: {missing}")

    extra = sorted(set(COUNTRIES) - codes)
    if extra:
        print(f"Note: classified but absent from the matrices: {extra}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["country", "name", "region", "language_groups", "eurovision_block", "notes"])
        for code in sorted(codes):
            name, region, languages, block, notes = COUNTRIES[code]
            writer.writerow([code, name, region, ";".join(languages), block, notes])

    print(f"Wrote {len(codes)} countries to {OUT_PATH}")


if __name__ == "__main__":
    main()
