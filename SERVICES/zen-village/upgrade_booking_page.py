#!/usr/bin/env python3
"""
Upgrade booking.html with:
1. FullCalendar.js availability calendar
2. Dynamic accommodation dropdown from API
3. Real booking API integration
4. Availability checking before submission
"""

BOOKING_FILE = "/opt/fpai/apps/zen-village/frontend/public/booking.html"

with open(BOOKING_FILE, 'r') as f:
    html = f.read()

# ── 1. Add FullCalendar CSS in <head> ──
fc_css = '''    <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css" rel="stylesheet">'''

if 'fullcalendar' not in html:
    html = html.replace(
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        fc_css + '\n    <link rel="preconnect" href="https://fonts.googleapis.com">'
    )
    print("Added FullCalendar CSS")

# ── 2. Add calendar CSS styles ──
calendar_css = '''
        /* Availability Calendar */
        .calendar-section {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--zen-mist);
        }
        .calendar-section h3 {
            font-family: var(--font-display);
            font-size: 1.3rem;
            margin-bottom: 0.5rem;
            color: var(--zen-forest-deep);
        }
        .calendar-section .subtitle {
            font-size: 0.85rem;
            color: var(--zen-moss);
            margin-bottom: 1rem;
        }
        #availability-calendar {
            min-height: 350px;
        }
        #availability-calendar .fc-daygrid-day.booked-date {
            background: rgba(220, 53, 69, 0.12) !important;
        }
        #availability-calendar .fc-daygrid-day.booked-date .fc-daygrid-day-number {
            color: #dc3545;
            text-decoration: line-through;
            opacity: 0.6;
        }
        #availability-calendar .fc-daygrid-day.available-date:hover {
            background: rgba(74, 103, 65, 0.1) !important;
            cursor: pointer;
        }
        .fc .fc-toolbar-title {
            font-family: var(--font-display) !important;
            font-size: 1.2rem !important;
        }
        .fc .fc-button {
            background: var(--zen-forest) !important;
            border-color: var(--zen-forest) !important;
            font-size: 0.8rem !important;
        }
        .fc .fc-button:hover {
            background: var(--zen-forest-deep) !important;
        }
        .fc .fc-day-today {
            background: rgba(196, 163, 90, 0.1) !important;
        }
        .calendar-legend {
            display: flex;
            gap: 1.5rem;
            margin-top: 0.75rem;
            font-size: 0.8rem;
            color: var(--zen-moss);
        }
        .calendar-legend span {
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 3px;
            display: inline-block;
        }
        .legend-dot.available { background: rgba(74, 103, 65, 0.2); border: 1px solid var(--zen-moss); }
        .legend-dot.booked { background: rgba(220, 53, 69, 0.15); border: 1px solid #dc3545; }
        .legend-dot.today { background: rgba(196, 163, 90, 0.2); border: 1px solid var(--zen-gold); }
        .price-preview {
            background: linear-gradient(135deg, rgba(196,163,90,0.1), rgba(196,163,90,0.05));
            border: 1px solid var(--zen-gold);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-top: 1rem;
            display: none;
        }
        .price-preview.active { display: block; }
        .price-preview h4 {
            color: var(--zen-forest-deep);
            font-family: var(--font-display);
            margin-bottom: 0.5rem;
        }
        .price-preview .price-row {
            display: flex;
            justify-content: space-between;
            padding: 0.25rem 0;
            font-size: 0.9rem;
        }
        .price-preview .price-total {
            border-top: 1px solid var(--zen-gold);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            font-weight: 600;
        }
        .availability-msg {
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            font-size: 0.85rem;
            margin-top: 0.5rem;
            display: none;
        }
        .availability-msg.available {
            background: rgba(74, 103, 65, 0.1);
            color: #2d5016;
            display: block;
        }
        .availability-msg.unavailable {
            background: rgba(220, 53, 69, 0.1);
            color: #dc3545;
            display: block;
        }
'''

if '.calendar-section' not in html:
    html = html.replace(
        '        /* Top Bar */',
        calendar_css + '\n        /* Top Bar */'
    )
    print("Added calendar CSS")

