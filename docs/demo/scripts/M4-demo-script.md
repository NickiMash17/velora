# M4 Demo Script — Organization Experience

**For:** presenting `M4-walkthrough.mp4` (or the live app) to investors, recruiters, or judges
**Length:** ~2 minutes of narration, matched to a ~2:10 walkthrough recording
**Tone:** confident, plain-language first, technical credibility second — the audience decides which half they need

---

## Opening — what Velora is (before you share your screen, or over the first few seconds)

> "Velora is an AI workforce platform. Businesses don't want another chatbot bolted onto their existing software — they want to hire digital employees: named, accountable team members that actually do the work, the way a real hire would, with a manager who can see what they're doing and step in when it matters.
>
> That's the vision. What I'm going to show you today is the foundation everything else gets built on: how a business actually gets *into* Velora in the first place. It looks simple. Getting it right — securely, and in a way that scales to real customers — is most of the work nobody sees."

## The problem this slice solves

> "Before someone can hire a digital employee, three things have to be true: they need an account, they need to be securely logged in, and they need a workspace — an organization — that everything else in the product hangs off of. Get any one of those wrong and nothing else matters. So this milestone is deliberately not flashy. It's the plumbing a serious product is built on, not a demo of AI novelty."

---

## Walking through it (timestamps match `M4-walkthrough.mp4`)

**0:00 – 0:14 — Landing on the login screen**

> "This is a real, running product — not a mockup. What you're looking at is the actual app, on my machine, right now. No account yet, so we start at login."

**0:14 – 0:26 — Registering**

> "I'll create an account the way any new customer would — email and password. Notice there's no fake friction here: no email verification loop, no CAPTCHA theater. Under the hood, that password is never stored in plain text — it's hashed with Argon2id, which is the current industry-recommended standard, the same class of protection a bank uses."

**0:26 – 0:40 — Landing on organization creation**

> "Immediately after signing up, Velora asks the one question that actually matters at this stage: what's your organization called? Not industry, not company size, not fifteen fields nobody wants to fill in on day one. Just a name. Everything else about the product hangs off this — but we don't make someone configure things we haven't built yet."

**0:40 – 0:50 — Creating the organization**

> "I'll type in a name and create it."

**0:50 – 1:15 — The dashboard**

> "And that's it — we're in. This is the organization's home: its name, its plan, who's signed in, and their role. It's intentionally minimal right now. I want to be very direct about that: there's no fake activity feed, no placeholder 'Digital Employees' with zero next to them. If a feature isn't real yet, it doesn't get a pretend version — that's a deliberate engineering principle for this product, not a limitation I'm glossing over."

**1:15 – 1:23 — Theme toggle**

> "Small thing, but worth ten seconds: light and dark mode both work, fully, right now — not just on the login screen."

**1:23 – 1:31 — Signing out**

> "Signing out is a real, clean action — not just clearing a browser tab."

**1:31 – 2:10 — Logging back in**

> "And here's the part that's easy to take for granted and hard to get right: I log back in with the same credentials, and I land straight back on my organization's dashboard — no re-onboarding, no 'create your organization again.' That persistence, securely, is a genuinely non-trivial engineering problem, and it's the reason this milestone took real architectural work, not just a login form."

---

## Why each piece matters (have ready if asked, don't over-explain unprompted)

- **Passwords hashed with Argon2id, tokens never stored where a script could steal them** — security was designed in from the first login, not retrofitted after a breach headline forced the issue.
- **Every organization's data is walled off at the database level**, not just hidden in the UI — even a bug in application code cannot leak one customer's data to another. This is enforced by Postgres itself (Row-Level Security), which is the same class of guarantee regulated industries require.
- **The "create an organization" step and "log back in" step are the same underlying mechanism** — a session securely picking up where it left off. That consistency is what makes it reliable instead of held together with special cases.

## How the architecture supports it (for a technical audience)

> "This runs on a modular monolith — one deployable FastAPI backend with clean internal module boundaries, and a Next.js frontend. That's a deliberate choice: we get the simplicity of one system to deploy and reason about today, with real seams already in place to split into services later, if and when scale actually demands it — not speculatively now. Multi-tenancy is enforced with Postgres Row-Level Security, and every milestone ships with its own automated test suite — this one shipped with over 150 backend tests plus a real end-to-end browser run, not just 'it worked when I clicked through it once.'"

## Current milestone

> "This is Milestone 4 of the platform: the Organization Experience. Milestones 1 through 3 built the platform foundation, the multi-tenant data layer, and secure authentication — all real, all tested, entirely behind an API with nothing to look at. This is the first milestone where that foundation becomes something a person can actually open and use."

## What's coming next

> "The natural next step is letting an organization admin invite teammates — that's what turns 'an organization' into 'a team,' and it's the foundation the actual AI workforce features get layered on top of after that. We're building this deliberately, one real, working slice at a time — no feature ships until it's genuinely real, tested, and demonstrable, which is exactly what you just watched."

---

## Presenter notes

- If asked "is this real or a prototype UI" — the honest answer is: real, working, tested backend and frontend, deliberately minimal scope. Say that plainly; don't oversell.
- If asked about AI features — be direct that this milestone is pre-AI-runtime by design (identity → data layer → auth → this), and point to the roadmap rather than improvising a feature that doesn't exist.
- Don't demo the ">1 organization" switcher screen — it exists in code but has no real path to it yet (no invite feature). If asked directly, say so; don't route around it to force a screenshot.
