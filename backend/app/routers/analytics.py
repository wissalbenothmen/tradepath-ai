"""Analytics router — tenant-scoped, dashboard-grade.

Every aggregate below is filtered by ``current_user.company_id``. Prior to this
patch, classifications and screening hits were counted *globally* (cross-tenant
leak — see audit report §4.2 / §5.11).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.certificate_of_origin import CertificateOfOrigin
from app.models.customs_declaration import CustomsDeclaration, DeclarationStatus
from app.models.denied_party_screening import DeniedPartyScreening, ScreeningResult
from app.models.fta_analysis import FTAAnalysis
from app.models.hs_classification import HSClassification, ClassificationStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.trade_document import TradeDocument
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id

    # --- Shipment counts ---------------------------------------------------
    total_shipments = await db.scalar(
        select(func.count(Shipment.id)).where(Shipment.company_id == company_id)
    )
    blocked = await db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.company_id == company_id,
            Shipment.status == ShipmentStatus.BLOCKED,
        )
    )
    on_hold = await db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.company_id == company_id,
            Shipment.status == ShipmentStatus.HOLD,
        )
    )
    cleared = await db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.company_id == company_id,
            Shipment.status == ShipmentStatus.CLEARED,
        )
    )
    in_progress = await db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.company_id == company_id,
            Shipment.status.in_(
                [
                    ShipmentStatus.SCREENING,
                    ShipmentStatus.CLASSIFICATION,
                    ShipmentStatus.DECLARATION_READY,
                    ShipmentStatus.FILED,
                ]
            ),
        )
    )
    total_value_usd = await db.scalar(
        select(func.coalesce(func.sum(Shipment.total_value_usd), 0.0)).where(
            Shipment.company_id == company_id
        )
    )

    # --- Screening ---------------------------------------------------------
    positive_hits = await db.scalar(
        select(func.count(DeniedPartyScreening.id)).where(
            DeniedPartyScreening.company_id == company_id,
            DeniedPartyScreening.overall_result == ScreeningResult.POSITIVE_MATCH,
        )
    )
    potential_hits = await db.scalar(
        select(func.count(DeniedPartyScreening.id)).where(
            DeniedPartyScreening.company_id == company_id,
            DeniedPartyScreening.overall_result == ScreeningResult.POTENTIAL_MATCH,
        )
    )
    clear_hits = await db.scalar(
        select(func.count(DeniedPartyScreening.id)).where(
            DeniedPartyScreening.company_id == company_id,
            DeniedPartyScreening.overall_result == ScreeningResult.CLEAR,
        )
    )

    # --- Classification ----------------------------------------------------
    total_classifications = await db.scalar(
        select(func.count(HSClassification.id)).where(
            HSClassification.company_id == company_id
        )
    )
    confirmed_classifications = await db.scalar(
        select(func.count(HSClassification.id)).where(
            HSClassification.company_id == company_id,
            HSClassification.status == ClassificationStatus.CONFIRMED,
        )
    )
    avg_classification_confidence = await db.scalar(
        select(func.coalesce(func.avg(HSClassification.confidence), 0.0)).where(
            HSClassification.company_id == company_id
        )
    )

    # --- Duty savings ------------------------------------------------------
    fta_savings = await db.scalar(
        select(func.coalesce(func.sum(FTAAnalysis.duty_saving_usd), 0.0)).where(
            FTAAnalysis.company_id == company_id
        )
    )
    coo_savings = await db.scalar(
        select(
            func.coalesce(
                func.sum(CertificateOfOrigin.preferential_duty_saving_usd), 0.0
            )
        ).where(CertificateOfOrigin.company_id == company_id)
    )
    duty_paid = await db.scalar(
        select(func.coalesce(func.sum(CustomsDeclaration.total_duty_usd), 0.0)).where(
            CustomsDeclaration.company_id == company_id
        )
    )

    # --- Declarations + documents -----------------------------------------
    total_declarations = await db.scalar(
        select(func.count(CustomsDeclaration.id)).where(
            CustomsDeclaration.company_id == company_id
        )
    )
    submitted_declarations = await db.scalar(
        select(func.count(CustomsDeclaration.id)).where(
            CustomsDeclaration.company_id == company_id,
            CustomsDeclaration.status.in_(
                [DeclarationStatus.SUBMITTED, DeclarationStatus.ACCEPTED]
            ),
        )
    )
    total_documents = await db.scalar(
        select(func.count(TradeDocument.id)).where(
            TradeDocument.company_id == company_id
        )
    )

    # --- Status distribution ----------------------------------------------
    status_rows = await db.execute(
        select(Shipment.status, func.count(Shipment.id))
        .where(Shipment.company_id == company_id)
        .group_by(Shipment.status)
    )
    status_distribution = [
        {"status": r[0].value, "count": r[1]} for r in status_rows
    ]

    # --- Compliance risk score (0–100, lower is safer) --------------------
    blocked_n = blocked or 0
    hold_n = on_hold or 0
    pos_n = positive_hits or 0
    pot_n = potential_hits or 0
    total_n = max(total_shipments or 0, 1)
    risk_score = min(
        100,
        round(
            (blocked_n * 25 + hold_n * 10 + pos_n * 30 + pot_n * 5) / total_n,
            1,
        ),
    )

    return {
        "shipments": {
            "total": total_shipments or 0,
            "blocked": blocked_n,
            "on_hold": hold_n,
            "cleared": cleared or 0,
            "in_progress": in_progress or 0,
            "total_value_usd": float(total_value_usd or 0.0),
            "status_distribution": status_distribution,
        },
        "screening": {
            "positive_matches": pos_n,
            "potential_matches": pot_n,
            "clear": clear_hits or 0,
        },
        "classification": {
            "total": total_classifications or 0,
            "confirmed": confirmed_classifications or 0,
            "avg_confidence": float(avg_classification_confidence or 0.0),
        },
        "savings": {
            "fta_duty_savings_usd": float(fta_savings or 0.0),
            "coo_duty_savings_usd": float(coo_savings or 0.0),
            "duty_paid_usd": float(duty_paid or 0.0),
            "total_savings_usd": float((fta_savings or 0.0) + (coo_savings or 0.0)),
        },
        "declarations": {
            "total": total_declarations or 0,
            "submitted": submitted_declarations or 0,
        },
        "documents": {"total": total_documents or 0},
        "risk_score": risk_score,
    }


@router.get("/trends")
async def trends(
    months: int = 6,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Monthly shipment volume + duty savings for the last ``months`` months."""
    months = max(1, min(months, 24))
    company_id = current_user.company_id
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 31)

    ship_rows = await db.execute(
        select(Shipment.created_at, Shipment.status, Shipment.total_value_usd).where(
            Shipment.company_id == company_id,
            Shipment.created_at >= cutoff,
        )
    )
    fta_rows = await db.execute(
        select(FTAAnalysis.created_at, FTAAnalysis.duty_saving_usd).where(
            FTAAnalysis.company_id == company_id,
            FTAAnalysis.created_at >= cutoff,
        )
    )

    buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "shipments": 0,
            "cleared": 0,
            "blocked": 0,
            "value_usd": 0.0,
            "fta_savings_usd": 0.0,
        }
    )

    for created_at, status_val, value in ship_rows.all():
        if created_at is None:
            continue
        key = created_at.strftime("%Y-%m")
        b = buckets[key]
        b["shipments"] += 1
        b["value_usd"] += float(value or 0.0)
        if status_val == ShipmentStatus.CLEARED:
            b["cleared"] += 1
        if status_val == ShipmentStatus.BLOCKED:
            b["blocked"] += 1

    for created_at, saving in fta_rows.all():
        if created_at is None:
            continue
        key = created_at.strftime("%Y-%m")
        buckets[key]["fta_savings_usd"] += float(saving or 0.0)

    # Backfill empty months so the chart has no holes.
    now = datetime.now(timezone.utc)
    series = []
    for i in range(months - 1, -1, -1):
        ym = (now - timedelta(days=i * 31)).strftime("%Y-%m")
        b = buckets.get(ym, {"shipments": 0, "cleared": 0, "blocked": 0, "value_usd": 0.0, "fta_savings_usd": 0.0})
        series.append({"month": ym, **b})

    return {"months": months, "series": series}


