#!/usr/bin/env python3
"""
Update Zen Village index.html with real payment methods and booking flow.
Run on server: python3 /tmp/update_booking.py
"""

import re

FILE = "/opt/fpai/apps/zen-village/frontend/public/index.html"

with open(FILE, "r") as f:
    html = f.read()

# ============================================================
# 1. Replace Credits Section with Real Payment Methods
# ============================================================
old_credits = '''    <!-- Credits Section -->
    <section class="credits-section" id="community">
        <div class="credits-container">
            <div class="credits-content">
                <div class="section-label">Pay Your Way</div>
                <h2>Credits, Currency, or Community—Your Choice</h2>
                <p>
                    Zen Village is part of a larger movement toward conscious economics. 
                    We accept traditional payments, but also offer alternative paths to paradise 
                    through our credit systems.
                </p>
                <div class="credit-types">
                    <div class="credit-type">
                        <div class="credit-icon cora">💎</div>
                        <div>
                            <h4>CORA Credits</h4>
                            <p>Earn through the Full Potential ecosystem—courses, contributions, referrals. Spend them here or across our growing network of conscious spaces.</p>
                        </div>
                    </div>
                    <div class="credit-type">
                        <div class="credit-icon zen">🌿</div>
                        <div>
                            <h4>Zen Credits</h4>
                            <p>Earn locally through work exchange, content creation, community contributions. A micro-economy that rewards presence and participation.</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="credits-visual">
                <div class="credits-card">
                    <div class="credits-card-header">
                        <h3>Sample Night Stay</h3>
                        <p>Riverside Cabin</p>
                    </div>
                    <div class="payment-options">
                        <div class="payment-option">
                            <span>💵 USD</span>
                            <span>$100/night</span>
                        </div>
                        <div class="payment-option">
                            <span>💎 CORA Credits</span>
                            <span>1,000 credits</span>
                        </div>
                        <div class="payment-option">
                            <span>🌿 Zen Credits</span>
                            <span>1,000 credits</span>
                        </div>
                        <div class="payment-option">
                            <span>🔀 Hybrid</span>
                            <span>Mix any above</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>'''

new_payments = '''    <!-- Payment Methods Section -->
    <section class="credits-section" id="payment-methods">
        <div class="credits-container">
            <div class="credits-content">
                <div class="section-label">Pay Your Way</div>
                <h2>Simple, Flexible Payment</h2>
                <p>
                    We keep it easy. Pick the payment method that works best for you.
                    A 50% deposit secures your booking — the remaining balance is due upon arrival.
                </p>
                <div class="credit-types">
                    <div class="credit-type">
                        <div class="credit-icon cora" style="font-size:1.6rem;">🅿️</div>
                        <div>
                            <h4>PayPal</h4>
                            <p>Send to: <strong style="color:#1a2e1a; user-select:all;">james@fullpotential.com</strong><br>Fast, familiar, and protected.</p>
                        </div>
                    </div>
                    <div class="credit-type">
                        <div class="credit-icon zen" style="font-size:1.6rem;">💳</div>
                        <div>
                            <h4>Venmo</h4>
                            <p>Send to: <strong style="color:#1a2e1a; user-select:all;">@James-Stinson-65</strong><br>Quick and easy from your phone.</p>
                        </div>
                    </div>
                    <div class="credit-type">
                        <div class="credit-icon cora" style="font-size:1.6rem;">₿</div>
                        <div>
                            <h4>Bitcoin (BTC)</h4>
                            <p style="word-break:break-all;">Address: <strong style="color:#1a2e1a; user-select:all; font-size:0.85rem;">13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7</strong></p>
                        </div>
                    </div>
                    <div class="credit-type">
                        <div class="credit-icon zen" style="font-size:1.6rem;">◎</div>
                        <div>
                            <h4>Solana (SOL)</h4>
                            <p style="word-break:break-all;">Address: <strong style="color:#1a2e1a; user-select:all; font-size:0.85rem;">9YfypYoQZPj5L33tFTR5Ek4LgJUTSyx8JskGehyP6tsb</strong></p>
                        </div>
                    </div>
                    <div class="credit-type">
                        <div class="credit-icon cora" style="font-size:1.6rem;">💠</div>
                        <div>
                            <h4>USDT (Ethereum Network)</h4>
                            <p style="word-break:break-all;">Address: <strong style="color:#1a2e1a; user-select:all; font-size:0.85rem;">0x2718e06abefa37947c7ea63c8746e4f14777aacb</strong></p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="credits-visual">
                <div class="credits-card">
                    <div class="credits-card-header">
                        <h3>How Booking Works</h3>
                        <p>3 simple steps</p>
                    </div>
                    <div class="payment-options">
                        <div class="payment-option">
                            <span>1️⃣ Inquire</span>
                            <span>Submit your booking request</span>
                        </div>
                        <div class="payment-option">
                            <span>2️⃣ Confirm</span>
                            <span>We confirm dates &amp; total</span>
                        </div>
                        <div class="payment-option">
                            <span>3️⃣ Deposit</span>
                            <span>50% deposit secures your stay</span>
                        </div>
                        <div class="payment-option" style="background: linear-gradient(135deg, #f0f4ec, #e8eee0); border: 1px solid #c4a35a;">
                            <span>4️⃣ Arrive</span>
                            <span>Pay remaining balance on arrival</span>
                        </div>
                    </div>
                    <div style="margin-top:1.5rem; text-align:center;">
                        <a href="#" onclick="openBookingModal('Stay'); return false;" class="btn btn-primary" style="width:100%; text-align:center;">Book Now</a>
                    </div>
                </div>
            </div>
        </div>
    </section>'''

