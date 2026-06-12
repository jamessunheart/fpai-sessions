"""app/setup_stripe.py — idempotent Stripe product/price creator.

Run once on the server to create the two Apprentice products. Safe to re-run;
will reuse existing products by metadata.fingerprint and only create missing ones.

Usage:
    STRIPE_SECRET_KEY=sk_... python -m app.setup_stripe

Output: writes product IDs to /etc/apprentice-gateway-products.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import stripe

PRODUCTS_FILE = Path(
    os.environ.get("APPRENTICE_PRODUCTS_FILE", "/etc/apprentice-gateway-products.json")
)

FINGERPRINT_MONTHLY = "fp:apprentice:monthly:v1"
FINGERPRINT_FOUNDING = "fp:apprentice:founding:v1"
FINGERPRINT_CHARACTER_MONTHLY = "fp:character:monthly:v1"
FINGERPRINT_CHARACTER_CODESIGN = "fp:character:codesign:v1"


def _find_product_by_fingerprint(fingerprint: str) -> stripe.Product | None:
    """Search existing products for a metadata fingerprint match."""
    # List in chunks; we don't expect many products on this account
    starting_after = None
    while True:
        kwargs = {"limit": 100, "active": True}
        if starting_after:
            kwargs["starting_after"] = starting_after
        page = stripe.Product.list(**kwargs)
        for prod in page.data:
            if prod.metadata.get("fingerprint") == fingerprint:
                return prod
        if not page.has_more:
            return None
        starting_after = page.data[-1].id


def _find_price_for_product(product_id: str) -> stripe.Price | None:
    """Find any active price attached to a product."""
    prices = stripe.Price.list(product=product_id, active=True, limit=10)
    return prices.data[0] if prices.data else None


def ensure_monthly() -> tuple[str, str]:
    """Create or reuse the $97/mo recurring product. Returns (product_id, price_id)."""
    existing = _find_product_by_fingerprint(FINGERPRINT_MONTHLY)
    if existing:
        price = _find_price_for_product(existing.id)
        if price:
            print(f"[monthly] reusing existing product={existing.id} price={price.id}")
            return existing.id, price.id
        # Product exists but no price; create one
        prod = existing
    else:
        prod = stripe.Product.create(
            name="Champion Stack Apprentice",
            description=(
                "Private substrate access · brain-server account · Ember-as-coach via "
                "Telegram · weekly mirror cycle · Champion seat in the Full Potential Game · "
                "/becoming live access · voice in roadmap. $97/month recurring · "
                "30-day money-back guarantee · cancel anytime. "
                "NOT an income opportunity; see Income Disclosure at "
                "https://fullpotential.com/apprentice/ids"
            ),
            statement_descriptor="FP APPRENTICE",
            metadata={"fingerprint": FINGERPRINT_MONTHLY, "tier": "apprentice"},
        )
        print(f"[monthly] created product={prod.id}")

    price = stripe.Price.create(
        product=prod.id,
        unit_amount=9700,  # $97.00
        currency="usd",
        recurring={"interval": "month"},
        nickname="Champion Stack Apprentice — $97/mo",
        metadata={"fingerprint": FINGERPRINT_MONTHLY},
    )
    print(f"[monthly] created price={price.id}")
    return prod.id, price.id


def ensure_founding() -> tuple[str, str]:
    """Create or reuse the $497 founding one-time product. Returns (product_id, price_id)."""
    existing = _find_product_by_fingerprint(FINGERPRINT_FOUNDING)
    if existing:
        price = _find_price_for_product(existing.id)
        if price:
            print(f"[founding] reusing existing product={existing.id} price={price.id}")
            return existing.id, price.id
        prod = existing
    else:
        prod = stripe.Product.create(
            name="Champion Stack Apprentice — Founding Tier",
            description=(
                "Optional one-time founding-cohort upgrade. Cap: 30 buyers. "
                "Includes founding-cohort weekly synthesis call priority, "
                "/becoming co-author credit, founding badge on Character Card. "
                "NOT required to receive any Apprentice product benefit. "
                "30-day money-back guarantee. See Income Disclosure at "
                "https://fullpotential.com/apprentice/ids"
            ),
            statement_descriptor="FP FOUNDING",
            metadata={"fingerprint": FINGERPRINT_FOUNDING, "tier": "apprentice_founding"},
        )
        print(f"[founding] created product={prod.id}")

    price = stripe.Price.create(
        product=prod.id,
        unit_amount=49700,  # $497.00
        currency="usd",
        nickname="Champion Stack Apprentice — Founding $497 one-time",
        metadata={"fingerprint": FINGERPRINT_FOUNDING},
    )
    print(f"[founding] created price={price.id}")
    return prod.id, price.id


def ensure_character_monthly() -> tuple[str, str]:
    """Create or reuse the $2,497/mo Character recurring product."""
    existing = _find_product_by_fingerprint(FINGERPRINT_CHARACTER_MONTHLY)
    if existing:
        price = _find_price_for_product(existing.id)
        if price:
            print(f"[character-monthly] reusing existing product={existing.id} price={price.id}")
            return existing.id, price.id
        prod = existing
    else:
        prod = stripe.Product.create(
            name="Character — Full Potential",
            description=(
                "For founders, builders, and visionaries with their own Ember-class AI "
                "assistant — personalized to their work, their corpus, their vision. "
                "Includes: own identity stack · own brain-server account · own decision "
                "frameworks · own truth substrate · narrator agent · monthly 1:1 with "
                "James · founder-circle TG channel · roadmap voice. "
                "$2,497/month founding rate (locked 12 months) · 30-day money-back "
                "guarantee · cancel anytime. Founding cohort cap: 7. "
                "NOT an income opportunity; see Income Disclosure at "
                "https://fullpotential.com/character/ids"
            ),
            statement_descriptor="FP CHARACTER",
            metadata={"fingerprint": FINGERPRINT_CHARACTER_MONTHLY, "tier": "character"},
        )
        print(f"[character-monthly] created product={prod.id}")

    price = stripe.Price.create(
        product=prod.id,
        unit_amount=249700,  # $2,497.00
        currency="usd",
        recurring={"interval": "month"},
        nickname="Character — $2,497/mo founding rate",
        metadata={"fingerprint": FINGERPRINT_CHARACTER_MONTHLY},
    )
    print(f"[character-monthly] created price={price.id}")
    return prod.id, price.id


def ensure_character_codesign() -> tuple[str, str]:
    """Create or reuse the $4,997 one-time co-design fee."""
    existing = _find_product_by_fingerprint(FINGERPRINT_CHARACTER_CODESIGN)
    if existing:
        price = _find_price_for_product(existing.id)
        if price:
            print(f"[character-codesign] reusing existing product={existing.id} price={price.id}")
            return existing.id, price.id
        prod = existing
    else:
        prod = stripe.Product.create(
            name="Character — Co-Design Fee (Founding)",
            description=(
                "Optional one-time founding co-design fee. Cap: 7 buyers. "
                "Includes priority on the 90-day Character substrate-build window, "
                "co-author credit on the published Character architecture, and a "
                "founding badge on the Character Card. NOT required for any "
                "Character product benefit. Pro-rated refundable within 90 days. "
                "See Income Disclosure at https://fullpotential.com/character/ids"
            ),
            statement_descriptor="FP CHAR FOUND",
            metadata={"fingerprint": FINGERPRINT_CHARACTER_CODESIGN, "tier": "character_codesign"},
        )
        print(f"[character-codesign] created product={prod.id}")

    price = stripe.Price.create(
        product=prod.id,
        unit_amount=499700,  # $4,997.00
        currency="usd",
        nickname="Character — Co-Design $4,997 one-time",
        metadata={"fingerprint": FINGERPRINT_CHARACTER_CODESIGN},
    )
    print(f"[character-codesign] created price={price.id}")
    return prod.id, price.id


def main() -> int:
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        print("ERROR: STRIPE_SECRET_KEY not set in env", file=sys.stderr)
        return 1
    stripe.api_key = key

    monthly_prod, monthly_price = ensure_monthly()
    founding_prod, founding_price = ensure_founding()
    character_prod, character_price = ensure_character_monthly()
    codesign_prod, codesign_price = ensure_character_codesign()

    config = {
        "mode": "test" if key.startswith("sk_test_") else "live",
        "monthly": {"product_id": monthly_prod, "price_id": monthly_price, "amount": 9700},
        "founding": {"product_id": founding_prod, "price_id": founding_price, "amount": 49700},
        "character_monthly": {
            "product_id": character_prod,
            "price_id": character_price,
            "amount": 249700,
        },
        "character_codesign": {
            "product_id": codesign_prod,
            "price_id": codesign_price,
            "amount": 499700,
        },
        "founding_cap": int(os.environ.get("FOUNDING_CAP", "30")),
        "character_founding_cap": int(os.environ.get("CHARACTER_FOUNDING_CAP", "7")),
    }

    PRODUCTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRODUCTS_FILE.write_text(json.dumps(config, indent=2))
    print(f"\nWrote {PRODUCTS_FILE}:")
    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