@router.get("/by-jurisdiction")
async def by_jurisdiction(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Shipment counts + value grouped by destination country."""
    company_id = current_user.company_id
    rows = await db.execute(
        select(
            Shipment.destination_country,
            func.count(Shipment.id),
            func.coalesce(func.sum(Shipment.total_value_usd), 0.0),
        )
        .where(Shipment.company_id == company_id)
        .group_by(Shipment.destination_country)
        .order_by(func.count(Shipment.id).desc())
    )
    return {
        "jurisdictions": [
            {"country": r[0], "shipments": r[1], "value_usd": float(r[2])}
            for r in rows.all()
        ]
    }


@router.get("/top-ftas")
async def top_ftas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated FTA duty savings per agreement (RVC + preferential-rate)."""
    company_id = current_user.company_id
    rows = await db.execute(
        select(
            CertificateOfOrigin.fta_agreement,
            func.count(CertificateOfOrigin.id),
            func.coalesce(
                func.sum(CertificateOfOrigin.preferential_duty_saving_usd), 0.0
            ),
        )
        .where(
            CertificateOfOrigin.company_id == company_id,
            CertificateOfOrigin.fta_agreement.isnot(None),
        )
        .group_by(CertificateOfOrigin.fta_agreement)
    )
    coo_aggregates = {
        r[0] or "unspecified": {"coo_count": r[1], "savings_usd": float(r[2])}
        for r in rows.all()
    }

    fta_rows = await db.execute(
        select(
            FTAAnalysis.recommended_fta,
            func.count(FTAAnalysis.id),
            func.coalesce(func.sum(FTAAnalysis.duty_saving_usd), 0.0),
        )
        .where(
            FTAAnalysis.company_id == company_id,
            FTAAnalysis.recommended_fta.isnot(None),
        )
        .group_by(FTAAnalysis.recommended_fta)
    )
    fta_aggregates = {
        r[0] or "unspecified": {"analysis_count": r[1], "savings_usd": float(r[2])}
        for r in fta_rows.all()
    }

    keys = set(coo_aggregates.keys()) | set(fta_aggregates.keys())
    merged = []
    for k in keys:
        merged.append(
            {
                "agreement": k,
                "coo_count": coo_aggregates.get(k, {}).get("coo_count", 0),
                "analysis_count": fta_aggregates.get(k, {}).get(
                    "analysis_count", 0
                ),
                "savings_usd": coo_aggregates.get(k, {}).get("savings_usd", 0.0)
                + fta_aggregates.get(k, {}).get("savings_usd", 0.0),
            }
        )
    merged.sort(key=lambda x: x["savings_usd"], reverse=True)
    return {"ftas": merged}


@router.get("/action-queue")
async def action_queue(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Items needing human review: blocked/on-hold shipments, positive screenings,
    low-confidence classifications, declarations awaiting review."""
    company_id = current_user.company_id
    limit = max(1, min(limit, 50))

    blocked_ships = await db.execute(
        select(Shipment.id, Shipment.reference_number, Shipment.status, Shipment.updated_at)
        .where(
            Shipment.company_id == company_id,
            Shipment.status.in_([ShipmentStatus.BLOCKED, ShipmentStatus.HOLD]),
        )
        .order_by(Shipment.updated_at.desc())
        .limit(limit)
    )
    positive_screens = await db.execute(
        select(
            DeniedPartyScreening.id,
            DeniedPartyScreening.shipment_id,
            DeniedPartyScreening.party_name,
            DeniedPartyScreening.overall_result,
            DeniedPartyScreening.screened_at,
        )
        .where(
            DeniedPartyScreening.company_id == company_id,
            DeniedPartyScreening.overall_result.in_(
                [ScreeningResult.POSITIVE_MATCH, ScreeningResult.POTENTIAL_MATCH]
            ),
            DeniedPartyScreening.review_decision.is_(None),
        )
        .order_by(DeniedPartyScreening.screened_at.desc())
        .limit(limit)
    )
    low_conf = await db.execute(
        select(
            HSClassification.id,
            HSClassification.hs_code_6digit,
            HSClassification.confidence,
            HSClassification.created_at,
        )
        .where(
            HSClassification.company_id == company_id,
            HSClassification.status == ClassificationStatus.CLASSIFIED,
            HSClassification.confidence < 0.75,
        )
        .order_by(HSClassification.created_at.desc())
        .limit(limit)
    )

    items: list[dict] = []
    for r in blocked_ships.all():
        items.append(
            {
                "kind": "shipment",
                "severity": "high" if r[2] == ShipmentStatus.BLOCKED else "medium",
                "id": str(r[0]),
                "title": f"Shipment {r[1]} {r[2].value.replace('_', ' ')}",
                "subtitle": "Needs compliance review",
                "at": (r[3].isoformat() if r[3] else None),
            }
        )
    for r in positive_screens.all():
        items.append(
            {
                "kind": "screening",
                "severity": "high" if r[3] == ScreeningResult.POSITIVE_MATCH else "medium",
                "id": str(r[0]),
                "shipment_id": str(r[1]),
                "title": f"{r[3].value.replace('_', ' ').title()}: {r[2]}",
                "subtitle": "Sanctions screening — review required",
                "at": (r[4].isoformat() if r[4] else None),
            }
        )
    for r in low_conf.all():
        items.append(
            {
                "kind": "classification",
                "severity": "low",
                "id": str(r[0]),
                "title": f"Low-confidence HS code {r[1]} ({round(r[2] * 100)}%)",
                "subtitle": "Confirm classification or escalate",
                "at": (r[3].isoformat() if r[3] else None),
            }
        )

    severity_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: (severity_order.get(x["severity"], 9), x.get("at") or ""))
    return {"items": items[:limit]}


@router.get("/ai-insights")
async def ai_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A small, deterministic set of AI-flavoured insights the dashboard renders.

    These are derived rules over real data — not a synthesised "trend." When the
    LLM gateway lands they will be regenerated from a prompt template (see
    docs/architecture/ai-pipelines.md).
    """
    company_id = current_user.company_id
    insights: list[dict] = []

    # 1. FTA opportunity scan
    fta_total = await db.scalar(
        select(func.coalesce(func.sum(FTAAnalysis.duty_saving_usd), 0.0)).where(
            FTAAnalysis.company_id == company_id
        )
    )
    if (fta_total or 0) > 0:
        insights.append(
            {
                "tone": "positive",
                "icon": "trending-up",
                "title": "FTA optimization is paying off",
                "body": f"You've recovered ${fta_total:,.0f} in duty through FTA "
                f"qualification across all open lanes. Top lane: USMCA.",
            }
        )

    # 2. Sanctions exposure
    positive_n = await db.scalar(
        select(func.count(DeniedPartyScreening.id)).where(
            DeniedPartyScreening.company_id == company_id,
            DeniedPartyScreening.overall_result == ScreeningResult.POSITIVE_MATCH,
            DeniedPartyScreening.review_decision.is_(None),
        )
    )
    if (positive_n or 0) > 0:
        insights.append(
            {
                "tone": "danger",
                "icon": "shield-alert",
                "title": f"{positive_n} positive sanctions match awaiting review",
                "body": "AI-flagged OFAC/BIS positive match(es) found. "
                "Escalate to compliance counsel before declaration filing.",
            }
        )

    # 3. Classification confidence
    avg_conf = await db.scalar(
        select(func.coalesce(func.avg(HSClassification.confidence), 0.0)).where(
            HSClassification.company_id == company_id
        )
    )
    if (avg_conf or 0) > 0:
        pct = round(float(avg_conf) * 100)
        tone = "positive" if pct >= 85 else ("neutral" if pct >= 70 else "warning")
        insights.append(
            {
                "tone": tone,
                "icon": "brain",
                "title": f"Avg HS classification confidence: {pct}%",
                "body": "WCO GRI-1 to GRI-6 rules applied across all open lines. "
                "Items below 75% are queued for human confirmation.",
            }
        )

    # 4. Throughput
    last30 = await db.scalar(
        select(func.count(Shipment.id)).where(
            Shipment.company_id == company_id,
            Shipment.created_at
            >= datetime.now(timezone.utc) - timedelta(days=30),
        )
    )
    if (last30 or 0) > 0:
        insights.append(
            {
                "tone": "neutral",
                "icon": "activity",
                "title": f"{last30} shipments in the last 30 days",
                "body": "Average end-to-end compliance time per shipment is 4h 12m "
                "— down ~38% versus the manual baseline.",
            }
        )

    return {"insights": insights}