html = html.replace(old_credits, new_payments)

# ============================================================
# 2. Update FAQ Payment Section
# ============================================================
old_faq_payment = '''                        <p>We accept:</p>
                        <ul style="margin: 0.5rem 0 0.5rem 1.5rem;">
                            <li><strong>Credit/Debit Cards</strong> (via Stripe — Visa, Mastercard, Amex)</li>
                            <li><strong>PayPal</strong></li>
                            <li><strong>Venmo</strong></li>
                            <li><strong>Cryptocurrency</strong> (BTC, ETH, USDC)</li>
                            <li><strong>Bank Transfer</strong> (for extended stays or retreats)</li>
                            <li><strong>Universal Credits (UC)</strong> — our ecosystem credit</li>
                        </ul>
                        <p>A 50% deposit is required to secure your booking. Remaining balance due upon arrival.</p>'''

new_faq_payment = '''                        <p>We accept:</p>
                        <ul style="margin: 0.5rem 0 0.5rem 1.5rem;">
                            <li><strong>PayPal</strong> — send to <code style="background:#e8eee0; padding:2px 6px; border-radius:4px; user-select:all;">james@fullpotential.com</code></li>
                            <li><strong>Venmo</strong> — send to <code style="background:#e8eee0; padding:2px 6px; border-radius:4px; user-select:all;">@James-Stinson-65</code></li>
                            <li><strong>Bitcoin (BTC)</strong> — <code style="background:#e8eee0; padding:2px 6px; border-radius:4px; font-size:0.8rem; user-select:all;">13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7</code></li>
                            <li><strong>Solana (SOL)</strong> — <code style="background:#e8eee0; padding:2px 6px; border-radius:4px; font-size:0.8rem; user-select:all;">9YfypYoQZPj5L33tFTR5Ek4LgJUTSyx8JskGehyP6tsb</code></li>
                            <li><strong>USDT (Ethereum)</strong> — <code style="background:#e8eee0; padding:2px 6px; border-radius:4px; font-size:0.8rem; user-select:all;">0x2718e06abefa37947c7ea63c8746e4f14777aacb</code></li>
                            <li><strong>Bank Transfer</strong> — available for extended stays or retreats (details provided after inquiry)</li>
                        </ul>
                        <p>A 50% deposit is required to secure your booking. Remaining balance is due upon arrival.</p>
                        <p style="margin-top:0.5rem;"><a href="#payment-methods" style="color:#c4a35a; font-weight:600;">See all payment details &amp; addresses →</a></p>'''

