// Shared submit handler for all /apply-* lane pages.
// Adds:
//   - Honeypot field (`website_url_extra`) appended to every form on load.
//     Real humans won't see it. Bots auto-fill any field they can find;
//     server discards anything where this field is non-empty.
//   - Source/UTM capture (utm_source, utm_medium, utm_campaign, ?ref=,
//     document.referrer) added to the JSON payload so the cockpit can
//     show "where did this person come from".

(function () {
  const form = document.getElementById('apply-form');
  if (!form) return;

  // ── Honeypot ────────────────────────────────────────────────────────────
  if (!form.querySelector('input[name="website_url_extra"]')) {
    const hp = document.createElement('input');
    hp.type = 'text';
    hp.name = 'website_url_extra';
    hp.value = '';
    hp.tabIndex = -1;
    hp.autocomplete = 'off';
    hp.setAttribute('aria-hidden', 'true');
    hp.style.cssText =
      'position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0;pointer-events:none';
    form.appendChild(hp);
  }

  // ── Source / UTM capture ────────────────────────────────────────────────
  function captureSource() {
    try {
      const params = new URLSearchParams(location.search);
      const src = {};
      ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref']
        .forEach(k => { const v = params.get(k); if (v) src[k] = v; });
      if (document.referrer) src.referrer = document.referrer;
      const cookieRef = (document.cookie.match(/zv_ref=([^;]+)/) || [])[1];
      if (cookieRef) src.cookie_ref = cookieRef;
      return src;
    } catch { return {}; }
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const lane = form.dataset.lane || 'general';
    const btn = document.getElementById('submit-btn');
    btn.disabled = true;
    btn.textContent = 'submitting...';

    const data = { lane };

    form.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="url"], input[type="number"], textarea').forEach(el => {
      if (el.name) data[el.name] = el.value;
    });

    const checkboxGroups = {};
    form.querySelectorAll('input[type="checkbox"]:checked').forEach(el => {
      if (!checkboxGroups[el.name]) checkboxGroups[el.name] = [];
      checkboxGroups[el.name].push(el.value);
    });
    Object.assign(data, checkboxGroups);

    data._source = captureSource();

    try {
      const resp = await fetch('/api/applications/' + lane, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (resp.ok) {
        form.style.display = 'none';
        document.getElementById('success').style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        btn.disabled = false;
        btn.textContent = 'submit application';
        alert('Something went wrong. Please try again.');
      }
    } catch (err) {
      form.style.display = 'none';
      document.getElementById('success').style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });
})();
