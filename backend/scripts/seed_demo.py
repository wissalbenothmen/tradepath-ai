"""Seed rich demo data for TradePath AI.

Run from ``backend/`` with::

    python -m scripts.seed_demo

Idempotent — re-running drops the demo tenant's rows and recreates them.
Creates two tenants:

* **Acme Trade Co** (3 users) — main demo tenant. 30+ shipments spread across
  6 months, full compliance workflow per shipment.
* **NorthStar Logistics** (1 user) — second tenant so the UI can demonstrate
  tenant isolation.

Default logins::

    demo@tradepath.ai       / DemoPass1!     (admin)
    broker@tradepath.ai     / BrokerPass1!
    compliance@tradepath.ai / CompliancePass1!
    otherco@tradepath.ai    / OtherCoPass1!   (second tenant)
"""
from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Allow ``python scripts/seed_demo.py`` from backend/.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.certificate_of_origin import (  # noqa: E402
    CertificateOfOrigin,
    COOFormat,
    OriginCriterion,
)
from app.models.customs_declaration import (  # noqa: E402
    CustomsDeclaration,
    DeclarationStatus,
    DeclarationType,
)
from app.models.denied_party_screening import (  # noqa: E402
    DeniedPartyScreening,
    ScreeningResult,
)
from app.models.fta_analysis import FTAAnalysis  # noqa: E402
from app.models.hs_classification import (  # noqa: E402
    ClassificationStatus,
    HSClassification,
)
from app.models.shipment import Shipment, ShipmentStatus, TransportMode  # noqa: E402
from app.models.shipment_amendment import ShipmentAmendment  # noqa: E402
from app.models.shipment_line_item import ShipmentLineItem  # noqa: E402
from app.models.trade_document import DocumentType, TradeDocument  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

random.seed(42)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
PRODUCTS = [
    {
        "desc": "14-inch laptop computers with Intel Core i7, 16GB RAM, 512GB SSD",
        "hs6": "847130",
        "hs_us": "8471.30.0100",
        "hs_eu": "8471300000",
        "duty_us": 0.0, "duty_eu": 0.0,
        "unit_value": 1450.0, "unit": "ea", "weight_kg": 1.4,
        "is_itar": False,
    },
    {
        "desc": "5G smartphones, OLED, 256GB",
        "hs6": "851712",
        "hs_us": "8517.12.0050",
        "hs_eu": "8517120000",
        "duty_us": 0.0, "duty_eu": 0.0,
        "unit_value": 820.0, "unit": "ea", "weight_kg": 0.21,
        "is_itar": False,
    },
    {
        "desc": "Cotton men's T-shirts, knitted, jersey weave",
        "hs6": "610910",
        "hs_us": "6109.10.0040",
        "hs_eu": "6109100010",
        "duty_us": 0.165, "duty_eu": 0.12,
        "unit_value": 8.40, "unit": "ea", "weight_kg": 0.18,
        "is_itar": False,
    },
    {
        "desc": "Industrial hydraulic pump, variable displacement, 250 bar",
        "hs6": "841320",
        "hs_us": "8413.20.0030",
        "hs_eu": "8413200000",
        "duty_us": 0.0, "duty_eu": 0.017,
        "unit_value": 4_280.0, "unit": "ea", "weight_kg": 38.0,
        "is_itar": False,
    },
    {
        "desc": "Specialty arabica green coffee beans, single origin",
        "hs6": "090111",
        "hs_us": "0901.11.0015",
        "hs_eu": "0901110000",
        "duty_us": 0.0, "duty_eu": 0.0,
        "unit_value": 4.20, "unit": "kg", "weight_kg": 1.0,
        "is_itar": False,
    },
    {
        "desc": "Electric passenger vehicle, lithium-ion 75kWh, 4-door sedan",
        "hs6": "870380",
        "hs_us": "8703.80.0000",
        "hs_eu": "8703801010",
        "duty_us": 0.025, "duty_eu": 0.10,
        "unit_value": 41_500.0, "unit": "ea", "weight_kg": 1_950.0,
        "is_itar": False,
    },
    {
        "desc": "Solid-state drives, NVMe, 1TB enterprise grade",
        "hs6": "852351",
        "hs_us": "8523.51.0000",
        "hs_eu": "8523511000",
        "duty_us": 0.0, "duty_eu": 0.0,
        "unit_value": 145.0, "unit": "ea", "weight_kg": 0.05,
        "is_itar": False,
    },
    {
        "desc": "Industrial CNC machining centre, 5-axis, controlled goods",
        "hs6": "845710",
        "hs_us": "8457.10.0010",
        "hs_eu": "8457100000",
        "duty_us": 0.044, "duty_eu": 0.027,
        "unit_value": 188_000.0, "unit": "ea", "weight_kg": 6_400.0,
        "is_itar": True,
    },
    {
        "desc": "Laboratory gas chromatograph with mass spectrometer",
        "hs6": "902730",
        "hs_us": "9027.30.4000",
        "hs_eu": "9027300000",
        "duty_us": 0.0, "duty_eu": 0.0,
        "unit_value": 62_500.0, "unit": "ea", "weight_kg": 78.0,
        "is_itar": False,
    },
    {
        "desc": "Pharmaceutical APIs (active pharmaceutical ingredients)",
        "hs6": "294200",
        "hs_us": "2942.00.5000",
        "hs_eu": "2942000000",
        "duty_us": 0.062, "duty_eu": 0.055,
        "unit_value": 1_200.0, "unit": "kg", "weight_kg": 1.0,
        "is_itar": False,
    },
]

