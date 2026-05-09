# INVITE_TEMPLATES.md

Templates for `/invite` on `@sunheartbrain_bot`. Each is a starting point — edit before sending if it doesn't fit the relationship. The bot picks the template by the heading slug you pass: `/invite NAME contact path` → matches `## path`.

**Variables** (substituted by the bot):
- `{NAME}` — invitee's first name
- `{WHY_THEM}` — one-line specific to this person ("you'd love this because…"); bot leaves blank for you to fill, or you can pass it inline
- `{TRACKED_LINK}` — `https://fullpotential.com/game/?inviter=James%20Sunheart` (auto-filled to the inviter's canonical name; champion-sign wires this to affiliate score)

**Default path** is `game`. **Voice register**: matches public site (Coherent Champions, World Peace Agreement, Character Card, Field Score). Strip the heavier framing for friends who'd resist it.

**Length variants**: each path has an email-length form (`## path`) and a WhatsApp-length form (`## path-wa-short`). The WhatsApp short forms are 1–3 lines, designed for first-touch on phone — no sign-off, no preamble, just frame + link. `scripts/cohort/wa-invite.sh` reads them.

---

## village

{NAME} —

{WHY_THEM}

We just started *The Village* — a daily 8 PM mockumentary at Camp Zen. Each day everyone shares whatever they share normally in our Telegram group (also called The Village); an AI editor named Kai listens silently and weaves the day into a short film we watch together at the dining hall.

You're not making content. You're just being in the village. The film is the byproduct. Your first share is your first Proof in the Game.

Two things you need: (1) join The Village TG group https://t.me/OfficialKaibot; (2) anything you'd rather not see in a cut, just say so or DM me. That's it.

Day 1 is 2026-05-09. Curtain at 8.

— James

---

## village-wa-short

{NAME} — opening Day 1 of *The Village* tonight (Camp Zen mockumentary, 8 PM dining hall). You're invited as a co-builder. Join the TG group: https://t.me/OfficialKaibot. Just be in the village; an AI editor named Kai patches the day into the cut. — J

---

## game

{NAME} —

{WHY_THEM}

I'm building Full Potential — a Game where Coherent Champions sign a World Peace Agreement, build a Character Card, run a 7-Day proof loop, and earn Field Score from witnessed reality (not vanity metrics).

Many paths from there: live near the village in Costa Rica, apprentice with me, come to a retreat, throw a party with us, sponsor it, get coaching, just witness. You enroll once, the path that fits comes after.

The substrate is live. I'm Champion #1. Looking for the first 5–10 humans in.

{TRACKED_LINK}

— James

---

## game-wa-short

{NAME} — Full Potential Game's live: {TRACKED_LINK}

I'm beta-testing now. Take a look, sign if you want, lmk what's broken.

---

## apprenticeship-wa-short

{NAME} — Full Potential Game's live: {TRACKED_LINK}

Looking for ~3 to apprentice with directly. Sign in, AI Port-In card asks the questions. Talk after.

---

## village-wa-short

{NAME} — building Full Potential at the village: {TRACKED_LINK}

Looking for 3–5 humans living near for a season+. Sign in, hit the Village interest path.

---

## witnessing-wa-short

{NAME} — quick ask: be a Witness in something I'm building. {TRACKED_LINK}

Sign in, opt into Witness Roster from your dashboard. Low time, high signal.

---

## retreat-wa-short

{NAME} — first Zen Village retreat is forming, Costa Rica, ≤10 cohort. {TRACKED_LINK}

Sign in + file retreat-interest from your Player State. Date/price set when first 3 commit.

---

## apprenticeship

{NAME} —

{WHY_THEM}

Running Full Potential and looking for ~3 people to apprentice with directly. You'd build this with me — your project pulls into the substrate, mine pulls into yours. The Game tracks both.

{TRACKED_LINK} — sign in, the AI Port-In card asks the right questions. We talk after.

— James

---

## witnessing

{NAME} —

{WHY_THEM}

Short ask: be a Witness in something I'm building. Full Potential Game has a Witness Roster — people who watch the field, ratify proofs, hold the rhythm. Low time, high signal, no commitment past attention.

{TRACKED_LINK} — sign in, opt into Witness Roster from your dashboard.

— James

---

## commerce

{NAME} —

{WHY_THEM}

Building Full Potential — a substrate where Champions enroll, build Cards, ship Proofs. Currently bootstrapping. Looking for sponsors / first investors for the first retreat (Costa Rica) and the broader village around it.

{TRACKED_LINK} — the dashboard shows what's live. Happy to walk you through what's needed and what the unit economics look like.

— James

---

## coaching

{NAME} —

{WHY_THEM}

Running coaching inside Full Potential. You sign in, build your Character Card (Aspirational + Reality layers), we work the gap weekly. The Card walks you through the questions; sessions hit the points where the Card stalls.

{TRACKED_LINK} — sign in and start the Card. We sync after your first proof.

— James

---

## retreat

{NAME} —

{WHY_THEM}

First Zen Village retreat is forming — Costa Rica, intimate cohort (≤10). The Game's substrate handles enrollment + cohort matching; we're filling cohort #1 now.

{TRACKED_LINK} — sign in and file retreat-interest from your Player State. Date and price are set once the first 3 are committed.

— James

---

## party

{NAME} —

{WHY_THEM}

Sunheart house party / Full Potential gathering — [DATE TBD]. Champions, Witnesses, Solvers, music, problem jams, Oracle stage. The Game has a Party path; RSVP and you're in.

{TRACKED_LINK}

— James

---

## village

{NAME} —

{WHY_THEM}

Building a village in Costa Rica around the Full Potential Game. Couches, jam boards, music, problem jams, Oracle stage. Looking for 3–5 humans to live nearby for a season or longer.

{TRACKED_LINK} — sign in, the dashboard has a Village interest path.

— James