# ── 3. Replace the accommodation select + add calendar section ──
old_accom_group = '''                    <div class="form-group" id="accom-select-group">
                        <label>Preferred Accommodation</label>
                        <select name="accommodation" id="bk-accom">
                            <option value="">No preference / Surprise me</option>
                            <option value="Riverlight Cabin">Riverlight Cabin — $120/night</option>
                            <option value="Zen Casa (3BR)">Zen Casa (3 Bedroom) — $180/night</option>
                            <option value="River House">River House — $85/night</option>
                            <option value="Jungle Platform">Jungle Platform — $45/night</option>
                            <option value="Sky Lily Zome">Sky Lily Zome — $130/night</option>
                            <option value="Astro Sol Zome">Astro Sol Zome — $130/night</option>
                            <option value="La Vista (Hilltop)">La Vista (Hilltop, 4x4 required) — $150/night</option>
                            <option value="The Nest (Hilltop)">The Nest (Hilltop, 4x4 required) — $115/night</option>
                            <option value="Full Property">Full Property Rental — from $450/night</option>
                        </select>
                    </div>'''

new_accom_group = '''                    <div class="form-group" id="accom-select-group">
                        <label>Preferred Accommodation</label>
                        <select name="accommodation" id="bk-accom">
                            <option value="">Loading accommodations...</option>
                        </select>
                    </div>

                    <!-- Availability Calendar -->
                    <div class="calendar-section" id="calendar-section" style="display:none;">
                        <h3>Check Availability</h3>
                        <p class="subtitle">Select your dates on the calendar. Booked dates are shown in red.</p>
                        <div id="availability-calendar"></div>
                        <div class="calendar-legend">
                            <span><span class="legend-dot available"></span> Available</span>
                            <span><span class="legend-dot booked"></span> Booked</span>
                            <span><span class="legend-dot today"></span> Today</span>
                        </div>
                        <div id="availability-msg" class="availability-msg"></div>
                        <div id="price-preview" class="price-preview">
                            <h4>Price Estimate</h4>
                            <div id="price-details"></div>
                        </div>
                    </div>'''

if old_accom_group in html:
    html = html.replace(old_accom_group, new_accom_group)
    print("Replaced accommodation dropdown + added calendar section")
else:
    print("WARNING: Could not find exact accommodation dropdown match")
    # Try a broader approach
    if 'id="accom-select-group"' in html and 'id="calendar-section"' not in html:
        # Insert calendar section after the accom-select-group div
        import re
        pattern = r'(</select>\s*</div>\s*)(<!-- Availability Calendar -->|<div class="form-group">\s*<label>Preferred Payment)'
        # Let's just insert after the accommodation select div closes
        html = html.replace(
            '</select>\n                    </div>\n\n                    <div class="form-group">\n                        <label>Preferred Payment Method</label>',
            '</select>\n                    </div>\n\n' + '''                    <!-- Availability Calendar -->
                    <div class="calendar-section" id="calendar-section" style="display:none;">
                        <h3>Check Availability</h3>
                        <p class="subtitle">Select your dates on the calendar. Booked dates are shown in red.</p>
                        <div id="availability-calendar"></div>
                        <div class="calendar-legend">
                            <span><span class="legend-dot available"></span> Available</span>
                            <span><span class="legend-dot booked"></span> Booked</span>
                            <span><span class="legend-dot today"></span> Today</span>
                        </div>
                        <div id="availability-msg" class="availability-msg"></div>
                        <div id="price-preview" class="price-preview">
                            <h4>Price Estimate</h4>
                            <div id="price-details"></div>
                        </div>
                    </div>

''' + '                    <div class="form-group">\n                        <label>Preferred Payment Method</label>'
        )
        print("Inserted calendar section via broader match")

