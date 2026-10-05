# DRAFT — WhatsApp a La Cocinona de Pueblo (+506 6362 6524)
STATUS: M1 SENT 2026-09-03 06:22 CR (delivered). M2 IS READY TO SEND — redemption line synced to REDEMPTION.md (same-day / ≤24h) by Claude 2026-09-03 09:1x CR.
DO NOT RE-SEND M1: it went out verbatim as recorded in VENDOR_LOG.md ("Soy un asistente de inteligencia artificial que trabaja para James…"), not as written below. The M1 text below is kept only as the template for the NEXT candidate.
Channel: WhatsApp text, in three short messages so they can answer between them.

--- Mensaje 1 ---
Buenas tardes. Soy Ember, el asistente de inteligencia artificial de James, un vecino de la zona de Chirripó. Cualquier acuerdo lo confirma él personalmente. ¿Le puedo hacer una consulta corta sobre una comida para diez personas?

--- Mensaje 2 (after they reply) ---
James quiere darle una buena comida (un casado completo) a diez personas, y quiere pagar la comida con algo nuevo que se llama SUPER, en vez de colones. Serían 100 SUPER por los diez platos.
<!-- DEFECT, marked 2026-10-05 (finding 25): that last sentence QUOTES the price. PROVIDER_CANDIDATES.md line 16 says to ASK a price in SUPER for 10 plates, and line 1 says to INSIST on a quoted price with this very candidate. For any FUTURE candidate this sentence must become a question: state the 100 SUPER = ₡40,000 we have set aside, then ask what they charge. Not re-sent or corrected to La Cocinona: M-NUDGE-2 now asks her price, which gives her strictly more freedom than this message did (2026-09-04 precedent). -->

SUPER es completamente nuevo — esta sería la primera vez que se usa para comida de verdad. Hoy, lo que se puede hacer con 100 SUPER es: ₡40,000 en colones (efectivo o SINPE), que James le entrega el mismo día si lo pide antes de las 3 de la tarde, y nunca más de 24 horas. O, si prefiere, puede gastar los SUPER con otra persona que los acepte: valen los ₡40,000 completos. Vale hasta el 31 de diciembre de 2026.

Le pregunto con honestidad, y un "no" es una respuesta perfectamente buena:
1. ¿Aceptaría 100 SUPER por la comida para diez personas?
2. Si sí — ¿qué haría usted con los SUPER?
3. Si sale bien, ¿aceptaría SUPER otra vez?

--- Mensaje 3 (after their answers) --- DEFECTIVE FOR THIS THREAD, see M-NUDGE-3 below (finding 24)
<!-- Kept verbatim as the record. It promises "James la va a llamar" — a voice call. Finding 20
     established WhatsApp is the only provider channel this system owns, so this message promises
     a channel we cannot keep. Do not send it to La Cocinona. For a NEW candidate it must be
     re-channelled before use. -->
Muchas gracias por responder. Todavía no hay nada reservado: James la va a llamar para confirmar la fecha y los detalles. Si en cualquier momento siente que esto le cuesta más de lo que le da, dígalo y paramos.

--- Agent notes ---
- Record every answer verbatim in VENDOR_LOG.md. Q2 in their words, no paraphrase.
- If Q2 has no concrete next use ("por ayudarle", "no sé") → classify FAVOR-NOT-EXCHANGE; thank them; do not book.
- If they ask for colones as well → default is no (single currency, Decision 001); record the counter, escalate to James.
- One follow-up after 48h if no reply, then silence.


> 2026-09-04 08:52 CR · REDEMPTION CHANGED (James: "Drop the 40,000 card idea"). The gift card and the ₡38,000 colones figure are gone; colones is now the full ₡40,000. The M2 text above is updated for any FUTURE send. The M2 that actually went out 2026-09-03 15:12Z carried the old three options — do NOT re-send, do NOT correct: every option she was offered is now equal or better. See REDEMPTION.md change log.

---

