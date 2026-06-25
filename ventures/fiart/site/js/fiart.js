/* Fi-art — Phase 1 shared logic
   No backend. Sample notes load from data/notes.json; creator-minted Open notes persist in
   localStorage ('fiart_notes') so the mint→marketplace→detail loop is demoable end to end. */

const FiArt = (() => {
  const LS_NOTES = 'fiart_notes';
  const LS_COVENANT = 'fiart_covenant';
  const COVENANT_VERSION = 'v0.1';

  // ---- note-type display config ----
  const TYPES = {
    open:     {label:'Open Fi-art',  badge:'art',      grad:['#3a4a5a','#27323d'], redeemable:false, risk:'Art-only',
               legal:'Art-only. Not redeemable. Not money.'},
    capacity: {label:'Capacity Note',badge:'capacity', grad:['#2c4f44','#1f3d34'], redeemable:true,  risk:'Capacity-backed',
               legal:'Redeemable for listed service. Not cash. Not legal tender.'},
    art:      {label:'Art Note',     badge:'artnote',  grad:['#866227','#5e441a'], redeemable:'maybe',risk:'Art-backed',
               legal:'Claim to artwork. Not legal tender. Cash value not guaranteed.'},
    access:   {label:'Access Note',  badge:'access',   grad:['#5b3f73','#3f2b52'], redeemable:true,  risk:'Access-backed',
               legal:'Redeemable for listed access. Not cash. Not legal tender.'},
    mirror:   {label:'Mirror Note',  badge:'mirror',   grad:['#a3432f','#7a2f20'], redeemable:true,  risk:'Reserve-backed',
               legal:'Redeemable claim. Reserve-backed. Not legal tender. Subject to terms.'}
  };

  // ---- money-claim scanner (Phase 1 enforcement, SPEC §16/§25) ----
  // Blocks misleading financial language on Open (non-verified) notes.
  const BANNED = [
    'legal tender','government-backed','government backed','federal reserve','treasury note',
    'guaranteed profit','guaranteed return','guaranteed appreciation','risk-free','risk free',
    'yield','interest rate','deposit','bank account','cash equivalent','redeemable for cash',
    'redeem for cash','investment opportunity','apy','roi guaranteed','banknote','money replacement',
    'fdic','insured','community insurance','default coverage','passive income','floor price guaranteed',
    'fractional revenue','guaranteed cash','guaranteed balance','savings account'
  ];
  function scanClaims(text){
    const t = (text||'').toLowerCase();
    const hits = BANNED.filter(p => t.includes(p));
    return {clean: hits.length === 0, hits};
  }

  // ---- currency-imagery quick check (BEP, SPEC §16) ----
  function currencyFlags(answers){
    // answers: {includesCurrency, resemblesBill, oneSided, oversizedOrUnder}
    const flags = [];
    if(answers.includesCurrency && answers.resemblesBill){
      if(!answers.oneSided) flags.push('Color currency reproductions must be one-sided (BEP).');
      if(!answers.oversizedOrUnder) flags.push('Reproductions must be under ¾ or over 1½× the real bill\'s linear size (BEP).');
    }
    return flags;
  }

  // ---- storage ----
  async function loadSampleNotes(){
    try{ const r = await fetch('data/notes.json'); return r.ok ? await r.json() : []; }
    catch(e){ return []; }
  }
  function loadMinted(){
    try{ return JSON.parse(localStorage.getItem(LS_NOTES) || '[]'); }catch(e){ return []; }
  }
  function saveMinted(note){
    const all = loadMinted(); all.unshift(note);
    localStorage.setItem(LS_NOTES, JSON.stringify(all));
  }
  async function allNotes(){
    const [sample, minted] = [await loadSampleNotes(), loadMinted()];
    return [...minted, ...sample];
  }
  async function getNote(id){
    return (await allNotes()).find(n => n.id === id) || null;
  }

  // ---- covenant ----
  function covenantSigned(){
    try{ return JSON.parse(localStorage.getItem(LS_COVENANT) || 'null'); }catch(e){ return null; }
  }
  function signCovenant(handle){
    const rec = {handle: handle||'anonymous', version: COVENANT_VERSION, signed_at: new Date().toISOString()};
    localStorage.setItem(LS_COVENANT, JSON.stringify(rec));
    return rec;
  }

  // ---- rendering ----
  function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  function noteArt(n){
    const cfg = TYPES[n.type] || TYPES.open;
    const g = cfg.grad;
    const denom = n.denomination || cfg.label;
    return `<div class="note-art" style="background:linear-gradient(135deg,${g[0]},${g[1]})">
      <div class="guilloche"></div><div class="denom">${esc(denom)}</div></div>`;
  }

  function badge(n){
    const cfg = TYPES[n.type] || TYPES.open;
    return `<span class="badge ${cfg.badge} dot">${esc(cfg.risk)}</span>`;
  }

  function card(n){
    const cfg = TYPES[n.type] || TYPES.open;
    const redeem = n.redeemable_for || (cfg.redeemable===false ? 'Nothing — art only' : '—');
    const price = n.price!=null ? `${esc(n.price)} ${esc(n.currency||'Fiart Marketplace Credit')}` : 'Not for sale';
    const ver = n.verified ? `<span class="badge verified">Verified</span>` : '';
    return `<a class="note-card" href="note.html?id=${encodeURIComponent(n.id)}">
      ${noteArt(n)}
      <div class="note-body">
        <div class="t">${esc(n.title)}</div>
        <div class="pill-row">${badge(n)} ${ver}</div>
        <div class="row"><span>Redeemable for</span><span>${esc(redeem)}</span></div>
        <div class="row"><span>${esc((TYPES[n.type]||{}).label||'')}</span><span class="price">${price}</span></div>
        <div class="legal-line">${esc(cfg.legal||'Not legal tender. Read the Truth Panel.')}</div>
      </div></a>`;
  }

  // ---- Truth Panel (the heart, SPEC §8) ----
  function truthPanel(n){
    const cfg = TYPES[n.type] || TYPES.open;
    const yn = v => v===true ? `<span class="v yes">Yes</span>` : v===false ? `<span class="v no">No</span>` : `<span class="v">${esc(v)}</span>`;
    const row = (k,v) => `<div class="tr"><span class="k">${k}</span>${v}</div>`;
    const redeemable = n.redeemable!=null ? n.redeemable : cfg.redeemable;
    const cashRedeem = n.cash_redeemable===true;

    let warn = '';
    if(redeemable === false || redeemable === 'no'){
      warn = `<div class="warn">This note is art-only and has no redemption claim. Not legal tender. No reserve backing.</div>`;
    } else if(n.type==='capacity' || n.type==='access'){
      warn = `<div class="warn ok">Redeemable only for the listed good, service, or experience — not cash redeemable unless explicitly stated.</div>`;
    } else if(n.type==='mirror'){
      warn = `<div class="warn danger">Redeemable through the listed liquidity steward subject to eligibility, limits, fees, and reserve terms.</div>`;
    } else if(n.type==='art'){
      warn = `<div class="warn">Conveys a claim to the artwork — not cash redemption unless explicitly stated.</div>`;
    }
    if(n.status==='impaired') warn = `<div class="warn danger">⚠ IMPAIRED — redemption cannot currently be honored. Recovery status pending.</div>`;
    if(n.status==='expired') warn = `<div class="warn">This note has expired. Held as a collectible; redemption window closed.</div>`;

    const failByType = {
      open:'Nothing to redeem — resale depends on a willing buyer.',
      capacity:'Provider may be unable to perform — see replacement terms.',
      access:'Event/membership terms may change — see listing.',
      art:'Physical claim depends on creator/custodian fulfillment.',
      mirror:'Reserve shortfall, eligibility limits, or partner failure.'
    };
    const whatFails = n.what_can_fail || failByType[n.type] || '—';
    const feesRow = n.type==='mirror' ? row('Fees / limits', `<span class="v">${esc(n.fees_limits||'Per partner terms')}</span>`) : '';
    const jurisRow = (n.type==='mirror'||n.type==='access') ? row('Jurisdiction', `<span class="v">${esc(n.jurisdiction_limits||'See terms')}</span>`) : '';

    return `<div class="truth">
      <div class="th"><span>Fi-art Truth Panel</span><span>${esc(n.id)}</span></div>
      <div class="rows">
        ${row('Type', `<span class="v">${esc(cfg.label)}</span>`)}
        ${row('Creator', `<span class="v">${esc(n.creator||'—')}${n.verified?' ✓':''}</span>`)}
        ${row('Redeemable', yn(redeemable))}
        ${row('Redeemable for', `<span class="v">${esc(n.redeemable_for || (redeemable===false?'Nothing':'—'))}</span>`)}
        ${row('Cash redeemable', yn(cashRedeem))}
        ${row('Backed by', `<span class="v">${esc(n.backed_by || (redeemable===false?'Cultural value':'—'))}</span>`)}
        ${row('Who must honor', `<span class="v">${esc(n.honored_by || (redeemable===false?'No one':'—'))}</span>`)}
        ${row('Transferable', `<span class="v">${esc(n.transferable||'—')}</span>`)}
        ${row('Expiration', `<span class="v">${esc(n.expiration||'None')}</span>`)}
        ${feesRow}
        ${jurisRow}
        ${row('Risk label', `<span class="v">${esc(n.risk_label || cfg.risk)}</span>`)}
        ${row('Legal status', `<span class="v">Not legal tender</span>`)}
        ${row('Dispute path', `<span class="v">${esc(n.dispute_path||'Trust Center')}</span>`)}
        ${row('Teaches', `<span class="v">${esc(n.educational_theme||'—')}</span>`)}
        ${row('What can fail', `<span class="v" style="color:var(--warn)">${esc(whatFails)}</span>`)}
      </div>
      ${warn}
    </div>`;
  }

  function qs(k){ return new URLSearchParams(location.search).get(k); }

  return {TYPES, scanClaims, currencyFlags, allNotes, getNote, saveMinted, loadMinted,
    covenantSigned, signCovenant, COVENANT_VERSION, card, truthPanel, badge, noteArt, esc, qs};
})();
