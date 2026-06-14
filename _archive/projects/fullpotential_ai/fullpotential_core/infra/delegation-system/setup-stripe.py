#!/usr/bin/env python3
"""
Automated Stripe Setup for White Rock Ministry
Creates products and payment links
"""

import stripe
import json

# Stripe API key
import os
stripe.api_key = os.getenv("STRIPE_API_KEY", "YOUR_STRIPE_API_KEY_HERE")

print("🚀 Setting up White Rock Ministry Stripe Products...")
print("=" * 60)

# Product configurations
products = [
    {
        "name": "White Rock Ministry - Basic Membership",
        "description": "90-minute consultation + trust structure guidance + treasury tools + 3 months community access",
        "price": 250000,  # $2,500 in cents
        "tier": "basic"
    },
    {
        "name": "White Rock Ministry - Premium Membership",
        "description": "Everything in Basic + personalized review + 1-year access + quarterly reviews + priority support",
        "price": 750000,  # $7,500 in cents
        "tier": "premium"
    },
    {
        "name": "White Rock Ministry - Platinum Membership",
        "description": "Everything in Premium + dedicated manager + unlimited consultations + lifetime access + 2% AUM fee",
        "price": 1500000,  # $15,000 in cents
        "tier": "platinum"
    }
]

payment_links = {}

for product_config in products:
    try:
        print(f"\n📦 Creating {product_config['tier'].upper()} tier...")
        
        # Create product
        product = stripe.Product.create(
            name=product_config["name"],
            description=product_config["description"]
        )
        
        print(f"  ✅ Product created: {product.id}")
        
        # Create price
        price = stripe.Price.create(
            product=product.id,
            unit_amount=product_config["price"],
            currency="usd"
        )
        
        print(f"  ✅ Price created: ${product_config['price']/100:,.0f}")
        
        # Create payment link
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price.id, "quantity": 1}],
            after_completion={
                "type": "hosted_confirmation",
                "hosted_confirmation": {
                    "custom_message": "Thank you for joining White Rock Ministry! Check your email for next steps including your consultation booking link."
                }
            }
        )
        
        payment_links[product_config['tier']] = payment_link.url
        
        print(f"  ✅ Payment link created: {payment_link.url}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Save payment links to file
print("\n" + "=" * 60)
print("💾 Saving payment links...")

with open('/Users/jamessunheart/Development/delegation-system/stripe-links.json', 'w') as f:
    json.dump(payment_links, f, indent=2)

print("✅ Payment links saved to: stripe-links.json")

print("\n" + "=" * 60)
print("🎉 STRIPE SETUP COMPLETE!")
print("=" * 60)
print("\n📋 Your Payment Links:\n")

for tier, link in payment_links.items():
    print(f"{tier.upper():12s}: {link}")

print("\n✅ Ready to integrate into landing page!")
