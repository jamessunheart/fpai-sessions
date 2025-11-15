#!/usr/bin/env python3
"""
Setup Stripe products and payment links for Church Guidance Funnel
Creates all pricing tiers automatically via Stripe API
"""

import stripe
import os

# Stripe API key (must be set as environment variable)
stripe.api_key = os.getenv("STRIPE_API_KEY")
if not stripe.api_key:
    raise ValueError("STRIPE_API_KEY environment variable must be set")

def create_products_and_links():
    """Create all Stripe products and payment links for the funnel"""

    products = []

    print("🛒 Creating Stripe products for Church Guidance Funnel...\n")

    # ===== TIER 2: AI FORMATION ASSISTANT =====

    # Tier 2a: Monthly Subscription ($97/month)
    print("Creating Tier 2a: AI Assistant - Monthly ($97/month)...")
    product_2a = stripe.Product.create(
        name="Church Formation AI Assistant - Monthly",
        description="Interactive AI chatbot that guides you through church formation. Generates customized Articles of Faith, Bylaws, IRS Letter 1045, Operating Procedures, and more. Monthly subscription with ongoing access.",
        metadata={
            "tier": "2a",
            "type": "subscription",
            "access_level": "ai_assistant"
        }
    )

    price_2a = stripe.Price.create(
        product=product_2a.id,
        unit_amount=9700,  # $97.00
        currency="usd",
        recurring={"interval": "month"}
    )

    link_2a = stripe.PaymentLink.create(
        line_items=[{"price": price_2a.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": "https://churchguidance.com/welcome-monthly"}
        }
    )

    products.append({
        "name": "AI Assistant - Monthly",
        "price": "$97/month",
        "product_id": product_2a.id,
        "price_id": price_2a.id,
        "payment_link": link_2a.url
    })

    print(f"✅ Created: {link_2a.url}\n")

    # Tier 2b: One-time Payment ($297)
    print("Creating Tier 2b: AI Assistant - Lifetime ($297 one-time)...")
    product_2b = stripe.Product.create(
        name="Church Formation AI Assistant - Lifetime",
        description="One-time payment for lifetime access to the AI Assistant. Generate unlimited church formation documents. Perfect for churches that want permanent access without monthly fees.",
        metadata={
            "tier": "2b",
            "type": "one_time",
            "access_level": "ai_assistant"
        }
    )

    price_2b = stripe.Price.create(
        product=product_2b.id,
        unit_amount=29700,  # $297.00
        currency="usd"
    )

    link_2b = stripe.PaymentLink.create(
        line_items=[{"price": price_2b.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": "https://churchguidance.com/welcome-lifetime"}
        }
    )

    products.append({
        "name": "AI Assistant - Lifetime",
        "price": "$297 one-time",
        "product_id": product_2b.id,
        "price_id": price_2b.id,
        "payment_link": link_2b.url
    })

    print(f"✅ Created: {link_2b.url}\n")

    # ===== TIER 3: PREMIUM PACKAGE =====

    print("Creating Tier 3: Premium Package ($997)...")
    product_3 = stripe.Product.create(
        name="Church Formation Premium Package",
        description="Everything in AI Assistant PLUS: Multi-state compliance checker, ongoing compliance reminders, automatic document updates based on legal changes, 12 months of compliance tracking, and priority AI response time.",
        metadata={
            "tier": "3",
            "type": "one_time",
            "access_level": "premium"
        }
    )

    price_3 = stripe.Price.create(
        product=product_3.id,
        unit_amount=99700,  # $997.00
        currency="usd"
    )

    link_3 = stripe.PaymentLink.create(
        line_items=[{"price": price_3.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": "https://churchguidance.com/welcome-premium"}
        }
    )

    products.append({
        "name": "Premium Package",
        "price": "$997 one-time",
        "product_id": product_3.id,
        "price_id": price_3.id,
        "payment_link": link_3.url
    })

    print(f"✅ Created: {link_3.url}\n")

    # ===== TIER 4: VIP PACKAGE =====

    print("Creating Tier 4: VIP Package ($2,997)...")
    product_4 = stripe.Product.create(
        name="Church Formation VIP Package",
        description="Everything in Premium PLUS optional human assistance. Our team provides personalized document review (30 min), answers specific questions via email/chat, and recommends professional resources. While we're not attorneys and don't provide legal advice, we offer general guidance on the formation process.",
        metadata={
            "tier": "4",
            "type": "one_time",
            "access_level": "vip"
        }
    )

    price_4 = stripe.Price.create(
        product=product_4.id,
        unit_amount=299700,  # $2,997.00
        currency="usd"
    )

    link_4 = stripe.PaymentLink.create(
        line_items=[{"price": price_4.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": "https://churchguidance.com/welcome-vip"}
        }
    )

    products.append({
        "name": "VIP Package",
        "price": "$2,997 one-time",
        "product_id": product_4.id,
        "price_id": price_4.id,
        "payment_link": link_4.url
    })

    print(f"✅ Created: {link_4.url}\n")

    # ===== SUMMARY =====

    print("=" * 70)
    print("✅ ALL STRIPE PRODUCTS CREATED SUCCESSFULLY")
    print("=" * 70)
    print()

    for product in products:
        print(f"📦 {product['name']} - {product['price']}")
        print(f"   Product ID: {product['product_id']}")
        print(f"   Price ID: {product['price_id']}")
        print(f"   Payment Link: {product['payment_link']}")
        print()

    # Save to file for reference
    with open('stripe_products.txt', 'w') as f:
        f.write("CHURCH GUIDANCE FUNNEL - STRIPE PRODUCTS\n")
        f.write("=" * 70 + "\n\n")
        for product in products:
            f.write(f"{product['name']} - {product['price']}\n")
            f.write(f"Product ID: {product['product_id']}\n")
            f.write(f"Price ID: {product['price_id']}\n")
            f.write(f"Payment Link: {product['payment_link']}\n\n")

    print("💾 Product details saved to: stripe_products.txt")

    return products

if __name__ == "__main__":
    create_products_and_links()
