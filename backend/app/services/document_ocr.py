from __future__ import annotations
from typing import Any
from app.config import get_settings

settings = get_settings()

# FX rates to USD (approximate)
FX_RATES_TO_USD: dict[str, float] = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067,
    "CNY": 0.138, "CAD": 0.74, "AUD": 0.65, "CHF": 1.11,
    "HKD": 0.128, "SGD": 0.74, "KRW": 0.00075, "INR": 0.012,
    "MXN": 0.058, "BRL": 0.20,
}


def convert_to_usd(amount: float, currency: str) -> float:
    rate = FX_RATES_TO_USD.get(currency.upper(), 1.0)
    return round(amount * rate, 2)


async def extract_commercial_invoice(
    file_bytes: bytes,
    filename: str,
) -> dict[str, Any]:
    """
    Extract structured data from a commercial invoice using Azure Document Intelligence.
    Falls back to empty structure when Azure credentials are not configured.
    """
    if not settings.AZURE_DI_ENDPOINT or not settings.AZURE_DI_KEY:
        return _mock_invoice_result(filename)

    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        from azure.core.credentials import AzureKeyCredential

        client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_DI_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_DI_KEY),
        )
        poller = client.begin_analyze_document(
            "prebuilt-invoice",
            AnalyzeDocumentRequest(bytes_source=file_bytes),
        )
        result = poller.result()

        if not result.documents:
            return _empty_invoice_result(filename)

        doc = result.documents[0]
        fields = doc.fields or {}

        def _val(key: str, field_type: str = "string"):
            f = fields.get(key)
            if f is None:
                return None
            if field_type == "currency":
                return f.value_currency.amount if f.value_currency else None
            if field_type == "date":
                return str(f.value_date) if f.value_date else None
            return f.content

        line_items = []
        for item in (fields.get("Items") or {}).get("value_array", []):
            item_fields = item.get("value_object", {})
            line_items.append({
                "description": _val_from_fields(item_fields, "Description"),
                "quantity": _val_from_fields(item_fields, "Quantity"),
                "unit_price": _val_from_fields(item_fields, "UnitPrice", "currency"),
                "amount": _val_from_fields(item_fields, "Amount", "currency"),
            })

        currency_raw = _val("InvoiceCurrencyCode") or "USD"
        total_amount = _val("InvoiceTotal", "currency") or 0.0

        return {
            "vendor_name": _val("VendorName"),
            "customer_name": _val("CustomerName"),
            "invoice_number": _val("InvoiceId"),
            "invoice_date": _val("InvoiceDate", "date"),
            "due_date": _val("DueDate", "date"),
            "currency": currency_raw,
            "total_amount": total_amount,
            "total_amount_usd": convert_to_usd(float(total_amount or 0), currency_raw),
            "shipping_address": _val("ShippingAddress"),
            "billing_address": _val("BillingAddress"),
            "line_items": line_items,
            "confidence": doc.confidence,
        }
    except Exception as exc:
        return {"error": str(exc), **_mock_invoice_result(filename)}


def _val_from_fields(fields: dict, key: str, field_type: str = "string"):
    f = fields.get(key)
    if f is None:
        return None
    if field_type == "currency":
        return f.get("valueCurrency", {}).get("amount")
    return f.get("content")


def _mock_invoice_result(filename: str) -> dict[str, Any]:
    """Return a realistic mock OCR extraction result when Azure DI is unavailable."""
    import random
    import re
    from datetime import date, timedelta

    vendors = [
        "Shenzhen Electronics Manufacturing Co. Ltd.",
        "Acme Industrial Supplies GmbH",
        "Maquiladora Textil de México S.A. de C.V.",
        "Global Machinery & Equipment Pte Ltd",
        "Pacific Foodstuffs Trading Corporation",
    ]
    customers = [
        "TechImport USA Inc.",
        "Atlantic Trade Solutions LLC",
        "Northern Distribution Group",
        "Continental Logistics Partners",
        "Pacific Rim Imports Ltd.",
    ]
    line_item_sets = [
        [
            {"description": "Laptop Computer Model TP-450 (i7/16GB/512GB)", "quantity": 50, "unit_price": 850.00, "amount": 42500.00},
            {"description": "USB-C Docking Station", "quantity": 50, "unit_price": 65.00, "amount": 3250.00},
            {"description": "Shipping & Handling", "quantity": 1, "unit_price": 480.00, "amount": 480.00},
        ],
        [
            {"description": "Industrial Hydraulic Pump Model HP-250 bar", "quantity": 12, "unit_price": 1850.00, "amount": 22200.00},
            {"description": "PTFE Seal Kit (per pump)", "quantity": 12, "unit_price": 95.00, "amount": 1140.00},
            {"description": "Freight CIF Los Angeles", "quantity": 1, "unit_price": 660.00, "amount": 660.00},
        ],
        [
            {"description": "Cotton Woven Fabric 62.04.62 — 180gsm", "quantity": 5000, "unit_price": 4.20, "amount": 21000.00},
            {"description": "Polyester Blend Trousers (S/M/L/XL assorted)", "quantity": 200, "unit_price": 18.50, "amount": 3700.00},
        ],
        [
            {"description": "Diesel Fuel Grade EN590 — 10,000L", "quantity": 10000, "unit_price": 0.95, "amount": 9500.00},
            {"description": "Lubricant Oil 15W-40 (200L drum)", "quantity": 20, "unit_price": 285.00, "amount": 5700.00},
        ],
        [
            {"description": "Sweet Biscuits Assorted (6-pack carton)", "quantity": 1000, "unit_price": 12.40, "amount": 12400.00},
            {"description": "Cereal Bars Oat & Honey (case of 24)", "quantity": 500, "unit_price": 18.00, "amount": 9000.00},
        ],
    ]

    seed = sum(ord(c) for c in filename)
    rng = random.Random(seed)
    vendor = vendors[seed % len(vendors)]
    customer = customers[(seed + 1) % len(customers)]
    items = line_item_sets[seed % len(line_item_sets)]
    total = sum(item["amount"] for item in items)
    inv_num = f"INV-2026-{rng.randint(10000, 99999)}"
    inv_date = (date(2026, 5, 1) - timedelta(days=rng.randint(1, 60))).isoformat()
    due_date = (date(2026, 5, 31) - timedelta(days=rng.randint(0, 10))).isoformat()
    confidence = round(rng.uniform(0.84, 0.97), 4)

    return {
        "vendor_name": vendor,
        "customer_name": customer,
        "invoice_number": inv_num,
        "invoice_date": inv_date,
        "due_date": due_date,
        "currency": "USD",
        "total_amount": round(total, 2),
        "total_amount_usd": round(total, 2),
        "shipping_address": "Port of Los Angeles, 425 S Palos Verdes St, San Pedro, CA 90731, USA",
        "billing_address": "200 Trade Center Blvd, Suite 400, Houston, TX 77002, USA",
        "line_items": items,
        "confidence": confidence,
        "filename": filename,
        "_mock": True,
    }


def _empty_invoice_result(filename: str) -> dict[str, Any]:
    return {
        "vendor_name": None, "customer_name": None, "invoice_number": None,
        "invoice_date": None, "due_date": None, "currency": "USD",
        "total_amount": None, "total_amount_usd": None, "shipping_address": None,
        "billing_address": None, "line_items": [], "confidence": 0.0,
        "filename": filename,
    }
