# Draft answers for the website assistant (ADR 0006)

**For Christopher to review. Nothing here ships until you approve it.** Each entry becomes a public statement made on
iBackHome's behalf. How to read this:

- **Q** = example questions a visitor might type (the matcher also uses keywords).
- **A** = the answer text. `{like_this}` is filled from data at request time (prices, fee, contact details), never typed
  or generated. If a number is not a placeholder, an automated test will fail.
- Facts come from the public pages (`landing.tsx`, `how-it-works.tsx`, `trust.tsx`, `pricing.tsx`, `audiences.tsx`),
  the spec and the code. Where the website and the code disagree, the entry is marked **DECIDE**.
- **Handoff** = the assistant says it can't answer that here and shows email and WhatsApp.

## A. What iBackHome is

**what-is-ibackhome**
Q: What is iBackHome? What do you do? How does this work?
A: iBackHome helps Nigerians abroad build at home. A verified supervisor visits your site and captures photo evidence of the work, and money for each stage is released only after the supervisor verifies it and you approve it. We are not a construction company: you keep your own contractor.

**construction-company**
Q: Are you a construction company? Do you build for me? Can you find me a contractor?
A: No. You keep your own contractor. We verify what they claim on site and control when money moves. *(Contractor matching: **DECIDE**. The site says you invite your contractor by phone; the pitch deck mentions matching, and no matching feature exists in the code. This entry does not promise it.)*

**how-it-works**
Q: How does it work step by step? How do I start?
A: 1) Create your project with your site address and budget. 2) Invite your contractor by phone number. 3) Your contractor prices the work in milestones (a bill of quantities) and you approve it. 4) Pin your site on the map. 5) Fund the first milestone. A supervisor then captures evidence, verifies the work, and you approve before money is released.

**where-we-work**
Q: Where do you work? Which states or cities?
A: Anywhere in Nigeria. When you set up your project, we match a vetted supervisor near your site.

## B. Money and escrow

**pilot-status** — **DECIDE (honesty)**
Q: Is it live? Is my money safe? Is this real money? Are you licensed?
A: We are in a pilot. During the pilot, payments run in test mode and no real money is held yet. We are in final talks with a licensed escrow partner, and real money will only be switched on once that partner is signed and live. For questions about the pilot, contact us at {contact_email}.
*(The public pages currently say a licensed escrow partner already holds your money. This answer uses the pilot wording. Decide whether the pages should change too.)*

**who-holds-money** — **DECIDE (same issue)**
Q: Who holds my money? Does iBackHome hold my money?
A: iBackHome never holds client funds. The design is that funds sit with a licensed escrow partner and are released only after the supervisor verifies the work and you approve it. During our pilot this runs in test mode: no real money is held yet.

**release-process**
Q: When is money released? How do payments to my contractor work?
A: Milestone by milestone. When your contractor says a stage is done, the supervisor verifies it on site with evidence. Only then can you approve, and approving triggers the release. Nothing is released before both steps.

**dispute**
Q: What if I don't agree a milestone is done? Can I dispute it?
A: Raise a dispute instead of approving. The release pauses, and our team reviews the evidence with you and your contractor. Two staff sign off the outcome: pay the milestone, or send it back for rework.

**currency**
Q: Which currency do I pay in? What about naira?
A: You pay the supervision plan in US dollars, by card. When you fund a milestone you can pay by card in GBP, USD or EUR. Your contractor and suppliers are paid in naira at the exchange rate recorded on the day you fund. You see both amounts before you pay. *(**DECIDE**: the pricing page says "US dollars" and the how-it-works page says "GBP, USD or EUR"; this entry reconciles them. Please confirm.)*

**contractor-payment**
Q: How is my contractor paid? Is the fee taken from my contractor's payment?
A: By the escrow partner, in naira, after verification and your approval. Fees are shown as separate lines when you fund a milestone. The milestone amount you agreed is what your contractor receives.

## C. Prices

**pricing-overview**
Q: How much does it cost? What are your prices? Is there a monthly fee?
A: Supervision is a monthly fee per project: Basic {plan_basic_price} a month ({visits_basic} site visits a month), Standard {plan_standard_price} ({visits_standard} visits), Premium {plan_premium_price} ({visits_premium} visits), which we recommend. On top of that there is a {funding_fee} fee on money you fund into escrow. See the pricing page for details.

**billing-periods**
Q: Is there a discount for paying yearly? Can I pay for six months?
A: Yes. Paying for 6 months costs 5 months, and paying for 12 months costs 10 months. The monthly price is on the pricing page.

**funding-fee**
Q: What is the fee when I fund a milestone?
A: A {funding_fee} fee on each milestone you fund. It is shown as its own line before you pay, and it is not taken from your contractor's payment.