GRI_RULES = [
    {"rule": "GRI 1", "note": "Classification by terms of headings and notes"},
    {"rule": "GRI 3(a)", "note": "Most specific description preferred"},
    {"rule": "GRI 6", "note": "Subheading legal notes apply"},
]

LANES = [
    {"origin": "USA", "dest": "DEU", "mode": "sea", "incoterms": "FOB"},
    {"origin": "MEX", "dest": "USA", "mode": "road", "incoterms": "DAP"},
    {"origin": "CHN", "dest": "USA", "mode": "sea", "incoterms": "CIF"},
    {"origin": "DEU", "dest": "FRA", "mode": "road", "incoterms": "EXW"},
    {"origin": "VNM", "dest": "USA", "mode": "sea", "incoterms": "FOB"},
    {"origin": "USA", "dest": "MEX", "mode": "road", "incoterms": "FCA"},
    {"origin": "DEU", "dest": "GBR", "mode": "sea", "incoterms": "DAP"},
    {"origin": "KOR", "dest": "DEU", "mode": "air", "incoterms": "CIP"},
    {"origin": "JPN", "dest": "USA", "mode": "sea", "incoterms": "CIF"},
    {"origin": "BRA", "dest": "FRA", "mode": "sea", "incoterms": "CFR"},
    {"origin": "IND", "dest": "GBR", "mode": "sea", "incoterms": "FOB"},
    {"origin": "USA", "dest": "JPN", "mode": "air", "incoterms": "CIP"},
    {"origin": "SGP", "dest": "AUS", "mode": "sea", "incoterms": "CFR"},
    {"origin": "AUS", "dest": "USA", "mode": "air", "incoterms": "CIP"},
    {"origin": "USA", "dest": "KOR", "mode": "sea", "incoterms": "FOB"},
    {"origin": "TWN", "dest": "DEU", "mode": "sea", "incoterms": "FOB"},
    {"origin": "CAN", "dest": "USA", "mode": "road", "incoterms": "DAP"},
    {"origin": "USA", "dest": "CAN", "mode": "road", "incoterms": "FOB"},
    {"origin": "FRA", "dest": "USA", "mode": "air", "incoterms": "CIP"},
    {"origin": "ITA", "dest": "USA", "mode": "sea", "incoterms": "FOB"},
    {"origin": "ESP", "dest": "MEX", "mode": "sea", "incoterms": "DAP"},
]

EXPORTERS = [
    "Acme Manufacturing Co",
    "Heartland Components LLC",
    "Pacifica Trading Group",
    "BlueRidge Industrial",
    "Linden & Mauer GmbH",
    "Lyon Logistique SAS",
    "Saigon Apparel JSC",
    "Han River Tech Co",
    "Yokohama Precision KK",
    "São Paulo Commodities Ltda",
    "Mumbai Mills Pvt Ltd",
    "Aurora Mining Inc",
]
IMPORTERS = [
    "Northwind Distribution Inc",
    "Atlantic Wholesale LLC",
    "Mountain View Retail Group",
    "Stonebridge Industries",
    "Hanseatic Imports GmbH",
    "Paris Concept Stores SAS",
    "London Specialty Goods Ltd",
    "Sapporo Trade House KK",
]
SCREENING_NEAR_MATCHES = [
    ("Acme Trading International", "potential_match", 0.78),
    ("Pacifica Holdings Ltd", "potential_match", 0.71),
    ("Eastern Energy Cooperative", "potential_match", 0.66),
]
SCREENING_POSITIVE = [("Sanctioned Holdings LLC", "positive_match", 0.97)]
SDN_LISTS = [
    "OFAC SDN", "OFAC Consolidated", "EU Consolidated", "UN Security Council",
    "HM Treasury (UK)", "BIS Entity List", "BIS Denied Persons", "BIS Unverified",
]