## M-NUDGE — the Saturday nudge, 30 days late (drafted 2026-10-03 10:05 CR, NOT sent)
Why this exists: SATURDAY_PACKET.md promised her ONE nudge on Sat 2026-09-05 12:15 CR. The heartbeat
went mute 2026-09-04 (B-08) and it never went — not that Saturday nor the three after it. She has been
open every one of them. Her listing is still live (Tripadvisor, read 2026-10-03: open, #1 of 7 in Rivas,
Sat 12:00–21:00 / Sun 09:00–20:00). So this is not the packet's nudge; it is a month-late one, and it has
to say so and take the blame, or it is mean.
WHO SENDS IT: James, by hand, from his own WhatsApp, inside her open hours — Sat 12:00-21:00 or
Sun 09:00-20:00 CR. There is no "today" in this instruction on purpose (see the 2026-10-05 amendment
below): the next window is the next Saturday or Sunday after he reads this, whenever that is.
NOT the agent: the approved channel runs through a bot that has been mute since 2026-09-03 22:15Z, and
the packet's one-nudge budget was for a message this is no longer.
IF SHE DOES NOT ANSWER — the trigger is counted FROM THE SEND, never from a calendar date, and it
cannot fire on a message that was not sent. Condition, in full: once this message is on the record in
VENDOR_LOG.md with its send timestamp, and the first full open window AFTER that send has closed
(the Sat or Sun following the send, 21:00 / 20:00 CR) with no reply, THEN candidate #1 rests and
candidate #2 (Comité Turismo Rural La Piedra de Rivas, WhatsApp 8317-8140) opens with a fresh
consent-first M1 — CANDIDATE_2_PACKET.md. Until the send is logged, candidate #1 is LIVE, candidate #2
stays CLOSED, and no amount of elapsed time changes that. One candidate live at a time.

TEXT (send verbatim, or change any word — it is your name on it):

> Buenas, doña. Le escribí hace un mes por una comida para diez personas y después me quedé callado.
> Eso fue falla nuestra, no suya, y le pido disculpas por dejarla esperando.
> Si ya no le interesa, no hay ningún problema y le agradezco igual.
> Si todavía le sirve, dígame y le cuento en dos líneas, sin compromiso.
> (Este mensaje lo redactó mi asistente de inteligencia artificial; cualquier acuerdo lo confirmo yo
> personalmente. — James, vecino de la zona de Chirripó)

IF SHE ANSWERS, SEND M-NUDGE-2 BELOW — do not improvise and do not re-send M2. M-NUDGE above promises
her "dos líneas, sin compromiso", and M-NUDGE-2 is those two lines: it carries the whole offer and it
asks Q2 in her own turn. Then capture her Q2 answer verbatim — "¿y qué haría usted con los SUPER?" —
into VENDOR_LOG.md, no paraphrase. That one sentence is what turns condition 1 from ✗ to ✓.

### AMENDMENT 2026-10-05 15:30Z (09:30 CR) — finding 21, Claude, Super Agent
This draft was written 2026-10-03 10:05 CR to repair finding 10: a nudge whose timer was armed by our
own action and then read as patience. In the same hour, this section re-armed the identical structure —
it said "send it TODAY after 12:00 CR" (Sat 2026-10-03) and "if nothing by Sunday close, candidate #1
rests and #2 opens" (Sun 2026-10-04 20:00 CR). Both moments have passed. The message was NOT sent:
VENDOR_LOG.md and VENDOR_LOG_198.md (mirror pulled 2026-10-05T14:15Z) both still end at the two
2026-09-03T15:12 entries. So for the SECOND time a fallback stood ready to rest a provider and open a
stranger on the strength of a message nobody sent. Nothing acted on it and no harm reached her — but
nothing prevented it either, and the first instance cost thirty days.
Fixed above, inside remit: the trigger is now relative to the SEND and refuses to fire without a logged
send; the "today" is replaced by the standing window rule.
STATE, unchanged by this amendment: candidate #1 La Cocinona de Pueblo is LIVE and NOT rested;
candidate #2 is CLOSED; nobody has been contacted; REDEMPTION.md untouched; the one-candidate guard
holds. Next open window: Sat 2026-10-11 12:00-21:00 CR.
AGING, named not fixed: the text says "le escribi hace un mes". On 2026-10-11 the real gap is 38 days,
which "hace un mes" still covers honestly. If this goes out after about 2026-11-03, change that phrase
to "hace dos meses" — a late apology that understates the lateness is not an apology.
RULE: A DEADLINE THAT COUNTS DOWN WHETHER OR NOT WE ACTED IS A CLOCK ON OUR OWN DIARY, NOT ON THE OTHER
PERSON. Corollary: a repair is not a repair until the artifact carrying it has been read against the
rule that prompted it.

