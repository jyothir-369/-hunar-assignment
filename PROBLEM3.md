# Problem 3 — Attendance Tracking Without Smartphones

> **The constraint:** There are no smartphones, and therefore no apps. But LLMs exist,
> and "everything else" is on the table: voice/IVR, telephony, biometric hardware,
> RFID, SMS, kiosks, fixed cameras, even paper registers.
>
> **The job:** Track the daily attendance of 1,000 employees across 100 locations.

---

## TL;DR

I'd build a **multi-channel attendance system** with no single point of failure. The
default channel is a one-question **voice/IVR check-in** triggered by a daily
**Hunar-style outbound AI call** at the start of each shift — this works on any phone,
landline or mobile, and gets us to ~80% coverage on day one. Layered on top:

- **Shared kiosk / biometric devices** (fingerprint or face) at the larger sites
  for higher accuracy and zero-friction check-in
- **Supervisor SMS / WhatsApp** fallback for sites without kiosks
- **A daily reconciliation LLM** that reasons across all channels, flags anomalies
  (e.g. a "present" voice check from a number that's never called before, two check-ins
  in different cities within an hour, ghost workers), and produces a single
  auditable attendance ledger for HR

Every channel feeds the same ledger; the LLM's job is to make the messy multi-source
reality usable for an HR person.

---

## 1. What "no smartphones" actually rules out

It's worth being explicit, because "no apps" doesn't mean "no tech":

| Excluded | Still available |
|---|---|
| Native mobile apps, push notifications | Landlines, basic mobile phones (voice + SMS only) |
| QR codes scanned from a personal phone | Printed QR codes, barcode badges, RFID badges |
| GPS from a personal device | Fixed-site check-in (kiosk, biometric, RFID reader) |
| Biometric unlock of a personal phone | Dedicated fingerprint/face hardware at the site |
| Web dashboards on personal devices | Web dashboard for HR on a desktop PC |
| "Sign in with Google/Apple" | OTP over SMS, voice OTP, supervisor confirmation |

The shape of the problem is therefore: **the *employee* has no smart device in
their pocket, but the *site* and the *HR function* can be as instrumented as we
like.** That changes the architecture.

---

## 2. The voice-first default channel

The single most important thing is that **almost every employee has *some* phone
number on file** — a mobile, often a landline at the site. So the default check-in
path is a **voice call**:

1. At the start of each shift, the system places an **outbound call** (powered by a
   voice AI agent — exactly the Hunar technology we've already integrated) to every
   employee's number. The call is in the local language, lasts 10–20 seconds, and
   asks for a single spoken "Yes" to confirm presence.
2. The **LLM behind the agent** does:
   - **Speaker verification** from the voiceprint (re-using the LLM's ability to
     compare short voice clips; this catches the "I called in for my friend"
     problem)
   - **Anti-spoofing** by detecting playback / synthetic voices
   - **Transcription + intent classification** — "yes" / "I'm on the way" /
     "I am sick today" all map to a structured result the system can act on
3. If the call is missed (no answer in 30s), the system:
   - Retries once after 5 minutes
   - Then escalates to an **IVR pull channel** — the employee can call a free
     number from any phone and punch in their employee ID + a one-time voice OTP
4. If both outbound and inbound fail, the system falls back to **SMS** (works on
   any phone that can receive texts, including feature phones):
   - "Reply Y to mark present, N to mark absent, L for leave."
   - The LLM parses free-form replies ("I'll be late by an hour" → late arrival
     with reason) so HR doesn't have to re-read everything.

This single channel alone covers the **vast majority of cases** because we own
the call — we don't need the employee to remember to do anything.

### Edge cases the voice channel handles well

- **Noisy factory floor** — the agent asks the user to step away, or the
  supervisor triggers a re-call from a quieter phone.
- **Language diversity across 100 sites** — we deploy 10–12 language personas;
  the LLM picks the right one based on the employee's profile.
- **Emergencies** — if the agent hears distress words ("accident", "hurt"), the
  call is escalated to a human supervisor immediately.
- **Disability / speech difficulty** — the agent can switch to a DTMF (keypad)
  fallback: "Press 1 for present, 2 for absent."

---

## 3. Site-level hardware for higher-fidelity check-in

Voice is the *baseline*. For the larger or more sensitive sites, add hardware:

| Hardware | Where it shines | What it gives us |
|---|---|---|
| **Fingerprint / face biometric kiosk** | Factory gates, large offices | Hard-to-forge identity, fast throughput, no employee action needed |
| **RFID badge reader** | Warehouses, secure sites | Hands-free, works through gloves, integrates with access control |
| **Fixed IP camera + LLM vision** | Gates, lobbies | Visual confirmation; the LLM extracts face + matches against the roster |
| **Printed QR at the gate** | Anywhere you can mount a poster | Employee scans with a *shared* site tablet (not a personal phone) — the tablet is the device, not the phone |

The rule of thumb: **spend hardware budget on the 20% of sites that hold 80% of
the headcount.** A 200-person factory gets a biometric kiosk. A 4-person branch
office in a rural town uses the voice channel only.

A key design choice: every piece of site hardware **uploads to the same central
ledger** as the voice channel. The system never assumes a single source of truth.

---

## 4. Supervisor fallback (the human safety net)

For the small sites that can't justify a kiosk, the supervisor is the channel:

- Every supervisor gets a **shared tablet or laptop** at the site (not a personal
  phone — it's a company asset, so it doesn't violate the "no personal smartphone"
  rule for employees who don't have one).
- The supervisor **confirms attendance for the shift** once, in a 30-second
  voice/IVR call to a toll-free number, or by sending a structured SMS like
  `P 12 4` (present: 12, absent: 4).
- The LLM **parses the SMS** and reconciles against the per-employee voice
  check-ins — if 12 people confirmed by voice but the supervisor says 4 are
  absent, the LLM generates an exception report ("Aarav marked present by voice
  at 09:03 but supervisor marked absent. Possible spoof?"). The supervisor
  doesn't have to be 100% accurate because the system is the one making the
  final call.

This is also the channel that handles the **disconnected-from-network**
problem: at remote sites, the supervisor's tablet queues check-ins and uploads
once a connection is available. The LLM at the centre handles the "we just
received 30 minutes of queued check-ins, please slot them in" case cleanly.

---

## 5. The LLM's actual job: daily reconciliation

The single most valuable thing the LLM does is **not** the voice interaction.
It's the daily reconciliation pass at the end of the day. This is where the
"LLM as reasoning engine" idea actually pays off.

Each evening, the LLM ingests:

- All voice check-ins (timestamp, phone number, voice confidence, location)
- All biometric / RFID / camera events from site hardware
- All SMS confirmations
- All supervisor reports

…and produces:

1. **A per-employee attendance verdict** for the day: present / absent / late /
   leave / unverified, with a confidence score.
2. **A short, plain-English summary for HR**, e.g.
   > *"988 present, 9 absent (4 with approved leave), 3 unverified. Exceptions:
   > Aarav Sharma — voice said present from a number not on file, no biometric
   > match at the gate, supervisor marked absent. Recommend manual review. Priya
   > Iyer — biometric at 09:12, voice at 09:14 (different number), supervisor
   > confirmed. OK."*
3. **A weekly payroll-ready export** that handles partial days, late arrivals,
   overtime, and the inevitable "I was there but the system didn't see me" cases
   in a way an HR person can actually read.
4. **Anomaly flags** for things like:
   - Buddy-punching (one voice claiming to be two different people)
   - Geo-impossibility (claimed to be at site A and site B within an hour)
   - Pattern anomalies (an employee who's "always late on Mondays" — useful
     coaching signal, not just a number)

This is the part where an LLM genuinely earns its place over a rules engine —
the reconciliation is fuzzy, multi-source, and benefits from natural-language
summaries that a non-technical HR manager can act on.

---

## 6. Privacy, consent, and the "creepy" line

Voice biometrics and face recognition are sensitive. The system has to be
designed around three principles:

1. **Collect only what's needed.** We don't need the *content* of every call —
  just the timestamp, the speaker ID, and the intent. Store transcripts as
  short summaries, not full audio, unless an exception requires drilling in.
2. **Explain every decision.** When the LLM marks someone absent, the HR person
  must be able to click and see *why*. Black-box "the AI said so" is a
  non-starter for payroll.
3. **Employee opt-in with a real alternative.** Every employee is told, in their
  language, exactly what's being recorded and why. The opt-out is the
  IVR/SMS path, which is no-record-by-default. We do not penalise people for
  choosing the lower-fidelity channel — we just mark them with a lower
  confidence score and the supervisor confirms.

The result is a system that's *defensible*: when an employee asks "why was I
marked absent," there's a clear chain of evidence they (and a labour-court
judge) can review.

---

## 7. What this would look like in practice

| Site type | Headcount | Hardware | Primary check-in | Fallback |
|---|---|---|---|---|
| Large factory | 200 | Biometric gate + 2 kiosks | Fingerprint at the gate | Voice call |
| Medium office | 50 | RFID + supervisor tablet | Badge tap on entry | Voice call |
| Small branch | 8 | None | Voice call at shift start | SMS to supervisor |
| Field worker | 1–2 | None | Voice call to landline at site | Supervisor call-in |
| Remote / disconnected | varies | None, intermittent data | Supervisor tablet, queued | Voice call once signal returns |

Across 100 sites and 1,000 employees, the **expected channel mix** after a
quarter of operation is roughly:

- ~70% biometric / RFID (large and medium sites, where the headcount lives)
- ~20% voice (small branches, field, late arrivals, overrides)
- ~8% SMS (sick-leave notifications, ad-hoc check-ins)
- ~2% supervisor (genuine exceptions, dispute resolution)

That mix means the LLM reconciliation layer is doing real work every day —
it's never just one clean source — but the system as a whole is robust to
*any single channel failing*. If a biometric kiosk goes down for a day, the
voice and SMS channels still get 95% of the headcount marked correctly.

---

## 8. What I'd build first (the first 30 days)

1. **Week 1 — Voice channel only.** Stand up the outbound AI calling system
   (this is essentially a thin wrapper around the same Hunar integration we've
   built for the hiring product). One campaign per day, one question per
   employee. Measure: how many answered, how many confirmed, how many needed
   retries.
2. **Week 2 — SMS + supervisor fallback.** Add the inbound IVR number and the
   supervisor SMS path. Most "missed call" cases get resolved here.
3. **Week 3 — Hardware pilot.** Buy 5–10 biometric kiosks, deploy them at the
   largest sites. Confirm they work, confirm the data flows, confirm the LLM
   reconciliation handles the new source.
4. **Week 4 — Reconciliation + reporting.** Turn on the LLM reconciliation
   pass. Ship the HR dashboard (web, desktop) with the plain-English daily
   summary and the per-employee audit trail.

By the end of month one, HR has a system that *works* (voice + SMS covers the
majority), and a clear path to *better* (hardware rollout at the high-headcount
sites). The architecture supports both ends of that spectrum without a rewrite.

---

## 9. Why this beats the obvious alternatives

- **"Just use a register"** — fine for one site of 10 people. Doesn't scale to
  100 sites × 10 people. Doesn't give you an audit trail. Doesn't handle
  late arrivals, leaves, or disputes without a full-time clerk per site.
- **"Buy everyone a phone"** — solves the wrong problem, costs more than the
  system, and creates a new privacy headache (who owns the device, what can
  the company see on it).
- **"Use a single biometric system everywhere"** — too expensive for small
  sites, and fails the moment the device loses power or network.
- **"Just trust the supervisor"** — works until the supervisor is the one
  faking the register, or makes a typo on day 90 of doing this manually.

The multi-channel design is more code, but it's the only design that survives
*all* the failure modes — and the LLM is the piece that makes the multi-source
mess usable instead of painful.

---

## 10. One-line summary for the HR team

> *We call every employee at the start of their shift on a phone they already
> have, ask one question, and trust the answer — but verify it against every
> other signal we have. The system is invisible to the people who are where
> they say they are, and obvious to the people who aren't.*
