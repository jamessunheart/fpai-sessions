# Zen Village — Applicant Follow-Up Handover → Suri

**CONFIDENTIAL — contains applicant contact details and personal/health notes. Share only with Suri + James.**

Prepared 2026-06-09 · Hands the Zen Village applicant follow-up role from **Atlas & Halley → Suri**.

---

## 0. For James — 3 setup steps (≈5 min, all in the cockpit UI)

Cockpit: **https://zenvillagecr.com/cockpit** (log in as owner).

1. **Create Suri** — Members/Users → add user
   - username `suri` · role **member** · surface **submissions** (add `bookings`/`inbox` if she'll also handle those)
   - set a starting password, send it to her, tell her to change it on first login
2. **Revoke Atlas** — delete the `atlas` user
3. **Revoke Halley** — delete the `halley` user

If the UI has no delete control, tell me — I can do the revoke + create via the server API (one-time prod approval) instead.

> Note: **Atlas Blake is also an applicant** (scored 64, see below) — that's a separate person-record from the `atlas` staff login. Revoking the login does not touch the application.

---

## 1. The scoring system (now automatic again)

Every new application is auto-scored hourly. No manual step.

- **Pipeline:** server pulls each lane's applications → new ones scored by Claude → ranked output lands locally + feeds the cockpit.
- **5 dimensions, 100 pts:** Alignment · Skills · Community Fit · Readiness · Application Depth.
- **Tiers:** 🟢 Strong Recommend / Good Fit (≥70) · 🟡 Warm Lead (55–69) · ⚪ Needs Info / Pass (<55).
- Each scored applicant gets a one-paragraph summary, key skills, and ⚠ flags to probe on the intake call.

*(This had silently broken on ~June 5 when the source files were lost; restored + committed 2026-06-09. Now self-healing hourly.)*

---

## 2. Suri's playbook

1. **Work top-down.** Contact the 🟢 group first (7 people). They're the highest-fit and several are already in Costa Rica = low logistics friction.
2. **Read the ⚠ flag before each call** — it's the one thing to verify (a claim, a gap, a logistics risk, a duty-of-care item).
3. **In the cockpit**, mark each as `contacted` then `closed` so the queue stays honest (KPI shows anyone "slipping" > 48h).
4. **🟡 Warm Leads** — review after the 🟢 group; reach out only if there's capacity.
5. **⚪ group** — low priority; most are blank/incomplete submissions.

---

## 3. Ranked applicant queue (auto-scored · 17 total)

### 🟢 Strong / Good Fit (≥70) — CONTACT FIRST

| Score | Name | Lane | Contact | Probe (⚠) |
|------:|------|------|---------|-----------|
| 86 | Moritz Anton Münzer | practitioner | muenzer.dnomad@gmail.com · +506 7029 5051 | No communal-living experience — explore fit for shared living |
| 84 | Eric John | work-exchange | Ericjohnwagner@gmail.com · +1 435 994 5209 · @EricJohn.777 | Left a prior village over conflict culture — ask for his account |
| 81 | Ana Teresa Bacalao | work-exchange | anateresabacalao@gmail.com · +1 647 239 0190 · @anatbacalao | Self-described "vulnerable period" — check giver/receiver balance |
| 80 | Maria Del Pilar Castro | practitioner | mariadelpiar.cde@gmail.com (⚠ likely typo — confirm) · +506 8924 4596 · @soypilipili | Verify email before outreach |
| 78 | Kyra Thompson | practitioner | kyramthompson30@gmail.com · +1 864 631 5121 · @kyra__thompson | Day-trip/weekend only — clarify a recurring anchor slot |
| 71 | Dayanne | practitioner | sirenaenlaselva@gmail.com · +1 727 687 2550 · @sirena.en.la.selva | No references — request at least one |
| 70 | Nathan Phillips | work-exchange | videosbynate@gmail.com · +1 317 605 7862 · @n8.clarence | No communal-living experience — assess maturity (⚠ also submitted a blank dup, score 13) |

### 🟡 Warm Lead (55–69) — review, reach if capacity

| Score | Name | Lane | Contact | Probe (⚠) |
|------:|------|------|---------|-----------|
| 67 | Taylor Carter | work-exchange | cheftaylorcarter@gmail.com · +1 213 247 0951 · @taylormychaelcarter | Mission statement cut off mid-sentence — ask the finish |
| 66 | Brianna Cooper | work-exchange | bri.juliette637@gmail.com · +1 310 406 6467 · @b.jewelz | Healing/seeking framing — verify stable place to contribute |
| 65 | Katrina Anastasia | work-exchange | stayconnected.kat@gmail.com · +1 647 964 4647 · @katrina.anastasia | Met James at Envision; Cheyenne referral · Nov start — see if it accelerates |
| 64 | Atlas Blake | practitioner | atlasrblake@gmail.com · +1 858 867 9217 · @atlasofmans | Already on-site · 1,500-audience claim unsupported — ask specifics |
| 63 | William Seth Wade | work-exchange | williamsethwade@gmail.com · +1 646 771 1967 · @beverly_killbilly | Currently in a NYC shelter — verify pathway to Costa Rica |
| 61 | Christopher Turcotte | work-exchange | christopherturcotte@yahoo.com · +1 925 234 5471 | No communal-living experience — first shared space |
| 55 | Megan Lockwood | practitioner | Newmoonintentions.co@gmail.com · +1 203 919 2482 · @newmoonintentions | Already on-site (Quesada) · experience field blank |

### ⚪ Needs Info / Pass (<55) — low priority

| Score | Name | Lane | Contact | Note |
|------:|------|------|---------|------|
| 50 | John Douglas Kennedy | work-exchange | jdmkdesign@gmail.com · +1 905 965 2800 | Duty-of-care: confirm uninterrupted medication access + rural-CR healthcare plan before any acceptance |
| 40 | Si ("Firefly") | work-exchange | si.firefly88@gmail.com · +1 780 914 2608 | Already on-site but application essentially blank |
| 13 | Nathan Phillips | work-exchange | videosbynate@gmail.com · +1 317 605 7862 · @n8.clarence | Blank duplicate of the score-70 entry |

---

*Full per-applicant detail (all 5 dimension scores + notes + key skills) lives in the scored JSONs at `~/.config/fpai/zen_village/applicants/scored/` and on the cockpit Submissions surface.*
