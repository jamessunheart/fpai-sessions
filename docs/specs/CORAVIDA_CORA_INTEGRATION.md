# Coravida Cora Token Integration Specification

**Version:** 1.0  
**Created:** November 30, 2025

---

## Overview

This document specifies how Coravida.com integrates with the Cora token ecosystem via the FP Credits Gateway to enable token-based payments for wellness experiences.

---

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Coravida.com  │ ───► │  FP Credits      │ ───► │  Cora Treasury  │
│   (WordPress)   │      │  Gateway :8765   │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
        │                        │
        │                        │
        ▼                        ▼
┌─────────────────┐      ┌──────────────────┐
│  User Wallet    │      │  Exchange Rates  │
│  (Cora Balance) │      │  (1 UC = $1 USD) │
└─────────────────┘      └──────────────────┘
```

---

## API Endpoints

### FP Credits Gateway (Main Server: 198.54.123.234:8765)

#### Get User Balance
```http
GET /api/balance/{user_id}
Authorization: Bearer {api_key}

Response:
{
  "user_id": "user_123",
  "balance": {
    "cora": 500.00,
    "usd_equivalent": 500.00
  },
  "last_updated": "2025-11-30T12:00:00Z"
}
```

#### Get Exchange Rate
```http
GET /api/exchange-rates

Response:
{
  "UC": 1.00,
  "CORA": 1.00,
  "anchor_discount": 0.17,
  "phase": "anchor"
}
```

#### Process Payment
```http
POST /api/transactions/pay
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "user_id": "user_123",
  "amount_cora": 250.00,
  "amount_usd": 0.00,
  "merchant_id": "coravida",
  "order_id": "booking_456",
  "description": "Sunrise Yoga Retreat - 3 nights",
  "metadata": {
    "experience_id": "exp_789",
    "check_in": "2025-12-15",
    "check_out": "2025-12-18"
  }
}

Response:
{
  "transaction_id": "txn_abc123",
  "status": "completed",
  "amount_charged": {
    "cora": 250.00,
    "usd": 0.00
  },
  "discount_applied": 42.50,
  "new_balance": 250.00,
  "timestamp": "2025-11-30T12:00:00Z"
}
```

#### Refund Transaction
```http
POST /api/transactions/refund
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "transaction_id": "txn_abc123",
  "amount": 250.00,
  "reason": "Cancellation within policy"
}
```

---

## Payment Flows

### Flow 1: 100% Cora Payment (17% Discount)

```
1. User selects experience ($299/night × 3 = $897)
2. User clicks "Pay with Cora"
3. System checks Cora balance via GET /api/balance
4. If balance >= 744.51 (897 × 0.83):
   - Display: "Pay 744.51 CORA (Save $152.49!)"
5. User confirms payment
6. POST /api/transactions/pay with amount_cora: 744.51
7. Booking confirmed
8. User receives confirmation + receipt
```

### Flow 2: Hybrid Payment (Partial Cora + USD)

```
1. User selects experience ($897 total)
2. User has 400 CORA balance
3. System calculates:
   - CORA portion: 400 CORA = $481.93 value (with 17% bonus)
   - USD portion: $897 - $481.93 = $415.07
4. Display: "Pay 400 CORA + $415.07 USD"
5. User confirms
6. POST /api/transactions/pay with amount_cora: 400, amount_usd: 415.07
7. Redirect to Stripe for USD portion
8. Booking confirmed after both complete
```

### Flow 3: USD Only (Earn Cora Back)

```
1. User selects experience ($897 total)
2. User pays with credit card via Stripe
3. After successful payment:
   - User earns 5% back in CORA (44.85 CORA)
4. POST /api/transactions/earn with amount: 44.85
5. User notified: "You earned 44.85 CORA!"
```

---

## WordPress Plugin Structure

### Plugin: `coravida-cora-payments`

```
wp-content/plugins/coravida-cora-payments/
├── coravida-cora-payments.php      # Main plugin file
├── includes/
│   ├── class-cora-api.php          # API client
│   ├── class-cora-gateway.php      # WooCommerce gateway
│   ├── class-cora-shortcodes.php   # Display shortcodes
│   └── class-cora-admin.php        # Admin settings
├── assets/
│   ├── css/
│   │   └── cora-checkout.css       # Checkout styling
│   └── js/
│       └── cora-checkout.js        # Balance check, payment
└── templates/
    ├── checkout-cora-option.php    # Cora payment option
    ├── balance-display.php         # User balance widget
    └── savings-badge.php           # Discount badge