## M-NUDGE-2 — the two lines M-NUDGE promises (drafted 2026-10-05 13:20 CR, NOT sent)
WHO SENDS IT: James, same WhatsApp thread, only AFTER she answers M-NUDGE with anything other than no.
WHY IT EXISTS: M-NUDGE ends "dígame y le cuento en dos líneas, sin compromiso" and then told whoever
read it to capture her Q2 answer — while no message in this system asked Q2 in two lines. The only
artifact that asks Q2 was M2: ~150 words, the full offer, marked DO NOT RE-SEND in the form she already
received, and never linked from the M-NUDGE section. So her "sí" would have landed on an agent with
nothing to say, in the one moment her attention is actually spent. This is that message. (Finding 23.)
NOT M2: M2 is the cold-open offer for a first contact. She has had it. This is the promised short version.
WHAT IT DOES NOT ASK: Q3 ("¿aceptaría SUPER otra vez?") — that is a post-meal question and belongs to the
loop box, not here. Q1 is answered by whether she says yes to this.
EVERY FIGURE IN IT IS REDEMPTION.md's, checked 2026-10-05: 100 SUPER = ₡40,000 · colones same day if
asked before 3pm, never more than 24h · or spent with another person at the full ₡40,000 · valid to
2026-12-31. If REDEMPTION.md changes, this text is wrong until it is re-synced.

TEXT (send verbatim, or change any word — it is your name on it):

> Es así: James quiere pagarle la comida de las diez personas con SUPER en vez de colones. Tiene apartados
> 100 SUPER, y 100 SUPER = ₡40,000 — usted elige: colones el mismo día si lo pide antes de las 3 de la
> tarde (nunca más de 24 horas), o gastarlos con otra persona que los acepte, por los ₡40,000 completos.
> Vale hasta el 31 de diciembre de 2026.
> En el mensaje de setiembre le puse yo el número sin preguntarle el precio, y eso no estuvo bien.
> Dígame usted: ¿cuánto cobraría por los diez casados? Si pasa de ₡40,000, dígamelo igual — prefiero
> saber el precio justo que pedirle que lo rebaje.
> Y si le sirve, una última: ¿qué haría usted con los SUPER? Un "no" a todo está perfecto y le agradezco igual.

### AMENDMENT 2026-10-05 19:20Z (13:20 CR) — finding 23, Claude, Super Agent
Measured, not supposed: grep of every .md in core/SUPER found no second message behind M-NUDGE's
"dos líneas" promise, and no M-NUDGE-2 of any name. For two cycles this draft was reported — by me, in
memory and in the ledger — as "send-ready, no bracket left". It was send-ready as a FIRST message and
not as an exchange: the single act condition 1 depends on, asking "¿y qué haría usted con los SUPER?",
had no text anywhere, and the approved bot channel that could have asked it has been mute since
2026-09-03 22:15Z (B-08). Nothing reached her and nothing was lost — the message was never sent — but
had it been, the gap would have opened in the live moment of her attention, which is the most expensive
place in this whole system for a gap to open.
Same class as findings 10 and 21, moved one beat later: an artifact read as complete against a rule it
never satisfied. 10 and 21 were about our clock. This one is about her reply.
FIXED INSIDE REMIT, no new ask on James: M-NUDGE-2 written above, the capture instruction now points at
it, and the figures are synced to REDEMPTION.md as of today. The ask is still one forward plus, if she
answers, one more — he now has words for both instead of one.
RULE: AN ASK IS NOT READY UNTIL THE REPLY IT INVITES HAS A MESSAGE WAITING FOR IT.
Corollary to finding 21's corollary: "send-ready" must name which message is ready, or it is a claim
about a conversation made on the evidence of one line of it.
STATE, unchanged by this amendment: candidate #1 La Cocinona de Pueblo is LIVE and NOT rested; candidate
#2 is CLOSED; nobody has been contacted; no funds moved; REDEMPTION.md untouched; the one-candidate guard
holds. Next open window: Sat 2026-10-11 12:00-21:00 CR.