def _ref(company_id: uuid.UUID, seq: int) -> str:
    short = str(company_id).replace("-", "")[:6].upper()
    return f"TP-{short}-{seq:05d}"


def _between(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, max(1, int(delta.total_seconds()))))


# ---------------------------------------------------------------------------
# Seeders
# ---------------------------------------------------------------------------
async def _wipe_company(session, company_id: uuid.UUID) -> None:
    """Remove every row owned by ``company_id`` so reruns are clean."""
    ship_ids = (await session.execute(
        select(Shipment.id).where(Shipment.company_id == company_id)
    )).scalars().all()
    if ship_ids:
        await session.execute(delete(ShipmentLineItem).where(ShipmentLineItem.shipment_id.in_(ship_ids)))
        await session.execute(delete(ShipmentAmendment).where(ShipmentAmendment.shipment_id.in_(ship_ids)))
        await session.execute(delete(AuditLog).where(AuditLog.shipment_id.in_(ship_ids)))
    await session.execute(delete(HSClassification).where(HSClassification.company_id == company_id))
    await session.execute(delete(DeniedPartyScreening).where(DeniedPartyScreening.company_id == company_id))
    await session.execute(delete(CustomsDeclaration).where(CustomsDeclaration.company_id == company_id))
    await session.execute(delete(CertificateOfOrigin).where(CertificateOfOrigin.company_id == company_id))
    await session.execute(delete(FTAAnalysis).where(FTAAnalysis.company_id == company_id))
    await session.execute(delete(TradeDocument).where(TradeDocument.company_id == company_id))
    await session.execute(delete(Shipment).where(Shipment.company_id == company_id))
    await session.execute(delete(User).where(User.company_id == company_id))
    await session.commit()