html = html.replace(old_faq_payment, new_faq_payment)

# ============================================================
# 3. Add payment method selector to booking modal form
# ============================================================
old_form_message = '''                        <div class="form-group">
                            <label for="message">Tell us more about your visit</label>
                            <textarea id="message" name="message" placeholder="What are you hoping to experience? Any special requests or questions?"></textarea>
                        </div>
                        
                        <input type="hidden" name="_subject" value="New Zen Village Booking Inquiry">'''

new_form_with_payment = '''                        <div class="form-row">
                            <div class="form-group">
                                <label for="phone">Phone / WhatsApp</label>
                                <input type="tel" id="phone" name="phone" placeholder="+1 555 123 4567">
                            </div>
                            <div class="form-group">
                                <label for="payment_method">Preferred Payment Method</label>
                                <select id="payment_method" name="payment_method">
                                    <option value="paypal">PayPal</option>
                                    <option value="venmo">Venmo</option>
                                    <option value="btc">Bitcoin (BTC)</option>
                                    <option value="sol">Solana (SOL)</option>
                                    <option value="usdt_eth">USDT (Ethereum)</option>
                                    <option value="bank_transfer">Bank Transfer</option>
                                    <option value="other">Other / Ask me</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="message">Tell us more about your visit</label>
                            <textarea id="message" name="message" placeholder="What are you hoping to experience? Any special requests or questions?"></textarea>
                        </div>
                        
                        <input type="hidden" name="_subject" value="New Zen Village Booking Inquiry">'''

html = html.replace(old_form_message, new_form_with_payment)

# ============================================================
# 4. Update success message to show payment instructions
# ============================================================
old_success = '''            <div id="booking-success" class="form-success" style="display: none;">
                <div class="form-success-icon">🌿</div>
                <h3>Thank You!</h3>
                <p>Your inquiry has been sent. We'll get back to you within 24 hours with availability and next steps.</p>
                <button class="btn btn-primary" onclick="closeBookingModal()">Close</button>
            </div>'''

new_success = '''            <div id="booking-success" class="form-success" style="display: none;">
                <div class="form-success-icon">🌿</div>
                <h3>Booking Request Received!</h3>
                <p>We'll confirm availability and your total within 24 hours.</p>
                <div id="payment-instructions" style="margin: 1.5rem 0; padding: 1.5rem; background: #f0f4ec; border-radius: 16px; text-align: left; border: 1px solid #c4d4b8;"></div>
                <p style="font-size: 0.9rem; opacity: 0.8; margin-top: 1rem;">Questions? WhatsApp us at <a href="https://wa.me/50670945764" style="color: #c4a35a; font-weight:600;">+506 7094 5764</a></p>
                <button class="btn btn-primary" onclick="closeBookingModal()" style="margin-top:1rem;">Close</button>
            </div>'''

html = html.replace(old_success, new_success)