# ── 4. Add FullCalendar JS + booking API integration before </body> ──
# Remove the old season banner script and replace with the comprehensive booking JS
old_season_script = '''<script>
const SEASON_CFG = {highMonths: [12,1,2,3,4]};
function getSeason() {
  return SEASON_CFG.highMonths.includes(new Date().getMonth()+1) ? 'high' : 'green';
}
document.addEventListener('DOMContentLoaded', function() {
  var s = getSeason();
  var b = document.createElement('div');
  b.style.cssText = 'text-align:center;padding:0.75rem;font-weight:500;font-size:0.9rem;margin-bottom:1rem;border-radius:8px;';
  if (s === 'green') {
    b.style.background = 'linear-gradient(135deg, rgba(74,103,65,0.15), rgba(125,154,111,0.15))';
    b.style.color = '#3a5a30';
    b.innerHTML = '\U0001f33f <strong>Green Season Rates</strong> (May-Nov) \u2014 15% off all accommodations!';
  } else {
    b.style.background = 'linear-gradient(135deg, rgba(196,163,90,0.15), rgba(212,149,106,0.15))';
    b.style.color = '#8a6d2f';
    b.innerHTML = '\u2600\ufe0f <strong>High Season Rates</strong> (Dec-Apr) in effect';
  }
  var m = document.querySelector('main') || document.querySelector('.booking-content') || document.body;
  if (m.firstChild) m.insertBefore(b, m.firstChild);
});
</script>'''