**contractor-fee**
Q: Do contractors pay a fee? Is it free for contractors?
A: Handoff. *(**DECIDE**: the site has no stated contractor fee. The assistant should not guess.)*

**cancel-billing**
Q: Can I cancel? When is the monthly fee charged?
A: Handoff. *(The site leaves billing date and cancellation wording empty until supplied. Provide the wording, or keep as handoff.)*

## D. Supervisors and evidence

**who-supervisors**
Q: Who are the supervisors? How do you choose them?
A: Registered builders and engineers matched to sites near them. We check their professional registration, their NIN and two guarantors. We rotate them across sites, and other supervisors make unannounced spot checks.

**spot-checks**
Q: What are spot checks? Will my contractor know?
A: From time to time a different supervisor visits unannounced to compare what is on site with what was claimed. The contractor is not told in advance. That is what makes verified milestones worth trusting.

**evidence-checks**
Q: How do you know the photos are real? Can someone fake evidence? Can they send old or borrowed photos?
A: Not through iBackHome. The app has no upload button: photos and video must be taken with its own camera, inside your site boundary, and the phone's clock must be right. A photo from outside the site, a wrong clock or the wrong phone is rejected, and look-alike images are flagged for our team. The server decides, not the phone.

**offline**
Q: Does the app work without signal?
A: Yes. The supervisor can capture with no signal. The app keeps each photo's original time and place and uploads when back online, within 72 hours of capture.

**weekly-report**
Q: Do I get reports? How will I know what is happening on my site?
A: Every Friday you get a weekly report on WhatsApp, email and your dashboard. It is drafted by AI from your project's evidence, verifications and payments, and your supervisor checks it before you see it. Every claim links to the photo behind it.

**supervisor-rejects**
Q: What if the supervisor rejects my claim? (contractors)
A: You will see the reason. Fix what is needed and claim again. If you think the rejection is wrong, raise it with our team and we will review the evidence.

## E. Becoming a supervisor

**become-supervisor**
Q: How do I become a supervisor? How do I apply? Are you hiring?
A: Apply with the form on our Supervisors page. We check your professional registration number first, then call your two guarantors, and only after that ask for your NIN and verify your identity. If approved, we tell you how to install the app and assign you a site near you.

**supervisor-requirements**
Q: What do I need to be a supervisor?
A: A registered engineer (COREN) or builder (NIOB or CORBON), a valid NIN, two guarantors we can contact, an Android phone (Android 8 or later) with a working camera and GPS, and the ability to reach sites near where you live. You also declare any relatives who work as contractors, so you are never assigned to their projects.

**supervisor-pay**
Q: How much are supervisors paid? What is the rate?
A: Handoff. *(**DECIDE**: no rate or payment wording exists on the site; the page leaves it blank. Do not guess.)*

**supervisor-turned-down**
Q: What if my application is turned down?
A: We will email you the reason, and you can apply again once it is fixed.

## F. Contractors, signing in, the app

**for-contractors**
Q: I am a contractor. How do I join? How do I get paid?
A: Contractors join when a client adds their phone number to a project. You then sign in with that number and a one-time code. Payment is in naira through the escrow partner after the supervisor verifies a milestone and the client approves it.

**sign-in**
Q: How do I sign in? I did not get a code.
A: You sign in with your phone number or email and a one-time code. If no code arrives, check the number or email and try again in a minute. If it still fails, contact us and we will help.

**the-app**
Q: Is there an app? Which phones does it work on? Where do I download it?
A: Supervisors use an Android app (Android 8 or later). It is not on a public store yet; approved supervisors are told how to install it. Clients and contractors use the website.

## G. Contact and limits

**contact**
Q: How do I contact you? What is your email or WhatsApp? Can I speak to a person?
A: Email {contact_email} or WhatsApp {contact_whatsapp}.

**account-help** (handoff)
Q: Something is wrong with my account, payment, project, milestone or dispute. Where is my money? Why was I rejected?
A: I can't see anyone's account, so I can't help with that here. Please contact us at {contact_email} or on WhatsApp {contact_whatsapp} and we will look into it.

**out-of-scope** (handoff)
Q: Legal advice, tax, investment, planning permission, structural or engineering advice, anything unrelated.
A: That is outside what I can help with. I can answer questions about how iBackHome works. For anything else, please contact us at {contact_email}.

## Needs your decision before PR 2

1. **Escrow/pilot wording** (`pilot-status`, `who-holds-money`): approve the pilot wording above, and decide whether the public pages must change.
2. **Currency** wording (`currency`): confirm.
3. **Contractor matching** (`construction-company`): leave unpromised, or confirm it exists.
4. **Handoff-only topics**: contractor fee, cancellation and billing date, supervisor pay. Supply wording, or keep as handoff.
5. Anything missing or wrong, and anything you want the assistant to refuse.
