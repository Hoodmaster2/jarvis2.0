"""
Secure form filling with approval gates for sensitive actions.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

SENSITIVE_FIELDS = ["password", "creditcard", "cvv", "ssn", "pin", "security"]
PAYMENT_KEYWORDS = ["pay", "checkout", "purchase", "buy", "submit payment", "confirm order"]
FORM_APPROVAL_REQUIRED = ["payment", "password", "registration", "delete"]


def classify_form(form_data: dict) -> dict:
    inputs = form_data.get("inputs", [])
    field_names = [i.get("name", "").lower() for i in inputs]
    field_types = [i.get("type", "").lower() for i in inputs]

    has_password = any("password" in n for n in field_names) or "password" in field_types
    has_payment = any(k in " ".join(field_names) for k in PAYMENT_KEYWORDS)
    has_sensitive = any(k in " ".join(field_names) for k in SENSITIVE_FIELDS)
    action = form_data.get("action", "").lower()
    action_sensitive = any(k in action for k in FORM_APPROVAL_REQUIRED)

    requires_approval = has_password or has_payment or has_sensitive or action_sensitive
    return {
        "requires_approval": requires_approval,
        "reasons": [
            reason for reason, flag in [
                ("password field detected", has_password),
                ("payment field detected", has_payment),
                ("sensitive field detected", has_sensitive),
                ("sensitive action detected", action_sensitive),
            ] if flag
        ],
        "sensitive_fields": [n for n in field_names if any(k in n for k in SENSITIVE_FIELDS)],
    }


def sanitize_form_value(field_name: str, value: str) -> str:
    field_lower = field_name.lower()
    if any(k in field_lower for k in ["password", "creditcard", "cvv", "ssn"]):
        return "***"
    return value


async def fill_form_safe(page, form_data: dict, values: dict, approved: bool = False) -> dict:
    classification = classify_form(form_data)
    if classification["requires_approval"] and not approved:
        return {
            "status": "requires_approval",
            "classification": classification,
            "message": "Form requires approval before filling",
        }

    results = []
    for field in form_data.get("inputs", []):
        name = field.get("name", "")
        if name in values:
            try:
                selector = f'[name="{name}"], #{name}'
                el = page.locator(selector).first
                await el.fill(str(values[name]))
                results.append({
                    "field": name,
                    "filled": True,
                    "value": sanitize_form_value(name, str(values[name])),
                })
            except Exception as e:
                results.append({"field": name, "filled": False, "error": str(e)})
    return {"status": "filled", "results": results}


async def submit_form_safe(page, form_index: int = 0, approved: bool = False) -> dict:
    forms = await page.evaluate("""() =>
        Array.from(document.querySelectorAll('form')).map((f, i) => ({
            index: i,
            action: f.action,
            method: f.method,
        }))
    """)
    if not forms or form_index >= len(forms):
        return {"status": "error", "message": "Form not found"}

    form = forms[form_index]
    form_cls = classify_form({"action": form.get("action", ""), "inputs": []})

    if form_cls["requires_approval"] and not approved:
        return {
            "status": "requires_approval",
            "message": "Form submission requires approval",
            "form": form,
        }

    await page.evaluate(f"document.forms[{form_index}].submit()")
    return {"status": "submitted", "form": form}