```

### Key Plugin Functions

```php
<?php
// Get user's Cora balance
function coravida_get_cora_balance($user_id) {
    $api = new Cora_API();
    return $api->get_balance($user_id);
}

// Calculate Cora price with discount
function coravida_calculate_cora_price($usd_amount) {
    $discount_rate = 0.17; // 17% anchor discount
    return $usd_amount * (1 - $discount_rate);
}

// Display Cora savings badge
function coravida_savings_badge($usd_price) {
    $cora_price = coravida_calculate_cora_price($usd_price);
    $savings = $usd_price - $cora_price;
    
    return sprintf(
        '<div class="cora-badge">
            <span class="cora-icon">🪙</span>
            Pay %s CORA - Save $%.2f!
        </div>',
        number_format($cora_price, 2),
        $savings
    );
}
```

---

## Shortcodes

### Display User Balance
```
[cora_balance]
```
Output: "Your Cora Balance: 500.00 🪙"

### Display Cora Price
```
[cora_price amount="299"]
```
Output: "Pay with Cora: 248.17 🪙 (Save $50.83!)"

### Cora Checkout Button
```
[cora_checkout product_id="123"]
```
Output: Button that initiates Cora payment flow

---

## Security Requirements

### API Authentication

1. **API Key Storage**: Store in wp-config.php, never in database
   ```php
   define('CORAVIDA_CORA_API_KEY', 'sk_live_xxx');
   define('CORAVIDA_CORA_API_URL', 'https://fullpotential.ai/services/credits');
   ```

2. **Request Signing**: HMAC-SHA256 signature on all requests
   ```php
   $signature = hash_hmac('sha256', $payload, $api_secret);
   ```

3. **SSL Only**: All API calls over HTTPS

### User Authentication

1. WordPress user must be logged in for Cora payments
2. Cora wallet linked to WordPress user ID
3. Email verification required for first Cora transaction

---

## Error Handling

| Error Code | Description | User Message |
|------------|-------------|--------------|
| `INSUFFICIENT_BALANCE` | Not enough CORA | "You need X more CORA for this purchase" |
| `WALLET_NOT_LINKED` | No wallet connected | "Please connect your Cora wallet" |
| `TRANSACTION_FAILED` | Payment processing error | "Payment failed. Please try again." |
| `RATE_LIMIT` | Too many requests | "Please wait a moment and try again" |
| `MAINTENANCE` | System maintenance | "Cora payments temporarily unavailable" |

---

## Webhook Events

### Inbound Webhooks (from FP Credits Gateway)

```http
POST /wp-json/coravida/v1/webhooks/cora
Content-Type: application/json
X-Cora-Signature: {hmac_signature}

{
  "event": "transaction.completed",
  "data": {
    "transaction_id": "txn_abc123",
    "user_id": "user_123",
    "amount": 250.00,
    "order_id": "booking_456"
  }
}
```

### Webhook Events to Handle

| Event | Action |
|-------|--------|
| `transaction.completed` | Confirm booking |
| `transaction.failed` | Cancel pending booking |
| `transaction.refunded` | Process refund |
| `balance.updated` | Refresh user balance cache |

---

## Testing

### Test Credentials

```
API URL: https://fullpotential.ai/services/credits/api
Test API Key: sk_test_coravida_xxx
Test User ID: test_user_coravida
Test Balance: 10000.00 CORA
```

### Test Scenarios

1. ✅ Successful 100% Cora payment
2. ✅ Successful hybrid payment
3. ✅ Insufficient balance handling
4. ✅ Wallet not linked handling
5. ✅ Refund processing
6. ✅ Webhook verification

---

## Implementation Checklist

- [ ] Create WordPress plugin skeleton
- [ ] Implement Cora API client class
- [ ] Create WooCommerce payment gateway
- [ ] Build checkout UI components
- [ ] Add balance display widget
- [ ] Implement webhook handlers
- [ ] Add admin settings page
- [ ] Write unit tests
- [ ] Security audit
- [ ] Production deployment

---

## Related Documents

- [CORAVIDA_WEBSITE_SPEC.md](./CORAVIDA_WEBSITE_SPEC.md)
- [UNIVERSAL_CREDITS_PROTOCOL.md](../../docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md)
- [FP Credits Gateway API](../../SERVICES/fp-credits-gateway/)

