booking_js = '''<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js"></script>
<script>
(function() {
  const API = '/api/bookings';
  const SEASON_CFG = {highMonths: [12,1,2,3,4]};
  let accommodations = [];
  let calendar = null;
  let bookedDates = new Set();
  let selectedAccId = '';
  let selStart = null;
  let selEnd = null;

  function getSeason() {
    return SEASON_CFG.highMonths.includes(new Date().getMonth()+1) ? 'high' : 'green';
  }

  // Season banner
  function addSeasonBanner() {
    var s = getSeason();
    var b = document.createElement('div');
    b.style.cssText = 'text-align:center;padding:0.75rem;font-weight:500;font-size:0.9rem;margin-bottom:1rem;border-radius:8px;';
    if (s === 'green') {
      b.style.background = 'linear-gradient(135deg, rgba(74,103,65,0.15), rgba(125,154,111,0.15))';
      b.style.color = '#3a5a30';
      b.innerHTML = '\\u{1F33F} <strong>Green Season Rates</strong> (May\\u2013Nov) \\u2014 15% off all accommodations!';
    } else {
      b.style.background = 'linear-gradient(135deg, rgba(196,163,90,0.15), rgba(212,149,106,0.15))';
      b.style.color = '#8a6d2f';
      b.innerHTML = '\\u2600\\uFE0F <strong>High Season Rates</strong> (Dec\\u2013Apr) in effect';
    }
    var m = document.querySelector('main') || document.querySelector('.booking-content') || document.body;
    if (m.firstChild) m.insertBefore(b, m.firstChild);
  }

  // Load accommodations from API
  async function loadAccommodations() {
    try {
      const res = await fetch(API + '/accommodations');
      const data = await res.json();
      accommodations = data.accommodations || [];
      populateDropdown();
    } catch (e) {
      console.error('Failed to load accommodations:', e);
      populateFallback();
    }
  }

  function populateDropdown() {
    const sel = document.getElementById('bk-accom');
    sel.innerHTML = '<option value="">Select accommodation...</option>';
    const zones = {};
    accommodations.forEach(function(a) {
      if (!zones[a.zone]) zones[a.zone] = [];
      zones[a.zone].push(a);
    });
    var zoneNames = {village_heart: 'Village Heart', river_grove: 'River Grove', escape_ridge: 'Escape Ridge'};
    Object.keys(zones).forEach(function(z) {
      var grp = document.createElement('optgroup');
      grp.label = zoneNames[z] || z;
      zones[z].forEach(function(a) {
        var opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name + ' \\u2014 $' + a.current_nightly + '/night';
        opt.dataset.rate = a.current_nightly;
        opt.dataset.cleaning = a.cleaning_fee;
        opt.dataset.name = a.name;
        grp.appendChild(opt);
      });
      sel.appendChild(grp);
    });
  }

  function populateFallback() {
    var sel = document.getElementById('bk-accom');
    sel.innerHTML = '<option value="">No preference / Surprise me</option>' +
      '<option value="astro-alpha">Sky Lily Zome \\u2014 $130/night</option>' +
      '<option value="astro-sol">Astro Sol Zome \\u2014 $130/night</option>' +
      '<option value="green-casita">Green Casita \\u2014 $95/night</option>' +
      '<option value="riverlight">Riverlight Cabin \\u2014 $120/night</option>' +
      '<option value="zen-casa">Zen Casa \\u2014 $180/night</option>' +
      '<option value="the-vista">La Vista \\u2014 $150/night</option>' +
      '<option value="the-nido">The Nest \\u2014 $115/night</option>' +
      '<option value="camp-spring">Camp Spring \\u2014 $20/night</option>' +
      '<option value="glamp-grove">Glamp Grove \\u2014 $45/night</option>';
  }

  // Calendar initialization
  function initCalendar() {
    var calEl = document.getElementById('availability-calendar');
    if (!calEl || calendar) return;
    calendar = new FullCalendar.Calendar(calEl, {
      initialView: 'dayGridMonth',
      headerToolbar: { left: 'prev', center: 'title', right: 'next' },
      height: 'auto',
      selectable: true,
      selectMirror: true,
      validRange: { start: new Date().toISOString().split('T')[0] },
      dayCellDidMount: function(info) {
        var ds = info.date.toISOString().split('T')[0];
        if (bookedDates.has(ds)) {
          info.el.classList.add('booked-date');
        } else {
          info.el.classList.add('available-date');
        }
      },
      select: function(info) {
        var start = info.startStr;
        var end = info.endStr;
        // Check if any selected date is booked
        var d = new Date(start);
        var endD = new Date(end);
        var conflict = false;
        while (d < endD) {
          if (bookedDates.has(d.toISOString().split('T')[0])) { conflict = true; break; }
          d.setDate(d.getDate() + 1);
        }
        if (conflict) {
          showAvailMsg('Some of those dates are already booked. Please choose different dates.', false);
          calendar.unselect();
          return;
        }
        document.getElementById('bk-checkin').value = start;
        document.getElementById('bk-checkout').value = end;
        selStart = start;
        selEnd = end;
        showAvailMsg('\\u2705 Those dates are available!', true);
        updatePricePreview();
      },
      datesSet: function(info) {
        if (selectedAccId) {
          fetchBookedDates(selectedAccId, info.startStr, info.endStr);
        }
      }
    });
    calendar.render();
  }

  async function fetchBookedDates(structureId, startDate, endDate) {
    try {
      var res = await fetch(API + '/availability/' + structureId + '/dates?start_date=' + startDate + '&end_date=' + endDate);
      var data = await res.json();
      bookedDates = new Set(data.unavailable_dates || []);
      if (calendar) {
        calendar.refetchEvents();
        // Re-render day cells
        calendar.destroy();
        calendar = null;
        initCalendar();
      }
    } catch (e) {
      console.error('Failed to fetch availability:', e);
    }
  }

  function showAvailMsg(msg, isAvailable) {
    var el = document.getElementById('availability-msg');
    if (!el) return;
    el.textContent = msg;
    el.className = 'availability-msg ' + (isAvailable ? 'available' : 'unavailable');
  }

  function updatePricePreview() {
    var preview = document.getElementById('price-preview');
    var details = document.getElementById('price-details');
    if (!preview || !details) return;

    var checkin = document.getElementById('bk-checkin').value;
    var checkout = document.getElementById('bk-checkout').value;
    var sel = document.getElementById('bk-accom');
    var opt = sel.options[sel.selectedIndex];

    if (!checkin || !checkout || !opt || !opt.dataset.rate) {
      preview.classList.remove('active');
      return;
    }

    var nights = Math.ceil((new Date(checkout) - new Date(checkin)) / 86400000);
    if (nights <= 0) { preview.classList.remove('active'); return; }

    var rate = parseFloat(opt.dataset.rate);
    var cleaning = parseFloat(opt.dataset.cleaning || 0);
    var subtotal = rate * nights;
    var total = subtotal + cleaning;

    details.innerHTML =
      '<div class="price-row"><span>' + nights + ' night' + (nights > 1 ? 's' : '') + ' \\u00d7 $' + rate + '</span><span>$' + subtotal.toLocaleString() + '</span></div>' +
      (cleaning > 0 ? '<div class="price-row"><span>Cleaning fee</span><span>$' + cleaning + '</span></div>' : '') +
      '<div class="price-row price-total"><span>Estimated Total</span><span>$' + total.toLocaleString() + '</span></div>';
    preview.classList.add('active');
  }

  // Wire accommodation change to show calendar
  document.getElementById('bk-accom').addEventListener('change', function() {
    selectedAccId = this.value;
    var calSection = document.getElementById('calendar-section');

    if (selectedAccId) {
      calSection.style.display = 'block';
      bookedDates = new Set();
      if (!calendar) {
        initCalendar();
      }
      var view = calendar.view;
      fetchBookedDates(selectedAccId, view.activeStart.toISOString().split('T')[0], view.activeEnd.toISOString().split('T')[0]);
    } else {
      calSection.style.display = 'none';
    }
    updatePricePreview();
  });

  // Update price when dates change manually
  document.getElementById('bk-checkin').addEventListener('change', updatePricePreview);
  document.getElementById('bk-checkout').addEventListener('change', function() {
    updatePricePreview();
    // Check availability when both dates are set
    var checkin = document.getElementById('bk-checkin').value;
    var checkout = this.value;
    if (checkin && checkout && selectedAccId) {
      fetch(API + '/availability/' + selectedAccId + '?check_in=' + checkin + '&check_out=' + checkout)
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.available) {
            showAvailMsg('\\u2705 Available! ' + d.nights + ' nights, $' + d.pricing.total + ' total', true);
          } else {
            showAvailMsg('\\u274c Not available for those dates. Please try different dates.', false);
          }
        })
        .catch(function() {});
    }
  });

  // Init on load
  document.addEventListener('DOMContentLoaded', function() {
    addSeasonBanner();
    loadAccommodations();
  });
})();
</script>'''

