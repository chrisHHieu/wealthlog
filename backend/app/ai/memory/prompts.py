"""Prompt templates for all memory subsystems."""

# ── Canonical topic vocabulary ────────────────────────────────────────────────
# Haiku must choose topics only from this list. Normalizing to a fixed set
# ensures token-level overlap matching works consistently across sessions.

CANONICAL_TOPICS: tuple[str, ...] = (
    # Financial flows
    "thu nhập",   # income, salary, bonus
    "chi tiêu",   # spending, expenses
    "tiết kiệm",  # savings
    "đầu tư",     # investments, stocks
    "ngân sách",  # budget management
    "nợ",         # debt, loans, credit cards
    "tài khoản",  # bank accounts, e-wallets
    # Planning
    "mục tiêu",   # savings goals, targets
    "kế hoạch",   # planning, strategy
    "định kỳ",    # recurring transactions, subscriptions
    # Spending categories
    "ăn uống",    # food, dining
    "di chuyển",  # transport, fuel, vehicle
    "nhà ở",      # rent, utilities, housing
    "mua sắm",    # shopping, clothes, gadgets
    "sức khỏe",   # health, insurance, medical
    "giải trí",   # entertainment, hobbies
    "giáo dục",   # education, courses, books
    # Life context
    "gia đình",   # family, spouse, children
    "công việc",  # job, career, business
    "du lịch",    # travel, vacation
    # Behavioural
    "thói quen",  # habits, routines, patterns
    "cảm xúc",    # emotional patterns, avoidance signals
)

# Default topics per fact category — used as fallback when Haiku emits nothing valid.
CATEGORY_DEFAULT_TOPICS: dict[str, list[str]] = {
    "habit":      ["thói quen"],
    "preference": ["thói quen"],
    "goal":       ["mục tiêu"],
    "context":    ["gia đình"],
    "pattern":    ["thói quen"],
    "commitment": ["kế hoạch"],
    "emotion":    ["cảm xúc"],
    "general":    [],
}

_TOPIC_LIST_STR = ", ".join(CANONICAL_TOPICS)


# ── Fact extraction (runs every N turns via Haiku) ───────────────────────────

REVIEW_PROMPT = (
    "Read the personal-finance conversation above between the user and AI.\n\n"
    "Extract memorable observations across these types:\n"
    "1. habit       — what the user regularly does or avoids\n"
    "                 (e.g., 'forgets to log cash transactions')\n"
    "2. preference  — how they like things done\n"
    "                 (e.g., 'prefers weekly summaries over daily alerts')\n"
    "3. goal        — what they are saving or working toward\n"
    "                 (e.g., 'saving 120M VND for a house by Dec 2026')\n"
    "4. context     — life situation, role, household\n"
    "                 (e.g., 'spouse manages separate finances', 'student')\n"
    "5. pattern     — a behavioral trend observed in THIS session, NOT a one-off\n"
    "                 (e.g., 'consistently underestimates monthly food spending')\n"
    "6. commitment  — something the user explicitly said they WILL DO\n"
    "                 (e.g., 'said they will set up auto-savings this week')\n"
    "7. emotion     — an avoidance signal or emotional pattern worth noting\n"
    "                 (e.g., 'becomes defensive when discussing credit card debt')\n\n"
    "ALSO: if any new observation CONTRADICTS an existing fact, use 'replace' — "
    "do NOT add a duplicate.\n\n"
    "RULES:\n"
    "- Return a JSON array. Each item:\n"
    "  - 'action': 'add' (new) or 'replace' (supersedes existing)\n"
    "  - 'fact': one short sentence in the SAME LANGUAGE as the conversation\n"
    "  - 'category': one of the types above\n"
    "  - 'importance': 1-10\n"
    "  - 'confidence': 1-10\n"
    "  - 'expires_in_days': null = evergreen (use for commitments: 14-30 days)\n"
    "  - 'topics': 1-3 tags chosen ONLY from this exact list — do NOT invent new tags:\n"
    f"              {_TOPIC_LIST_STR}\n"
    "  - If action='replace', add 'replaces': 1-based index from Known facts list\n"
    "- Patterns require clear evidence — not speculation.\n"
    "- Commitments expire in 14-30 days (they resolve or lapse).\n"
    "- If nothing new is found, return []\n\n"
    "importance: 9-10 core facts; 6-8 frequently useful; 3-5 supplementary; 1-2 incidental\n"
    "confidence: 9-10 explicit statement; 6-8 strongly implied; 3-5 inferred; 1-2 guess\n\n"
    "Return ONLY valid JSON, no explanation.\n"
    "Example:\n"
    "[\n"
    "  {\"action\": \"add\", \"fact\": \"Saving 120M for house down payment by Dec 2026\",\n"
    "   \"category\": \"goal\", \"importance\": 9, \"confidence\": 10,\n"
    "   \"topics\": [\"mục tiêu\", \"nhà ở\", \"tiết kiệm\"]},\n"
    "  {\"action\": \"add\", \"fact\": \"Said will set up 3M/month auto-savings this week\",\n"
    "   \"category\": \"commitment\", \"importance\": 7, \"confidence\": 9,\n"
    "   \"expires_in_days\": 14, \"topics\": [\"tiết kiệm\", \"kế hoạch\"]},\n"
    "  {\"action\": \"replace\", \"replaces\": 3,\n"
    "   \"fact\": \"Income ~20M/month (raised from 15M, unverified)\",\n"
    "   \"category\": \"context\", \"importance\": 9, \"confidence\": 7,\n"
    "   \"topics\": [\"thu nhập\"]}\n"
    "]"
)