async def _ensure_user(session, *, email: str, password: str, full_name: str,
                        role: UserRole, company_id: uuid.UUID) -> User:
    existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        existing.company_id = company_id
        existing.hashed_password = hash_password(password)
        existing.full_name = full_name
        existing.role = role
        await session.commit()
        await session.refresh(existing)
        return existing
    user = User(
        email=email, hashed_password=hash_password(password),
        full_name=full_name, role=role, company_id=company_id, is_active="true",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _shipment_status_for_age(days_old: int) -> ShipmentStatus:
    """Older shipments are more likely to be cleared; recent ones still in flight."""
    if days_old > 90:
        return random.choices(
            [ShipmentStatus.CLEARED, ShipmentStatus.BLOCKED, ShipmentStatus.HOLD],
            weights=[80, 8, 12],
        )[0]
    if days_old > 30:
        return random.choices(
            [ShipmentStatus.CLEARED, ShipmentStatus.FILED, ShipmentStatus.DECLARATION_READY,
             ShipmentStatus.HOLD, ShipmentStatus.BLOCKED],
            weights=[55, 15, 12, 10, 8],
        )[0]
    if days_old > 7:
        return random.choices(
            [ShipmentStatus.FILED, ShipmentStatus.DECLARATION_READY, ShipmentStatus.CLASSIFICATION,
             ShipmentStatus.SCREENING, ShipmentStatus.HOLD],
            weights=[25, 30, 20, 15, 10],
        )[0]
    return random.choices(
        [ShipmentStatus.DRAFT, ShipmentStatus.SCREENING, ShipmentStatus.CLASSIFICATION],
        weights=[40, 30, 30],
    )[0]


async def _seed_tenant(session, *, company_id: uuid.UUID, owner: User,
                       shipment_count: int, start_date: datetime) -> dict:
    """Create ``shipment_count`` shipments and their dependent rows."""
    stats = {"shipments": 0, "classifications": 0, "screenings": 0, "declarations": 0,
             "coos": 0, "ftas": 0, "documents": 0, "amendments": 0}

    for seq in range(1, shipment_count + 1):
        days_offset = random.randint(0, 180)
        created_at = start_date + timedelta(days=180 - days_offset)
        lane = random.choice(LANES)
        status = _shipment_status_for_age(days_offset)
        exporter = random.choice(EXPORTERS)
        importer = random.choice(IMPORTERS)

        # Pick 1-4 products
        chosen = random.sample(PRODUCTS, k=random.randint(1, 4))
        total_value = 0.0
        total_weight = 0.0
        for p in chosen:
            qty = random.randint(1, 50) if p["unit"] == "ea" else random.randint(50, 500)
            total_value += qty * p["unit_value"]
            total_weight += qty * p["weight_kg"]

        denied_status = random.choices(
            ["clear", "potential_match", "positive_match"], weights=[80, 14, 6]
        )[0]
        # Guarantee at least 2 positive matches in the first 10 shipments so
        # the action queue + AI insights demos always have a red flag to show.
        if seq in (4, 9):
            denied_status = "positive_match"
        restriction = "clear" if not any(p["is_itar"] for p in chosen) else random.choice(
            ["license_required", "clear"]
        )

        shipment = Shipment(
            reference_number=_ref(company_id, seq),
            company_id=company_id,
            created_by=owner.id,
            status=status,
            transport_mode=TransportMode(lane["mode"]),
            origin_country=lane["origin"],
            destination_country=lane["dest"],
            incoterms=lane["incoterms"],
            exporter_name=exporter,
            exporter_country=lane["origin"],
            importer_name=importer,
            consignee_name=importer,
            notify_party=importer,
            manufacturer_name=exporter,
            freight_forwarder=random.choice([
                "Maersk Logistics", "DSV Air & Sea", "Kuehne+Nagel", "Expeditors", "DHL Global Forwarding",
            ]),
            total_value_usd=round(total_value, 2),
            total_weight_kg=round(total_weight, 2),
            currency="USD",
            shipment_date=(created_at - timedelta(days=random.randint(0, 5))).date(),
            denied_party_status=denied_status,
            restriction_status=restriction,
            notes=None,
            created_at=created_at,
            updated_at=created_at + timedelta(hours=random.randint(1, 240)),
        )
        session.add(shipment)
        await session.flush()
        stats["shipments"] += 1

        # ---- Line items + per-line HS classification + per-line FTA ----
        for idx, p in enumerate(chosen, start=1):
            qty = random.randint(1, 50) if p["unit"] == "ea" else random.randint(50, 500)
            line_value = round(qty * p["unit_value"], 2)
            line_weight = round(qty * p["weight_kg"], 2)

            line = ShipmentLineItem(
                shipment_id=shipment.id,
                line_number=idx,
                product_description=p["desc"],
                hs_code=p["hs6"],
                country_of_origin=lane["origin"],
                quantity=qty,
                unit=p["unit"],
                unit_value_usd=p["unit_value"],
                total_value_usd=line_value,
                weight_kg=line_weight,
                duty_rate=p["duty_us"] if lane["dest"] == "USA" else p["duty_eu"],
                duty_amount_usd=round(line_value * (p["duty_us"] if lane["dest"] == "USA" else p["duty_eu"]), 2),
                fta_preference=random.choice([None, "USMCA", "EUR.1", "GSP Form A"]),
                restriction_status=restriction,
                is_itar_ear="true" if p["is_itar"] else "false",
                hs_code_confirmed="true" if random.random() < 0.7 else "false",
            )
            session.add(line)
            await session.flush()

            # HS classification record
            confidence = round(random.uniform(0.65, 0.99), 2)
            cls_status = (ClassificationStatus.CONFIRMED
                          if confidence >= 0.85 and random.random() < 0.8
                          else ClassificationStatus.CLASSIFIED)
            cls = HSClassification(
                company_id=company_id,
                product_id=None,
                line_item_id=line.id,
                classified_by=owner.id,
                status=cls_status,
                hs_code_6digit=p["hs6"],
                hs_code_us_hts=p["hs_us"],
                hs_code_eu_taric=p["hs_eu"],
                hs_code_uk_gt=p["hs_us"],
                confidence=confidence,
                gri_rules_applied=GRI_RULES,
                top_candidates=[
                    {"hs_code": p["hs6"], "confidence": confidence,
                     "rationale": "GRI 1 — terms of the heading"},
                    {"hs_code": p["hs6"][:4] + "90",
                     "confidence": round(confidence - 0.12, 2),
                     "rationale": "Residual subheading candidate"},
                ],
                gpt_reasoning=(
                    "Item described as " + p["desc"][:80] +
                    f" — matched to heading {p['hs6'][:4]} via GRI 1 "
                    "with subheading determined by GRI 6."
                ),
                duty_rate_us=p["duty_us"],
                duty_rate_eu=p["duty_eu"],
                anti_dumping_duty=0.0,
                is_itar_ear_flagged="true" if p["is_itar"] else "false",
                confirmed_by=owner.id if cls_status == ClassificationStatus.CONFIRMED else None,
                confirmed_at=created_at + timedelta(hours=2)
                    if cls_status == ClassificationStatus.CONFIRMED else None,
                created_at=created_at + timedelta(hours=1),
            )
            session.add(cls)
            stats["classifications"] += 1

            # FTA analysis (when origin/dest combo has a real FTA)
            fta_map = {
                ("MEX", "USA"): ("USMCA", 0.025, 0.0),
                ("USA", "MEX"): ("USMCA", 0.05, 0.0),
                ("USA", "CAN"): ("USMCA", 0.025, 0.0),
                ("CAN", "USA"): ("USMCA", 0.025, 0.0),
                ("DEU", "FRA"): ("EU Single Market", 0.0, 0.0),
                ("DEU", "GBR"): ("EU-UK TCA", 0.027, 0.0),
                ("FRA", "USA"): ("EU-US Trade Pact", 0.025, 0.005),
                ("ITA", "USA"): ("EU-US Trade Pact", 0.025, 0.005),
                ("VNM", "USA"): ("CPTPP", 0.165, 0.06),
                ("KOR", "DEU"): ("EU-Korea FTA", 0.03, 0.0),
                ("USA", "KOR"): ("KORUS FTA", 0.04, 0.0),
                ("USA", "JPN"): ("US-Japan TAG", 0.026, 0.004),
                ("JPN", "USA"): ("US-Japan TAG", 0.026, 0.004),
                ("SGP", "AUS"): ("SAFTA", 0.05, 0.0),
                ("AUS", "USA"): ("AUSFTA", 0.025, 0.0),
                ("IND", "GBR"): ("UK-India FTA", 0.058, 0.012),
                ("ESP", "MEX"): ("EU-Mexico FTA", 0.035, 0.005),
                ("TWN", "DEU"): ("EU-Taiwan BIT", 0.03, 0.012),
            }
            agreement = fta_map.get((lane["origin"], lane["dest"]))
            if agreement:
                name, mfn, pref = agreement
                saving = round(line_value * (mfn - pref), 2)
                fta = FTAAnalysis(
                    company_id=company_id,
                    shipment_id=shipment.id,
                    line_item_id=line.id,
                    origin_country=lane["origin"],
                    destination_country=lane["dest"],
                    hs_code=p["hs6"],
                    applicable_ftas=[
                        {"name": name, "qualified": True, "rvc": 65.0, "saving_usd": saving},
                    ],
                    recommended_fta=name,
                    mfn_duty_rate=mfn,
                    preferential_duty_rate=pref,
                    duty_saving_pct=round((mfn - pref), 4),
                    duty_saving_usd=saving,
                    qualification_met="true",
                    gpt_analysis=(
                        f"Origin {lane['origin']} to {lane['dest']}: {name} eligibility "
                        f"verified via RVC threshold (65% ≥ minimum). Estimated saving "
                        f"${saving:,.0f} per shipment."
                    ),
                    created_at=created_at + timedelta(hours=3),
                )
                session.add(fta)
                stats["ftas"] += 1

        # ---- Screening (1-2 parties per shipment) ----
        parties = [exporter, importer]
        for party in parties:
            if denied_status == "positive_match" and party == importer:
                name, res, score = SCREENING_POSITIVE[0]
                actual_name = name
            elif denied_status == "potential_match" and party == importer:
                near = random.choice(SCREENING_NEAR_MATCHES)
                actual_name = near[0]
                res = near[1]
                score = near[2]
            else:
                actual_name = party
                res, score = "clear", round(random.uniform(0.0, 0.3), 2)
            sc = DeniedPartyScreening(
                company_id=company_id,
                shipment_id=shipment.id,
                screened_by=owner.id,
                party_name=actual_name,
                party_type="importer" if party == importer else "exporter",
                party_country=lane["dest"] if party == importer else lane["origin"],
                overall_result=ScreeningResult(res),
                highest_score=score,
                lists_checked=SDN_LISTS,
                matches=[] if res == "clear" else [
                    {"list": "OFAC SDN", "score": score,
                     "candidate": actual_name + " (sanctioned)",
                     "rationale": "Phonetic + tokenised name match above threshold"},
                ],
                legal_hold_applied="true" if res == "positive_match" else "false",
                whitelisted="false",
                review_decision="approved" if res == "clear" else None,
                screened_at=created_at + timedelta(minutes=30),
            )
            session.add(sc)
            stats["screenings"] += 1

        # ---- Declaration for non-draft shipments ----
        if status not in (ShipmentStatus.DRAFT, ShipmentStatus.SCREENING):
            dec_type = (DeclarationType.CBP_ENTRY_01 if lane["dest"] == "USA"
                        else DeclarationType.EU_SAD if lane["dest"] in ("DEU", "FRA")
                        else DeclarationType.UK_C88 if lane["dest"] == "GBR"
                        else DeclarationType.CBP_ENTRY_01)
            dec_status = (DeclarationStatus.ACCEPTED if status == ShipmentStatus.CLEARED
                          else DeclarationStatus.SUBMITTED if status == ShipmentStatus.FILED
                          else DeclarationStatus.REVIEW if status == ShipmentStatus.DECLARATION_READY
                          else DeclarationStatus.DRAFT)
            cif = round(total_value * 1.06, 2)
            fob = round(total_value * 0.97, 2)
            duty_rate = 0.05
            decl = CustomsDeclaration(
                company_id=company_id,
                shipment_id=shipment.id,
                created_by=owner.id,
                declaration_type=dec_type,
                status=dec_status,
                entry_number=f"ENT-{random.randint(1_000_000, 9_999_999)}",
                port_of_entry=random.choice(["USNYC", "USLAX", "DEHAM", "GBLON", "FRMRS", "USORD"]),
                declared_value_usd=round(total_value, 2),
                cif_value_usd=cif,
                fob_value_usd=fob,
                total_duty_usd=round(cif * duty_rate, 2),
                total_tax_usd=round(cif * 0.07, 2),
                inconsistencies=[] if dec_status != DeclarationStatus.REVIEW else [
                    {"field": "consignee_name", "severity": "low",
                     "issue": "Consignee name differs from manufacturer; verify identity"},
                ],
                gpt_validation_notes=(
                    "All required fields present. Currency consistent across CIF/FOB. "
                    "Duty calculation matches HS classification anti-dumping flag = none."
                ),
                submitted_at=created_at + timedelta(days=1) if dec_status in (
                    DeclarationStatus.SUBMITTED, DeclarationStatus.ACCEPTED) else None,
                created_at=created_at + timedelta(hours=4),
            )
            session.add(decl)
            stats["declarations"] += 1

        # ---- COO for FTA-eligible lanes ----
        coo_map = {
            ("MEX", "USA"): (COOFormat.USMCA, "USMCA"),
            ("USA", "MEX"): (COOFormat.USMCA, "USMCA"),
            ("CAN", "USA"): (COOFormat.USMCA, "USMCA"),
            ("USA", "CAN"): (COOFormat.USMCA, "USMCA"),
            ("DEU", "GBR"): (COOFormat.EUR1, "EU-UK TCA"),
            ("FRA", "USA"): (COOFormat.EUR1, "EU-US Trade Pact"),
            ("ITA", "USA"): (COOFormat.EUR1, "EU-US Trade Pact"),
            ("VNM", "USA"): (COOFormat.FORM_A_GSP, "GSP"),
            ("BRA", "FRA"): (COOFormat.FORM_A_GSP, "GSP"),
            ("IND", "GBR"): (COOFormat.FORM_A_GSP, "UK-India FTA"),
            ("KOR", "DEU"): (COOFormat.BILATERAL, "EU-Korea FTA"),
            ("USA", "KOR"): (COOFormat.BILATERAL, "KORUS FTA"),
            ("JPN", "USA"): (COOFormat.BILATERAL, "US-Japan TAG"),
            ("AUS", "USA"): (COOFormat.BILATERAL, "AUSFTA"),
        }
        coo_format = coo_map.get((lane["origin"], lane["dest"]))
        if coo_format and status in (ShipmentStatus.FILED, ShipmentStatus.CLEARED,
                                     ShipmentStatus.DECLARATION_READY):
            fmt, fta_name = coo_format
            non_orig = round(total_value * random.uniform(0.10, 0.35), 2)
            rvc = round((total_value - non_orig) / total_value * 100, 1)
            saving = round(total_value * 0.06, 2)
            coo = CertificateOfOrigin(
                company_id=company_id,
                shipment_id=shipment.id,
                created_by=owner.id,
                coo_format=fmt,
                origin_criterion=OriginCriterion.REGIONAL_VALUE_CONTENT,
                fta_agreement=fta_name,
                exporter_name=exporter,
                producer_name=exporter,
                importer_name=importer,
                country_of_origin=lane["origin"],
                origin_analysis=(
                    f"AI-assisted origin analysis confirms {fta_name} eligibility. "
                    f"RVC = {rvc}% (above minimum 60-65%). Non-originating materials = "
                    f"${non_orig:,.0f}. Substantial transformation criterion satisfied."
                ),
                rvc_percentage=rvc,
                rvc_calculation={
                    "transaction_value_usd": total_value,
                    "non_originating_materials_usd": non_orig,
                    "rvc_percentage": rvc,
                    "method": "transaction-value",
                },
                preferential_duty_saving_usd=saving,
                document_content=(
                    f"CERTIFICATE OF ORIGIN — {fmt.value.upper()}\n"
                    f"Exporter: {exporter}\nImporter: {importer}\n"
                    f"Country of Origin: {lane['origin']}\nFTA: {fta_name}\n"
                    f"RVC: {rvc}%\nDuty Saving: ${saving:,.2f}\n"
                ),
                is_certified="true",
                certified_at=created_at + timedelta(hours=8),
                created_at=created_at + timedelta(hours=6),
            )
            session.add(coo)
            stats["coos"] += 1

        # ---- Documents (commercial invoice with OCR) ----
        if random.random() < 0.7:
            doc = TradeDocument(
                company_id=company_id,
                shipment_id=shipment.id,
                uploaded_by=owner.id,
                document_type=DocumentType.COMMERCIAL_INVOICE,
                filename=f"INV-{shipment.reference_number}.pdf",
                blob_url=f"blob://trade-docs/{company_id}/{shipment.id}/invoice.pdf",
                ocr_extracted={
                    "invoice_number": f"INV-{random.randint(100000, 999999)}",
                    "invoice_date": shipment.shipment_date.isoformat() if shipment.shipment_date else None,
                    "exporter_name": exporter,
                    "importer_name": importer,
                    "currency": "USD",
                    "total_value": round(total_value, 2),
                    "line_count": len(chosen),
                    "incoterms": lane["incoterms"],
                },
                ocr_confidence=round(random.uniform(0.86, 0.99), 2),
                processing_status="completed",
                created_at=created_at + timedelta(hours=0.5),
            )
            session.add(doc)
            stats["documents"] += 1
        if random.random() < 0.4:
            doc2 = TradeDocument(
                company_id=company_id,
                shipment_id=shipment.id,
                uploaded_by=owner.id,
                document_type=random.choice([DocumentType.PACKING_LIST, DocumentType.BILL_OF_LADING]),
                filename=f"PL-{shipment.reference_number}.pdf",
                processing_status="completed",
                created_at=created_at + timedelta(hours=1),
            )
            session.add(doc2)
            stats["documents"] += 1

        # ---- Voice amendment on a sizable share of active shipments ----
        active_statuses = (
            ShipmentStatus.SCREENING, ShipmentStatus.CLASSIFICATION,
            ShipmentStatus.DECLARATION_READY, ShipmentStatus.FILED, ShipmentStatus.HOLD,
            ShipmentStatus.CLEARED,
        )
        # Guarantee an amendment on every 3rd shipment so the demo has plenty to show.
        if status in active_statuses and (random.random() < 0.55 or seq % 3 == 0):
            transcripts = [
                (f"Hi, this is {exporter}. We need to correct line {random.randint(1, len(chosen))} "
                 f"on shipment {shipment.reference_number}. The country of origin should be "
                 f"updated to {lane['origin']}, and the gross weight is actually "
                 f"{round(total_weight * 1.05, 1)} kilograms, not the original figure. "
                 "Please re-run the FTA analysis once corrected.", "weight_kg"),
                (f"Hello, broker speaking. Quick amendment on {shipment.reference_number}: the HS code "
                 f"on line 1 should be {random.choice(['8471.30', '8517.12', '8523.51'])} — the "
                 "previous classification was too generic. The end-use is industrial, not consumer. "
                 "Please update the classification and confirm.", "hs_code"),
                (f"This is the compliance team. For shipment {shipment.reference_number}, "
                 f"please flag that the declared value on the commercial invoice (${round(total_value,2):,.2f}) "
                 f"matches CIF, not FOB. The carrier corrected this with us yesterday. "
                 "Update the customs declaration accordingly.", "declared_value"),
                (f"It's {exporter} again. The incoterms changed from {lane['incoterms']} to DAP — "
                 "the buyer is now covering inland transport at destination. Please refresh the "
                 "duty calculation and notify the customs broker.", "incoterms"),
                (f"Voice memo for {shipment.reference_number}. The consignee just confirmed the "
                 "port of entry has shifted from the originally-stated one to USNYC due to a vessel "
                 "diversion. No other fields change. Please refile the declaration with the new port.",
                 "port_of_entry"),
                (f"Note from logistics on {shipment.reference_number}: one of the line items "
                 "needs an ITAR licence number added. The number is TEMP-PENDING and we will "
                 "supply the real one tomorrow. Hold the customs lodgement until then.", "license_required"),
            ]
            transcript_text, target = random.choice(transcripts)
            am = ShipmentAmendment(
                shipment_id=shipment.id,
                agent_id=owner.id,
                amendment_type=random.choice(["correction", "clarification", "hs_code_revision", "value_revision"]),
                voice_file_url=f"blob://shipment-amendments/{shipment.reference_number}.m4a",
                voice_transcript=transcript_text,
                transcript_status="completed",
                target_field=target,
                provider="deepinfra",
                model="openai/whisper-large-v3",
                status="completed",
                created_at=created_at + timedelta(hours=12),
            )
            session.add(am)
            stats["amendments"] += 1

    await session.commit()
    return stats


async def main() -> None:
    print("Creating tables (if missing)…")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # --- Acme tenant -------------------------------------------------------
    acme_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    async with async_session() as session:
        await _wipe_company(session, acme_id)
        admin = await _ensure_user(
            session,
            email="demo@tradepath.ai",
            password="DemoPass1!",
            full_name="Demo Admin",
            role=UserRole.ADMIN,
            company_id=acme_id,
        )
        await _ensure_user(
            session, email="broker@tradepath.ai", password="BrokerPass1!",
            full_name="Sam Broker", role=UserRole.CUSTOMS_BROKER, company_id=acme_id,
        )
        await _ensure_user(
            session, email="compliance@tradepath.ai", password="CompliancePass1!",
            full_name="Riley Compliance", role=UserRole.TRADE_COMPLIANCE, company_id=acme_id,
        )
        start = datetime.now(timezone.utc) - timedelta(days=180)
        stats = await _seed_tenant(
            session, company_id=acme_id, owner=admin,
            shipment_count=52, start_date=start,
        )

    print("  Acme Trade Co  ->", stats)

    # --- NorthStar tenant (proves isolation) -------------------------------
    northstar_id = uuid.UUID("22222222-2222-4222-8222-222222222222")
    async with async_session() as session:
        await _wipe_company(session, northstar_id)
        owner2 = await _ensure_user(
            session, email="otherco@tradepath.ai", password="OtherCoPass1!",
            full_name="NorthStar Owner", role=UserRole.ADMIN, company_id=northstar_id,
        )
        stats2 = await _seed_tenant(
            session, company_id=northstar_id, owner=owner2,
            shipment_count=7, start_date=start,
        )
    print("  NorthStar      ->", stats2)

    print()
    print("Done. Logins:")
    print("  demo@tradepath.ai       / DemoPass1!     (Acme admin)")
    print("  broker@tradepath.ai     / BrokerPass1!   (Acme broker)")
    print("  compliance@tradepath.ai / CompliancePass1!")
    print("  otherco@tradepath.ai    / OtherCoPass1!  (NorthStar — separate tenant)")


if __name__ == "__main__":
    asyncio.run(main())
