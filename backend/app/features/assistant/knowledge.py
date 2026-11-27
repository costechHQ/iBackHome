"""What the website assistant knows (ADR 0006). Owner: Christopher.

Every answer here is a public statement made on iBackHome's behalf, written and approved by us. Nothing is
generated. A visitor's question is matched to the best entry (matcher.py); below a confidence threshold the
answer is a handoff to a person.

How to read an entry:
- `questions`: example questions. The FIRST is the entry's canonical question, shown as a "related question".
- `keywords`: words and short phrases that signal this topic (synonyms included).
- `answer`: the text. `{like_this}` is filled in at request time (see service.py): prices and the funding fee
  come from the plan list and the fee setting, contact details from settings. A test fails if an answer
  holds a money amount or a percentage that is not a placeholder.
- `handoff`: the answer points the visitor to a person (the panel also shows the contact buttons).

Honesty rules: during the pilot payments run in test mode and no real money is held; we are working with
banks to become the licensed escrow partner. No answer may say a partner is already in place. See
Docs/proposals/assistant-answers.md for the review notes behind each entry.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    id: str
    questions: tuple[str, ...]
    keywords: tuple[str, ...]
    answer: str
    handoff: bool = False


HANDOFF_CONTACT = (
    "Please call, text or WhatsApp {contact_whatsapp}, or email {contact_email}, or use our Contact page, "
    "and our team will help."
)

# Shown when nothing matches well enough: never a guess.
FALLBACK_ANSWER = "I'm not sure about that one, and I'd rather not guess. " + HANDOFF_CONTACT

ENTRIES: tuple[Entry, ...] = (
    # --- What iBackHome is -----------------------------------------------------------------------------
    Entry(
        id="what-is-ibackhome",
        questions=(
            "What is iBackHome?",
            "What do you do?",
            "How does iBackHome work?",
            "Tell me about iBackHome",
        ),
        keywords=(
            "ibackhome",
            "what is",
            "about",
            "overview",
            "what do you do",
            "platform",
            "service",
            "company",
        ),
        answer=(
            "iBackHome helps Nigerians abroad build at home. A verified supervisor visits your site and "
            "captures photo evidence of the work, and money for each stage is released only after the "
            "supervisor verifies it and you approve it. We are not a construction company: you work with a "
            "contractor you choose."
        ),
    ),
    Entry(
        id="construction-company",
        questions=(
            "Are you a construction company?",
            "Do you build for me?",
            "Do you build the house?",
        ),
        keywords=(
            "construction company",
            "construction",
            "do you build",
            "build for me",
            "build the house",
            "general contractor",
            "do you construct",
        ),
        answer=(
            "No. You work with a contractor you choose: bring your own and invite them by phone number, or "
            "ask us to find one for you. We verify what they claim on site and control when money moves."
        ),
    ),
    Entry(
        id="find-a-contractor",
        questions=(
            "Can you find me a contractor?",
            "I don't have a contractor",
            "How do you match contractors?",
            "Can you recommend a builder?",
        ),
        keywords=(
            "find a contractor",
            "find me a contractor",
            "find contractor",
            "need a contractor",
            "no contractor",
            "dont have a contractor",
            "match contractor",
            "match contractors",
            "recommend contractor",
            "recommend a contractor",
            "recommend a builder",
            "hire a contractor",
            "get a contractor",
            "contractor match",
            "matching",
            "shortlist",
        ),
        answer=(
            'Yes. Create your project and choose "I don\'t have a contractor yet", then tell us where you '
            "are building and what kind of work you need. Our team phones vetted contractors to check they "
            "are free and interested, and puts up to three forward. You read about them and choose one, and "
            "they are added to your project."
        ),
    ),
    Entry(
        id="contractor-vetting",
        questions=(
            "How do you choose contractors?",
            "Are the contractors checked?",
            "Are your contractors vetted?",
        ),
        keywords=(
            "check contractors",
            "check a contractor",
            "how do you check contractors",
            "contractors checked",
            "contractor vetted",
            "contractors vetted",
            "vet contractors",
            "choose contractors",
            "contractor references",
            "trust a contractor",
            "contractor quality",
            "good contractors",
            "reliable contractors",
        ),
        answer=(
            "Contractors apply to us. We check their registration where they have one, call two references, "
            "and only then approve them. We only put forward approved contractors, and we phone each one "
            "first to check they are free. You never get a contractor's phone number from us until you have "
            "chosen them."
        ),
    ),
    Entry(
        id="match-cost",
        questions=(
            "Does it cost anything to be matched with a contractor?",
            "Is finding a contractor free?",
        ),
        keywords=(
            "matching fee",
            "matching cost",
            "match cost",
            "cost to find a contractor",
            "free to find a contractor",
            "does matching cost",
            "charge to find a contractor",
        ),
        answer="Our team can tell you about that. " + HANDOFF_CONTACT,
        handoff=True,
    ),
    Entry(
        id="how-it-works",
        questions=(
            "How does it work step by step?",
            "How do I start?",
            "How do I get started?",
            "What are the steps?",
        ),
        keywords=(
            "how does it work",
            "how it works",
            "step by step",
            "get started",
            "how to start",
            "how do i start",
            "start a project",
            "create a project",
            "new project",
            "how do i begin",
            "steps",
            "process",
        ),
        answer=(
            "1) Create your project with your site address and budget. 2) Invite your contractor by phone "
            "number, or ask us to find one. 3) Your contractor prices the work in milestones (a bill of "
            "quantities) and you approve it. 4) Pin your site on the map. 5) Fund the first milestone. A "
            "supervisor then captures evidence, verifies the work, and you approve before money is released."
        ),
    ),
    Entry(
        id="where-we-work",
        questions=(
            "Where do you work?",
            "Which states or cities do you cover?",
            "Do you build outside Enugu?",
        ),
        keywords=(
            "where do you work",
            "states",
            "cities",
            "locations",
            "do you work in",
            "work in lagos",
            "work in enugu",
            "outside enugu",
            "nationwide",
            "areas",
            "cover",
        ),
        answer=(
            "Anywhere in Nigeria. When you set up your project, we match a vetted supervisor near your site."
        ),
    ),
    # --- Money and escrow ------------------------------------------------------------------------------
    Entry(
        id="pilot-status",
        questions=(
            "Is it live?",
            "Is my money safe?",
            "Is this real money?",
            "Are you licensed?",
        ),
        keywords=(
            "live",
            "pilot",
            "real money",
            "test mode",
            "licensed",
            "licence",
            "license",
            "safe",
            "launched",
            "launch",
            "regulated",
            "banks",
            "bank",
            "legit",
            "trust",
            "scam",
        ),
        answer=(
            "We are in a pilot. During the pilot, payments run in test mode and no real money is held yet. "
            "We are working with banks to become our licensed escrow partner, and real money will only be "
            "switched on once that partner is in place and live. For questions about the pilot, call, text "
            "or WhatsApp {contact_whatsapp}, or email {contact_email}."
        ),
    ),
    Entry(
        id="who-holds-money",
        questions=("Who holds my money?", "Does iBackHome hold my money?", "What is escrow?"),
        keywords=(
            "escrow",
            "holds my money",
            "hold my money",
            "who holds",
            "escrow partner",
            "funds held",
            "held by",
            "where is the money kept",
        ),
        answer=(
            "iBackHome never holds client funds. The design is that funds sit with a licensed escrow "
            "partner, and we are working with banks for this. Funds are released only after the supervisor "
            "verifies the work and you approve it. During our pilot this runs in test mode: no real money is "
            "held yet."
        ),
    ),
    Entry(
        id="release-process",
        questions=(
            "When is money released?",
            "How do milestone payments work?",
            "When does the contractor get paid?",
        ),
        keywords=(
            "released",
            "release",
            "milestone",
            "milestones",
            "milestone payment",
            "approve payment",
            "payment release",
            "when is money released",
            "when does the contractor get paid",
            "stage payment",
        ),
        answer=(
            "Milestone by milestone. When your contractor says a stage is done, the supervisor verifies it "
            "on site with evidence. Only then can you approve, and approving triggers the release. Nothing "
            "is released before both steps."
        ),
    ),
    Entry(
        id="dispute",
        questions=(
            "What if I don't agree a milestone is done?",
            "Can I dispute a milestone?",
            "What if the work is bad?",
        ),
        keywords=(
            "dispute",
            "disagree",
            "not done",
            "not complete",
            "unhappy",
            "complaint",
            "rework",
            "refuse to approve",
            "bad work",
            "poor work",
            "dont agree",
            "do not agree",
        ),
        answer=(
            "Raise a dispute instead of approving. The release pauses, and our team reviews the "
            "evidence with "
            "you and your contractor. Two staff sign off the outcome: pay the milestone, or send it back for "
            "rework."
        ),
    ),
    Entry(
        id="currency",
        questions=(
            "Which currency do I pay in?",
            "Can I pay in pounds or dollars?",
            "What about naira?",
        ),
        keywords=(
            "currency",
            "naira",
            "dollars",
            "dollar",
            "pounds",
            "pound",
            "gbp",
            "usd",
            "eur",
            "euro",
            "euros",
            "exchange rate",
            "pay in",
            "ngn",
        ),
        answer=(
            "You pay the supervision plan in US dollars, by card. When you fund a milestone you can pay by "
            "card in GBP, USD or EUR. Your contractor and suppliers are paid in naira at the exchange rate "
            "recorded on the day you fund. You see both amounts before you pay."
        ),
    ),
    Entry(
        id="contractor-payment",
        questions=(
            "How is my contractor paid?",
            "Is the fee taken from my contractor's payment?",
        ),
        keywords=(
            "contractor paid",
            "paid in naira",
            "fee taken",
            "deducted",
            "contractor receives",
            "pay my contractor",
            "how is my contractor paid",
            "contractors payment",
        ),
        answer=(
            "By the escrow partner, in naira, after verification and your approval. Fees are shown as "
            "separate lines when you fund a milestone. The milestone amount you agreed is what your "
            "contractor receives."
        ),
    ),
    # --- Prices ----------------------------------------------------------------------------------------
    Entry(
        id="pricing-overview",
        questions=(
            "How much does it cost?",
            "What are your prices?",
            "Is there a monthly fee?",
            "What are the plans?",
        ),
        keywords=(
            "price",
            "prices",
            "pricing",
            "cost",
            "costs",
            "how much",
            "monthly fee",
            "plan",
            "plans",
            "basic",
            "standard",
            "premium",
            "subscription",
            "package",
            "packages",
            "rates",
            "charge",
            "charges",
            "afford",
        ),
        answer=(
            "Supervision is a monthly fee per project: Basic {plan_basic_price} a month ({visits_basic} site "
            "visits a month), Standard {plan_standard_price} ({visits_standard} visits), Premium "
            "{plan_premium_price} ({visits_premium} visits), which we recommend. On top of that there is a "
            "{funding_fee} fee on money you fund into escrow. See the pricing page for details."
        ),
    ),
    Entry(
        id="billing-periods",
        questions=("Is there a discount for paying yearly?", "Can I pay for six months?"),
        keywords=(
            "yearly",
            "annual",
            "annually",
            "six months",
            "biannual",
            "discount",
            "pay yearly",
            "12 months",
            "6 months",
            "save",
            "months free",
        ),
        answer=(
            "Yes. Paying for 6 months costs 5 months, and paying for 12 months costs 10 months. The monthly "
            "price is on the pricing page."
        ),
    ),
    Entry(
        id="funding-fee",
        questions=("What is the fee when I fund a milestone?", "Is there a funding fee?"),
        keywords=(
            "funding fee",
            "fee on funding",
            "fund a milestone",
            "fund milestone",
            "transaction fee",
            "percentage fee",
            "service charge",
            "fee when i fund",
            "fees",
            "fee",
        ),
        answer=(
            "A {funding_fee} fee on each milestone you fund. It is shown as its own line before you pay, and "
            "it is not taken from your contractor's payment."
        ),
    ),
    Entry(
        id="contractor-fee",
        questions=("Do contractors pay a fee?", "Is it free for contractors?"),
        keywords=(
            "contractor fee",
            "contractors pay",
            "free for contractors",
            "fee for contractors",
            "do contractors pay",
            "contractor charges",
        ),
        answer="Our team can tell you about that. " + HANDOFF_CONTACT,
        handoff=True,
    ),
    Entry(
        id="cancel-billing",
        questions=("Can I cancel?", "When is the monthly fee charged?"),
        keywords=(
            "cancel",
            "cancellation",
            "when charged",
            "billing date",
            "refund",
            "stop subscription",
            "unsubscribe",
            "when is the fee charged",
            "end my plan",
        ),
        answer="Our team can tell you about that. " + HANDOFF_CONTACT,
        handoff=True,
    ),
    # --- Supervisors and evidence ----------------------------------------------------------------------
    Entry(
        id="who-supervisors",
        questions=("Who are the supervisors?", "How do you choose supervisors?", "Who checks the work?"),
        keywords=(
            "supervisor",
            "supervisors",
            "who verifies",
            "who checks",
            "who inspects",
            "site visits",
            "vetted supervisors",
            "who are the supervisors",
            "verify the work",
            "engineer visits",
        ),
        answer=(
            "Registered builders and engineers matched to sites near them. We check their professional "
            "registration, their NIN and two guarantors. We rotate them across sites, and other supervisors "
            "make unannounced spot checks."
        ),
    ),
    Entry(
        id="spot-checks",
        questions=("What are spot checks?", "Will my contractor know about a spot check?"),
        keywords=(
            "spot check",
            "spot checks",
            "unannounced",
            "surprise visit",
            "random visit",
            "will my contractor know",
            "unannounced visit",
        ),
        answer=(
            "From time to time a different supervisor visits unannounced to compare what is on site "
            "with what "
            "was claimed. The contractor is not told in advance. That is what makes verified "
            "milestones worth "
            "trusting."
        ),
    ),
    Entry(
        id="evidence-checks",
        questions=(
            "How do you know the photos are real?",
            "Can someone fake evidence?",
            "Can they send old or borrowed photos?",
            "Can I use photos from my gallery?",
        ),
        keywords=(
            "fake",
            "photos",
            "photo",
            "evidence",
            "old photos",
            "borrowed photos",
            "real photos",
            "gps",
            "geofence",
            "gallery",
            "upload",
            "tamper",
            "authentic",
            "prove",
            "proof",
            "pictures",
            "video",
        ),
        answer=(
            "Not through iBackHome. The app has no upload button: photos and video must be taken with its "
            "own camera, inside your site boundary, and the phone's clock must be right. A photo from "
            "outside "
            "the site, a wrong clock or the wrong phone is rejected, and look-alike images are flagged for "
            "our team. The server decides, not the phone."
        ),
    ),
    Entry(
        id="offline",
        questions=("Does the app work without signal?", "Does it work offline?"),
        keywords=(
            "offline",
            "signal",
            "no network",
            "no internet",
            "without signal",
            "poor network",
            "low connectivity",
            "without internet",
        ),
        answer=(
            "Yes. The supervisor can capture with no signal. The app keeps each photo's original time and "
            "place and uploads when back online, within 72 hours of capture."
        ),
    ),
    Entry(
        id="weekly-report",
        questions=("Do I get reports?", "How will I know what is happening on my site?"),
        keywords=(
            "report",
            "reports",
            "weekly",
            "friday",
            "updates",
            "progress report",
            "how will i know",
            "status update",
            "whatsapp updates",
            "progress",
            "updated",
        ),
        answer=(
            "Every Friday you get a weekly report on WhatsApp, email and your dashboard. It is drafted by AI "
            "from your project's evidence, verifications and payments, and your supervisor checks it before "
            "you see it. Every claim links to the photo behind it."
        ),
    ),
    Entry(
        id="supervisor-rejects",
        questions=("What if the supervisor rejects my claim?", "My milestone claim was rejected"),
        keywords=(
            "claim rejected",
            "supervisor rejects",
            "rejection reason",
            "claim again",
            "rejected my claim",
            "claim was rejected",
        ),
        answer=(
            "You will see the reason. Fix what is needed and claim again. If you think the rejection is "
            "wrong, raise it with our team and we will review the evidence."
        ),
    ),
    # --- Becoming a supervisor -------------------------------------------------------------------------
    Entry(
        id="become-supervisor",
        questions=(
            "How do I become a supervisor?",
            "How do I apply to be a supervisor?",
            "Are you hiring supervisors?",
        ),
        keywords=(
            "become a supervisor",
            "become supervisor",
            "apply to be a supervisor",
            "supervisor application",
            "hiring",
            "join as a supervisor",
            "supervisor job",
            "work as a supervisor",
            "engineer job",
            "apply to supervise",
            "jobs",
            "vacancy",
        ),
        answer=(
            "Apply with the form on our Supervisors page. We check your professional registration number "
            "first, then call your two guarantors, and only after that ask for your NIN and verify your "
            "identity. If approved, we tell you how to install the app and assign you a site near you."
        ),
    ),
    Entry(
        id="supervisor-requirements",
        questions=("What do I need to be a supervisor?", "What are the supervisor requirements?"),
        keywords=(
            "supervisor requirements",
            "need to be a supervisor",
            "coren",
            "niob",
            "corbon",
            "qualifications",
            "what do i need",
            "android phone",
            "requirements",
            "guarantors",
            "guarantor",
            "nin",
        ),
        answer=(
            "A registered engineer (COREN) or builder (NIOB or CORBON), a valid NIN, two guarantors we can "
            "contact, an Android phone (Android 8 or later) with a working camera and GPS, and the ability "
            "to reach sites near where you live. You also declare any relatives who work as contractors, so "
            "you are never assigned to their projects."
        ),
    ),
    Entry(
        id="supervisor-pay",
        questions=("How much are supervisors paid?", "What is the supervisor rate?"),
        keywords=(
            "supervisor pay",
            "supervisors paid",
            "supervisor salary",
            "how much supervisors earn",
            "supervisor rate",
            "earn",
            "earnings",
            "salary",
            "paid per visit",
        ),
        answer="Our team can tell you about that. " + HANDOFF_CONTACT,
        handoff=True,
    ),
    Entry(
        id="supervisor-turned-down",
        questions=("What if my application is turned down?", "Can I apply again?"),
        keywords=(
            "turned down",
            "application rejected",
            "not approved",
            "declined",
            "reapply",
            "apply again",
            "rejected application",
        ),
        answer="We will email you the reason, and you can apply again once it is fixed.",
    ),
    # --- Contractors, signing in, the app --------------------------------------------------------------
    Entry(
        id="for-contractors",
        questions=("I am a contractor. How do I join?", "How do contractors get paid?"),
        keywords=(
            "i am a contractor",
            "for contractors",
            "contractor join",
            "join as a contractor",
            "contractor sign in",
            "how do contractors get paid",
            "contractor payment",
            "builder",
            "builders",
            "contractors",
        ),
        answer=(
            "Contractors join when a client adds their phone number to a project, or chooses them from a "
            "shortlist we put forward. You then sign in with that number and a one-time code. Payment is in "
            "naira through the escrow partner after the supervisor verifies a milestone and the client "
            "approves it."
        ),
    ),
    Entry(
        id="contractor-apply",
        questions=("I am a contractor. How do I get clients?", "How do I get listed as a contractor?"),
        keywords=(
            "contractor apply",
            "i am a contractor how do i get clients",
            "how do i get clients",
            "get listed",
            "list my business",
            "get clients",
            "more clients",
            "contractor application",
            "register as a contractor",
            "join as a contractor",
            "listed",
            "get customers",
        ),
        answer=(
            "Apply with the form on our Contractors page. We check your registration, if you have one, and "
            "call two references. If we approve you, we may put your business forward when a client asks us "
            "to find a contractor, and we phone you first to check you are free."
        ),
    ),
    Entry(
        id="sign-in",
        questions=("How do I sign in?", "I did not get a code", "I can't log in"),
        keywords=(
            "sign in",
            "login",
            "log in",
            "code",
            "otp",
            "verification code",
            "didnt get a code",
            "no code",
            "cant sign in",
            "cant log in",
            "password",
            "sign up",
            "register",
            "account",
        ),
        answer=(
            "You sign in with your phone number or email and a one-time code. If no code arrives, check the "
            "number or email and try again in a minute. If it still fails, contact us and we will help."
        ),
    ),
    Entry(
        id="the-app",
        questions=("Is there an app?", "Which phones does it work on?", "Where do I download it?"),
        keywords=(
            "app",
            "android",
            "download",
            "play store",
            "phone app",
            "mobile app",
            "ios",
            "iphone",
            "install",
            "apk",
        ),
        answer=(
            "Supervisors use an Android app (Android 8 or later). It is not on a public store yet; approved "
            "supervisors are told how to install it. Clients and contractors use the website."
        ),
    ),
    # --- Contact and limits ----------------------------------------------------------------------------
    Entry(
        id="contact",
        questions=(
            "How do I contact you?",
            "What is your email or WhatsApp?",
            "Can I speak to a person?",
        ),
        keywords=(
            "contact",
            "email",
            "phone number",
            "whatsapp",
            "call",
            "text",
            "speak to a person",
            "talk to someone",
            "human",
            "customer service",
            "support",
            "reach you",
            "office",
            "address",
            "speak to someone",
            "talk to a person",
        ),
        answer=(
            "Call, text or WhatsApp {contact_whatsapp}, or email {contact_email}. You can also use our "
            "Contact page."
        ),
        handoff=True,
    ),
    Entry(
        id="account-help",
        questions=(
            "Something is wrong with my account or payment",
            "Where is my money?",
            "Why was I rejected?",
        ),
        keywords=(
            "why was i rejected",
            "my account",
            "my payment",
            "payment failed",
            "my project",
            "my milestone",
            "where is my money",
            "locked out",
            "something wrong",
            "problem with",
            "not working",
            "error",
            "charged",
            "my order",
            "my dispute",
            "my money",
            "my balance",
            "stuck",
        ),
        answer="I can't see anyone's account, so I can't help with that here. " + HANDOFF_CONTACT,
        handoff=True,
    ),
    Entry(
        id="out-of-scope",
        questions=(
            "Can you give me legal or tax advice?",
            "Can you help with planning permission?",
            "Tell me a joke",
        ),
        keywords=(
            "legal",
            "lawyer",
            "tax",
            "investment",
            "invest",
            "planning permission",
            "building permit",
            "structural",
            "engineering advice",
            "architect",
            "design",
            "visa",
            "immigration",
            "land title",
            "survey",
            "weather",
            "recipe",
            "politics",
            "joke",
            "poem",
            "football",
            "write code",
        ),
        answer=(
            "That is outside what I can help with. I can answer questions about how iBackHome works. For "
            "anything else: " + HANDOFF_CONTACT
        ),
        handoff=True,
    ),
)

ENTRIES_BY_ID: dict[str, Entry] = {e.id: e for e in ENTRIES}