# ── Fact consolidation (fires when fact count > threshold) ───────────────────

CONSOLIDATION_PROMPT = (
    "You are consolidating a user's long-term fact store. "
    "The numbered list above is everything currently remembered about them.\n\n"
    "Find pairs or clusters that say the same thing in different words "
    "(paraphrases, refinements, or contradictions where the newer fact wins). "
    "For each cluster, emit ONE 'merge' action that keeps the strongest "
    "phrasing and removes the redundant rows.\n\n"
    "RULES:\n"
    "- Return a JSON array of 'merge' actions ONLY — never 'add'.\n"
    "- Each item: 'action': 'merge', 'keeps': 1-based survivor index,\n"
    "  'removes': list of 1-based indices to delete,\n"
    "  'fact': merged text (survivor is overwritten with this),\n"
    "  'category', 'importance', 'confidence',\n"
    f"  'topics': 1-3 tags from: {_TOPIC_LIST_STR}\n"
    "- 'keeps' must NOT appear in 'removes'.\n"
    "- Skip genuinely independent facts.\n"
    "- If nothing is mergeable, return []\n\n"
    "Return ONLY valid JSON, no explanation.\n"
    "Example:\n"
    "[\n"
    "  {\"action\": \"merge\", \"keeps\": 3, \"removes\": [7, 12],\n"
    "   \"fact\": \"Saving 120M VND for house down payment (raised from 80M)\",\n"
    "   \"category\": \"goal\", \"importance\": 9, \"confidence\": 9}\n"
    "]"
)


# ── Dreaming pass (daily — rewrites expired facts with real outcomes) ────────

DREAMING_PROMPT = (
    "You are the nightly memory-consolidation ('dreaming') pass of a "
    "personal-finance assistant. Above you have the user's current financial "
    "data, their EXPIRED time-bound memory facts, and their OVERDUE "
    "commitments.\n\n"
    "Expired facts are deleted tonight unless you rewrite them. "
    "For each expired fact decide its fate:\n"
    "- 'rewrite' — still valuable as history. Restate it in past tense with "
    "the real outcome, citing the financial data when it provides evidence "
    "(e.g. 'Saving 50M for a car by Jun 2026' becomes "
    "'Saved 42M of the 50M car goal by Jun 2026 — fell short'). "
    "If the data says nothing about it, state the outcome as unknown.\n"
    "- 'drop' — trivial, redundant, or no longer informative once expired.\n\n"
    "For each overdue commitment, emit 'resolve_commitment' with status "
    "'done' when the data shows it happened, or 'abandoned' when it clearly "
    "lapsed or was replaced. Omit the item to leave it pending.\n\n"
    "RULES:\n"
    "- Return a JSON array. Item shapes:\n"
    "  {\"action\": \"rewrite\", \"index\": <1-based fact index>, "
    "\"fact\": \"...\",\n"
    "   \"importance\": 1-10, \"confidence\": 1-10,\n"
    "   \"topics\": 1-3 tags chosen ONLY from: "
    f"{_TOPIC_LIST_STR}}}\n"
    "  {\"action\": \"drop\", \"index\": <1-based fact index>}\n"
    "  {\"action\": \"resolve_commitment\", "
    "\"index\": <1-based commitment index>,\n"
    "   \"status\": \"done\" or \"abandoned\"}\n"
    "- Rewritten facts are history, not active plans: importance 3-6 unless "
    "it marks a major life event; confidence reflects evidence strength.\n"
    "- Keep each fact's original language.\n"
    "- Give every expired fact exactly one 'rewrite' or 'drop' decision.\n"
    "- Return ONLY valid JSON, no explanation. [] if there is nothing to do."
)