### AMENDMENT 2026-10-05 23:20Z (17:20 CR) — finding 25, Claude, Super Agent
THE NUMBER IN THIS MESSAGE WAS NEVER HERS TO BE TOLD. BUILD_001.md commits 100 SUPER for ten plates with
`mixed_payment_ok: no`; at the ₡400 peg that is **₡4,000 a plate**, a figure derived from the escrow divided
by a round number of guests and from nothing else — no quote, no menu, no market observation. Meanwhile
PROVIDER_CANDIDATES.md line 16 has said since day one "**Ask a price in SUPER for 10 plates**", and line 1
names the risk for THIS candidate: "may treat a foreigner's 10-plate order as hospitality — **insist on a
quoted price in SUPER**." Mensaje 2 told her instead, and has been in her phone since 2026-09-03 15:12Z.
This section, written eight hours earlier the same day to repair finding 23, carried the told price forward.
Market check this cycle, named for what it is: casado at a local soda **$5–8** (costarica-spirit.com, pub.
2026-07-27) and **₡4,500–₡7,500** (entercostarica.com). Our ₡4,000 is at or below the bottom of the second.
NOT ESTABLISHED: what she charges, or that either source speaks for Rivas. Nobody has asked her — that is
the finding. She is #1 of 7 in Rivas at 5.0 and grows her own produce; the Card asks for a casado completo.
WHY IT IS NOT ABOUT ₡10,000: pass condition 1 is "accepted **freely**", and with mixed payment forbidden and
no branch anywhere for "her quote exceeds the commitment", the only yes we left her is a yes below her own
price — the hospitality trap our own file predicted, manufactured by our own message. The vendor rule would
then file FAVOR-NOT-EXCHANGE and refuse to book, catching the symptom of a defect we introduced. And the
Build asks "can SUPER carry the loop on its own weight?" — a discounted yes grades her goodwill, not SUPER.
CLASS: NEW. Forward-chain to the next silence (finding 24) **passes this draft**: every slot is filled, every
promise keepable, all over WhatsApp. It checks whether a slot has a message and never whether the message's
figures are ours to state.
TEST ADDED — **STANDING CHECK ON EVERY NUMBER**: for each figure in a message, name who set it and whether
it is ours or theirs. Ours: the peg, the redemption terms, the escrow, the deadline, how many guests.
Theirs: **what the food costs.**
FIXED ABOVE, inside remit, no new ask on James: the offer keeps every figure we can back and the plate price
becomes her question, with the gap named out loud and the earlier quoting owned in one line. COST NAMED:
this is now longer than the "dos líneas" M-NUDGE promises her — seven lines, not four. I took the length over
the alternative, which is asking her to price a meal after we already told her what we would pay for it.
NO NEW BLOCK, and one fewer decision: price × plates = escrow, so her number, the plate count and **B-13**'s
resize are ONE decision, not three — answer B-13 and B-15's headcount together, and both get cheaper the
moment she says a number.
RULE: A MESSAGE THAT STATES SOMEONE ELSE'S NUMBER AS SETTLED HAS PRE-ANSWERED THE ONLY QUESTION THAT MAKES
THEIR YES FREE.
STATE, unchanged: candidate #1 La Cocinona de Pueblo is LIVE and NOT rested; candidate #2 is CLOSED; nobody
contacted; no funds moved; REDEMPTION.md untouched; the one-candidate guard holds. Next open window:
Sat 2026-10-11 12:00–21:00 CR.

## M-NUDGE-3 — what we say after she answers Q2 (drafted 2026-10-05 15:10 CR, NOT sent)
WHO SENDS IT: James, same WhatsApp thread, immediately after she answers Q2 in M-NUDGE-2.
WHY IT EXISTS: finding 24. Walking the chain forward from M-NUDGE-2, the next act is hers (her Q2
answer) and then OURS — and the only message that existed for that slot was "Mensaje 3", written for a
cold-open sequence, never linked from M-NUDGE-2, and promising "James la va a llamar": a voice call,
which finding 20 established this system does not own. Worse, what M3 says it will confirm — la fecha —
does not exist and cannot be made to exist by anyone but James: `day1`/`day7` are blank and
`beneficiaries`/`witness` are blank (condition 2, B-15, open 33 days). So her second "sí" would have
been answered either with a promise of a call that never comes, or with silence — the same silence that
already cost her thirty days, this time after a month-late apology. That is the most expensive silence
in this system.
WHAT IT DOES: tells her the truth — nothing is reserved, the date does not exist yet and why, the next
message comes over this same thread, and she may chase us. It asks her for NOTHING and reserves NOTHING.
NO TIMER: it names no date (findings 10, 21). The obligation it creates runs on US, not on her, and
nothing in this system rests her or opens another candidate on the strength of time we did not spend.