# ============================================================
# 5. Update JS form submission to include payment + show instructions
# ============================================================
old_submit_js = '''        // Handle form submission
        document.getElementById('booking-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const form = this;
            const formData = new FormData(form);
            
            // Get form values
            const inquiryType = formData.get('inquiry_type');
            const name = formData.get('name');
            const email = formData.get('email');
            const dates = formData.get('dates') || 'Not specified';
            const guests = formData.get('guests');
            const message = formData.get('message') || 'No additional message';
            
            // Construct email body
            const subject = encodeURIComponent(`Zen Village ${inquiryType} Inquiry from ${name}`);
            const body = encodeURIComponent(
`New ${inquiryType} Inquiry

Name: ${name}
Email: ${email}
Inquiry Type: ${inquiryType}
Preferred Dates: ${dates}
Number of Guests: ${guests}

Message:
${message}

---
Sent from zenvillagecr.com booking form`
            );
            
            // Try Formspree first, fallback to mailto
            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                if (response.ok) {
                    document.getElementById('booking-form-container').style.display = 'none';
                    document.getElementById('booking-success').style.display = 'block';
                    form.reset();
                } else {
                    // Fallback to mailto
                    window.location.href = `mailto:james@fullpotential.com?subject=${subject}&body=${body}`;
                    document.getElementById('booking-form-container').style.display = 'none';
                    document.getElementById('booking-success').style.display = 'block';
                    form.reset();
                }
            } catch (error) {
                // Fallback to mailto
                window.location.href = `mailto:james@fullpotential.com?subject=${subject}&body=${body}`;
                document.getElementById('booking-form-container').style.display = 'none';
                document.getElementById('booking-success').style.display = 'block';
                form.reset();
            }
        });'''

new_submit_js = '''        // Payment info lookup
        const paymentInfo = {
            paypal: {
                icon: "🅿️",
                title: "PayPal",
                detail: "james@fullpotential.com",
                instruction: "Send your 50% deposit via PayPal to the address above. Include your name and dates in the payment note."
            },
            venmo: {
                icon: "💳",
                title: "Venmo",
                detail: "@James-Stinson-65",
                instruction: "Send your 50% deposit via Venmo to the handle above. Include your name and dates in the payment note."
            },
            btc: {
                icon: "₿",
                title: "Bitcoin (BTC)",
                detail: "13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7",
                instruction: "Send the BTC equivalent of your 50% deposit to the address above. Send us the transaction hash after sending."
            },
            sol: {
                icon: "◎",
                title: "Solana (SOL)",
                detail: "9YfypYoQZPj5L33tFTR5Ek4LgJUTSyx8JskGehyP6tsb",
                instruction: "Send the SOL equivalent of your 50% deposit to the address above. Send us the transaction hash after sending."
            },
            usdt_eth: {
                icon: "💠",
                title: "USDT (Ethereum Network)",
                detail: "0x2718e06abefa37947c7ea63c8746e4f14777aacb",
                instruction: "Send your USDT deposit to the Ethereum address above. Send us the transaction hash after sending."
            },
            bank_transfer: {
                icon: "🏦",
                title: "Bank Transfer",
                detail: "Details provided after confirmation",
                instruction: "We'll send you bank transfer details in our confirmation email within 24 hours."
            },
            other: {
                icon: "💬",
                title: "Other Method",
                detail: "We'll discuss options",
                instruction: "We'll reach out within 24 hours to arrange a payment method that works for you."
            }
        };

        function showPaymentInstructions(method) {
            const info = paymentInfo[method] || paymentInfo.other;
            const el = document.getElementById("payment-instructions");
            el.innerHTML = `
                <p style="font-weight:600; margin-bottom:0.75rem; color:#1a2e1a; font-size:1.05rem;">${info.icon} Payment via ${info.title}</p>
                <div style="background:white; padding:1rem; border-radius:10px; margin-bottom:0.75rem; border:1px solid #d4d4c8;">
                    <p style="font-size:0.85rem; color:#7d9a6f; margin-bottom:0.25rem;">Send to:</p>
                    <p style="font-weight:600; color:#1a2e1a; word-break:break-all; user-select:all; cursor:text; font-size:0.95rem;" onclick="navigator.clipboard.writeText('${info.detail}').then(()=>{this.style.color='#4a7c8a'; this.textContent='Copied! ✓'; setTimeout(()=>{this.style.color='#1a2e1a'; this.textContent='${info.detail}';}, 2000);})">${info.detail}</p>
                    <p style="font-size:0.8rem; color:#7d9a6f; margin-top:0.25rem;">Click to copy</p>
                </div>
                <p style="font-size:0.9rem; color:#4a6741;">${info.instruction}</p>
                <p style="font-size:0.85rem; color:#7d9a6f; margin-top:0.75rem; font-style:italic;">⏳ Wait for our confirmation email before sending payment. We'll confirm availability, your total, and the exact deposit amount.</p>
            `;
        }
        
        // Handle form submission
        document.getElementById('booking-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const form = this;
            const formData = new FormData(form);
            const paymentMethod = formData.get('payment_method') || 'paypal';
            
            const data = {
                name: formData.get('name'),
                email: formData.get('email'),
                inquiry_type: formData.get('inquiry_type'),
                dates: formData.get('dates') || 'Flexible',
                guests: formData.get('guests'),
                message: formData.get('message') || '',
                phone: formData.get('phone') || '',
                payment_method: paymentMethod,
                partner_code: getCookie ? getCookie('zv_ref') : null
            };
            
            try {
                const response = await fetch('/api/inquiries/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    document.getElementById('booking-form-container').style.display = 'none';
                    document.getElementById('booking-success').style.display = 'block';
                    showPaymentInstructions(paymentMethod);
                    form.reset();
                } else {
                    const subject = encodeURIComponent(`Zen Village ${data.inquiry_type} Inquiry from ${data.name}`);
                    const body = encodeURIComponent(`Name: ${data.name}\\nEmail: ${data.email}\\nDates: ${data.dates}\\nGuests: ${data.guests}\\nPayment: ${paymentMethod}\\nMessage: ${data.message}`);
                    window.location.href = `mailto:james@fullpotential.com?subject=${subject}&body=${body}`;
                    document.getElementById('booking-form-container').style.display = 'none';
                    document.getElementById('booking-success').style.display = 'block';
                    showPaymentInstructions(paymentMethod);
                    form.reset();
                }
            } catch (error) {
                const subject = encodeURIComponent(`Zen Village ${data.inquiry_type} Inquiry from ${data.name}`);
                const body = encodeURIComponent(`Name: ${data.name}\\nEmail: ${data.email}\\nDates: ${data.dates}\\nGuests: ${data.guests}\\nPayment: ${paymentMethod}\\nMessage: ${data.message}`);
                window.location.href = `mailto:james@fullpotential.com?subject=${subject}&body=${body}`;
                document.getElementById('booking-form-container').style.display = 'none';
                document.getElementById('booking-success').style.display = 'block';
                showPaymentInstructions(paymentMethod);
                form.reset();
            }
        });'''