if old_season_script in html:
    html = html.replace(old_season_script, booking_js)
    print("Replaced season script with full booking JS")
else:
    print("Old season script not found exactly, appending before </body>")
    # Try removing just the old script block and add new one
    import re
    # Remove old season script
    html = re.sub(
        r'<script>\s*const SEASON_CFG.*?</script>',
        '',
        html,
        flags=re.DOTALL
    )
    html = html.replace('</body>', booking_js + '\n</body>')
    print("Added booking JS before </body>")

# ── 5. Update form submission to also create a real booking ──
old_submit = '''            try {
                const res = await fetch('/api/inquiries/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (res.ok) {
                    showSuccess(data.payment_method);
                } else {
                    window.location.href = `mailto:james@fullpotential.com?subject=${encodeURIComponent('Zen Village Booking: ' + data.name)}&body=${encodeURIComponent(JSON.stringify(data, null, 2))}`;
                    showSuccess(data.payment_method);
                }
            } catch (err) {
                window.location.href = `mailto:james@fullpotential.com?subject=${encodeURIComponent('Zen Village Booking: ' + data.name)}&body=${encodeURIComponent(JSON.stringify(data, null, 2))}`;
                showSuccess(data.payment_method);
            }'''

new_submit = '''            try {
                // Submit inquiry (sends email notification)
                const inquiryRes = await fetch('/api/inquiries/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                // Also create a booking record if accommodation selected
                const accomSel = document.getElementById('bk-accom');
                const accomId = accomSel ? accomSel.value : '';
                if (accomId && checkin && checkout) {
                    try {
                        await fetch('/api/bookings/', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                structure_id: accomId,
                                guest_name: data.name,
                                guest_email: data.email,
                                guest_phone: data.phone || '',
                                check_in: checkin,
                                check_out: checkout,
                                special_requests: data.message || '',
                                source: 'direct',
                                partner_code: data.partner_code || null,
                                discount_percent: 0
                            })
                        });
                    } catch (bookErr) {
                        console.warn('Booking record creation failed (inquiry still sent):', bookErr);
                    }
                }

                showSuccess(data.payment_method);
            } catch (err) {
                window.location.href = `mailto:james@fullpotential.com?subject=${encodeURIComponent('Zen Village Booking: ' + data.name)}&body=${encodeURIComponent(JSON.stringify(data, null, 2))}`;
                showSuccess(data.payment_method);
            }'''

if old_submit in html:
    html = html.replace(old_submit, new_submit)
    print("Updated form submission to create booking records")
else:
    print("WARNING: Could not find exact form submit block to update")

with open(BOOKING_FILE, 'w') as f:
    f.write(html)

print("\nDone! Booking page upgraded with:")
print("  - FullCalendar.js availability calendar")
print("  - Dynamic accommodation dropdown from API")
print("  - Real-time availability checking")
print("  - Price preview")
print("  - Booking API integration")