TEXT (send verbatim, or change any word — it is your name on it):

> Gracias, doña. Se lo anoto con sus palabras, tal como me lo dijo.
> Todavía no hay nada reservado, y no le voy a pedir que aparte comida sin fecha: primero tengo que
> hablar con las diez personas para saber qué quieren comer. En cuanto lo tenga, le escribo por aquí
> mismo con la fecha y los diez platos, y ahí usted dice sí o no, sin compromiso.
> Si pasa el tiempo y no le escribo, escríbame usted y pregúnteme — tiene todo el derecho, ya la dejé
> esperando una vez.
> Y si en algún momento esto le cuesta más de lo que le da, dígamelo y paramos.
> (Mi asistente de inteligencia artificial me ayuda a escribir; los acuerdos los confirmo yo. — James)

### AMENDMENT 2026-10-05 21:10Z (15:10 CR) — finding 24, Claude, Super Agent
TWO defects, both measured in the files, not supposed:
(1) THE CHAIN TERMINATES ON THE STEP WE SKIPPED. `super_build.py status BUILD_001.md` states its own NBM
    as "director-only first — (a) name the beneficiaries and a witness ... then (b) one conversation with
    one candidate provider". Condition 2 (beneficiaries + witness) is ✗ and has not moved in 33 days;
    condition 1 (provider + Q2 verbatim) is the one four cycles of work have been aimed at. Even with her
    Q2 captured, #001 goes 2/4 → 3/4 and NO MEAL CAN BE ORDERED: the Card's own pass test is "a meal they
    WANTED", and nobody has asked ten people what they want. So the provider path has been polished to the
    exact point where it must stop and wait on the path nobody is moving — and every cycle's WAITING ON
    JAMES list has led with M-NUDGE, step (b), while the machine underneath it said (a) first.
(2) THE POST-Q2 SLOT HELD A MESSAGE WE CANNOT KEEP. Mensaje 3 is the only text for that slot, is not
    linked from M-NUDGE-2, and promises a voice call (finding 20: WhatsApp is the only channel we own)
    to confirm a date that does not exist. Marked DEFECTIVE above; M-NUDGE-3 replaces it for this thread.
Class: findings 10, 21, 23 — an artifact read as complete against a rule it never satisfied — now at the
FOURTH beat. 10 and 21 were our clock; 23 was her reply; this one is her SECOND reply.
FIXED INSIDE REMIT, no new ask on James: M-NUDGE-3 written; Mensaje 3 marked defective; the ask order
corrected so B-15 leads and M-NUDGE follows, with the reason named.
THE METHOD I SAID I DID NOT HAVE (cycle 23, recorded as an open disagreement with my own audit): I wrote
that an artifact must be read against the NEXT act it invites and that I did not know what does that.
This cycle did it, and the method has a name — FORWARD-CHAIN TO THE NEXT SILENCE. Walk the acts forward
from the ask, alternating ours and theirs, and at every point where the other person is waiting on US
ask three questions: what message exists in this slot, can we keep what it promises, and over what
channel. Stop at the first slot that fails. It found both defects above in one pass, and it is the first
test in this audit that looks past the artifact in hand. It is a test, not a guarantee: it cannot see a
slot whose act I failed to imagine.
RULE: A MESSAGE IS NOT READY UNTIL EVERY SILENCE IT CREATES HAS A MESSAGE WE CAN KEEP.
STATE, unchanged: candidate #1 La Cocinona de Pueblo is LIVE and NOT rested; candidate #2 is CLOSED;
nobody contacted; no funds moved; REDEMPTION.md untouched; the one-candidate guard holds. Next open
window: Sat 2026-10-11 12:00-21:00 CR.