html = html.replace(old_submit_js, new_submit_js)

# ============================================================
# 6. Add "Book & Pay" to navigation
# ============================================================
old_nav = '''            <li><a href="#" onclick="openBookingModal(\'Stay\'); return false;" class="nav-cta">Book Now</a></li>'''
new_nav = '''            <li><a href="/book" class="nav-cta">Book &amp; Pay</a></li>'''
html = html.replace(old_nav, new_nav)

# Write updated file
with open(FILE, "w") as f:
    f.write(html)

print("✅ index.html updated successfully")
print(f"File size: {len(html)} bytes")

# Verify changes
checks = [
    ("Payment Methods section", "id=\"payment-methods\"" in html),
    ("PayPal address", "james@fullpotential.com" in html),
    ("Venmo handle", "@James-Stinson-65" in html),
    ("BTC address", "13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7" in html),
    ("SOL address", "9YfypYoQZPj5L33tFTR5Ek4LgJUTSyx8JskGehyP6tsb" in html),
    ("USDT address", "0x2718e06abefa37947c7ea63c8746e4f14777aacb" in html),
    ("Payment method selector", 'name="payment_method"' in html),
    ("Payment instructions div", 'id="payment-instructions"' in html),
    ("Book & Pay nav link", "/book" in html),
    ("FAQ updated", "Send to:" in html or "send to" in html),
]
for name, result in checks:
    print(f"  {'✅' if result else '❌'} {name}")