# ── Session summarization (fires on idle sessions via Haiku) ─────────────────

SUMMARY_PROMPT = (
    "Summarize the personal-finance conversation above.\n\n"
    "Return ONLY a JSON object with these fields:\n"
    "- summary: 2-4 sentences. What the user asked, what was done, what was "
    "concluded. No greetings, no meta-comments. Same language as conversation.\n"
    "- key_topics: 2-5 main topics, 1-3 words each. Same language.\n"
    "- outcome: ONE sentence — what got decided or accomplished. "
    "null if nothing concrete.\n"
    "- commitments: list of things the user explicitly said they WILL DO. "
    "[] if none. Each entry is one short sentence.\n"
    "  Examples: [\"Set up 3M/month auto-savings this week\", "
    "\"Review insurance next month\"]\n"
    "- pushback: ONE sentence describing what the user resisted, avoided, or "
    "deflected when asked — or null if nothing notable.\n"
    "  Example: \"User avoided discussing credit card balance when asked directly.\"\n"
    "- open_questions: list of unresolved topics that should be followed up. "
    "[] if none.\n"
    "  Example: [\"Whether spouse's income is shared\", "
    "\"Exact balance of car loan\"]\n\n"
    "Return ONLY valid JSON (no markdown fences, no explanation):\n"
    '{"summary":"...","key_topics":["..."],"outcome":"...or null",'
    '"commitments":[],"pushback":"...or null","open_questions":[]}'
)


# ── UserModel synthesis (fires every N sessions via Sonnet) ──────────────────

SYNTHESIS_PROMPT = (
    "Your task: write a coherent, current understanding of this WealthLog user "
    "based on the facts and session history provided above.\n\n"
    "Structure your response EXACTLY with these five section headers:\n\n"
    "## Financial Situation\n"
    "2-3 sentences: income level, major expenses, debts, current savings rate, "
    "overall health. Use actual numbers when known; mark uncertainty explicitly "
    "with \"~[estimate] (unconfirmed)\" rather than omitting.\n\n"
    "## How They Think About Money\n"
    "2-3 sentences: decision style, risk tolerance, what kind of advice they "
    "respond well to, any known blind spots or avoidance patterns.\n\n"
    "## Active Goals\n"
    "Bullet list. Each line: goal, current status, deadline if known. "
    "Write \"(no active goals known)\" if none.\n\n"
    "## Behavioral Patterns\n"
    "Bullet list. Only include patterns with evidence from multiple sessions "
    "or an explicit user statement. "
    "Write \"(none observed yet)\" if insufficient data.\n\n"
    "## Open Threads\n"
    "Bullet list: pending commitments, unresolved contradictions, things to "
    "follow up on. Write \"(none)\" if empty.\n\n"
    "RULES:\n"
    "- Write in the SAME LANGUAGE as the majority of the facts/summaries\n"
    "- Be specific — use numbers and dates where known\n"
    "- Mark guesses: \"appears to be\", \"likely\", \"unconfirmed\"\n"
    "- If an existing user model was provided above: carry forward what is "
    "still valid, update what has changed, add new observations\n"
    "- Total length: 300-600 words\n"
    "- Return ONLY the model text — no preamble, no JSON wrapper\n"
)
