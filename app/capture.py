"""Pure parser for the capture bar: text in, one Intent out. No Flask, no database."""
import difflib
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

CATEGORIES = ["Food", "Transport", "Study", "Fun", "Bills", "Other"]
KEYWORDS = {
    "Food": "lunch dinner breakfast coffee tea chai snack snacks pizza burger groceries grocery food meal canteen restaurant swiggy zomato juice",
    "Transport": "uber ola cab bus metro auto fuel petrol train taxi rapido transport ticket",
    "Study": "book books course tuition fees notes stationery pen print printout udemy study exam",
    "Fun": "movie movies netflix game games party concert spotify outing cinema fun",
    "Bills": "rent bill bills electricity wifi recharge phone subscription internet",
}
WORD_CATEGORY = {word: cat for cat, words in KEYWORDS.items() for word in words.split()}
WEEKDAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5, "sun": 6, "sunday": 6,
}
FILLER = {"done", "did", "completed", "complete", "finished", "yes", "x"}
NEGATIVE = {"undone", "no", "not", "skipped", "skip"}
MONEY_VERBS = {"spent", "spend", "paid", "pay", "bought", "buy"}
NUMBER = re.compile(r"^([+\-=]?)[₹$€£]?(\d[\d,]*(?:\.\d+)?|\.\d+)(?:rs|inr|hrs|hr|h|kg|km|l)?$")


@dataclass
class Intent:
    kind: str  # set | add | money | undo | empty | error | ambiguous | unknown
    day: date | None = None
    tracker: dict | None = None
    value: float | None = None
    category: str | None = None
    note: str = ""
    message: str = ""
    suggestions: list = field(default_factory=list)  # [{"label", "text"}]
    create: dict | None = None  # {"name", "type"}


def parse(text: str, trackers: list[dict], today: date) -> Intent:
    raw = text.strip()
    if not raw:
        return Intent("empty", day=today)
    if raw.lower() in ("undo", "undo that", "u"):
        return Intent("undo", day=today)

    tokens = raw.split()
    day, tokens = _extract_day(tokens, today)
    num, tokens = _extract_number(tokens)
    words, negative = _clean_words([t.lower() for t in tokens])
    money_verb = bool(words) and words[0] in MONEY_VERBS
    if money_verb:
        words = words[1:]

    if money_verb or (num and num["first"] and num["sign"] == "-"):
        return _money(num, words, trackers, day)
    if not words:
        if num:
            return _money(num, [], trackers, day)
        return Intent("error", day=day, message="Type a tracker name, like 'gym' or 'water 3'.")

    tracker, rest, near, ambiguous = _resolve(words, trackers)
    if tracker:
        return _for_tracker(tracker, rest, num, negative, day)
    if num and any(_category_of(w) for w in words):
        return _money(num, words, trackers, day)

    extras = ([num["raw"]] if num else []) + [t for t in raw.split() if t.lower() in DAY_TOKENS]
    suggestions = [{"label": t["name"], "text": " ".join([t["name"].lower()] + extras)} for t in near]
    if ambiguous:
        return Intent("ambiguous", day=day, suggestions=suggestions, message="Which one did you mean?")
    name = " ".join(words).title()
    return Intent(
        "unknown", day=day, suggestions=suggestions, message=f"No tracker called '{name}'.",
        create={"name": name, "type": _guess_type(num)},
    )


DAY_TOKENS = {"today", "yesterday", "yday"} | set(WEEKDAYS)


def _extract_day(tokens, today):
    if len(tokens) < 2:
        return today, tokens
    day, kept = today, []
    found = False
    for tok in tokens:
        low = tok.lower()
        if not found and low == "today":
            found = True
        elif not found and low in ("yesterday", "yday"):
            day, found = today - timedelta(days=1), True
        elif not found and low in WEEKDAYS:
            # most recent such weekday, strictly before today
            day, found = today - timedelta(days=(today.weekday() - WEEKDAYS[low]) % 7 or 7), True
        elif low not in DAY_TOKENS:
            kept.append(tok)
    return day, kept


def _extract_number(tokens):
    for i, tok in enumerate(tokens):
        m = NUMBER.match(tok.lower())
        if m:
            num = {"sign": m.group(1), "amount": float(m.group(2).replace(",", "")), "raw": tok, "first": i == 0}
            return num, tokens[:i] + tokens[i + 1:]
    return None, tokens


def _clean_words(words):
    negative = False
    while len(words) > 1 and (words[-1] in FILLER or words[-1] in NEGATIVE):
        negative = negative or words[-1] in NEGATIVE
        words = words[:-1]
    while len(words) > 1 and words[0] in ("did", "done"):
        words = words[1:]
    return words, negative


def _category_of(word):
    if word in WORD_CATEGORY:
        return WORD_CATEGORY[word]
    return next((c for c in CATEGORIES if c.lower() == word), None)


def _money(num, words, trackers, day, tracker=None):
    if not num:
        return Intent("error", day=day, message="How much? Try 'spent 250 lunch'.")
    tracker = tracker or next((t for t in trackers if t["type"] == "money"), None)
    if tracker is None:
        return Intent("error", day=day, message="Create a money tracker first.",
                      create={"name": "Spending", "type": "money"})
    category = next((c for c in map(_category_of, words) if c), "Other")
    return Intent("money", day=day, tracker=tracker, value=num["amount"], category=category, note=" ".join(words))


def _for_tracker(tracker, rest, num, negative, day):
    kind, note = tracker["type"], " ".join(rest)
    amount = None if num is None else (-num["amount"] if num["sign"] == "-" else num["amount"])
    if kind == "money":
        return _money(num, rest, [tracker], day, tracker)
    if kind == "check":
        done = not negative and not (num and num["amount"] == 0)
        return Intent("set", day=day, tracker=tracker, value=1.0 if done else 0.0, note=note)
    if kind == "count":
        if num and num["sign"] == "=":
            return Intent("set", day=day, tracker=tracker, value=num["amount"], note=note)
        if num:
            return Intent("add", day=day, tracker=tracker, value=amount, note=note)
        if negative:
            return Intent("set", day=day, tracker=tracker, value=0.0, note=note)
        return Intent("add", day=day, tracker=tracker, value=1.0, note=note)
    if num is None:
        hint = "mood 4" if kind == "mood" else f"{tracker['name'].lower()} 7.5"
        return Intent("error", day=day, tracker=tracker, message=f"{tracker['name']} needs a value, like '{hint}'.")
    if kind == "mood" and not (num["amount"] == int(num["amount"]) and 1 <= num["amount"] <= 5):
        return Intent("error", day=day, tracker=tracker, message="Mood is a whole number from 1 to 5.")
    return Intent("set", day=day, tracker=tracker, value=amount, note=note)


def _resolve(words, trackers):
    """Longest leading run of words that names a tracker; the rest becomes a note."""
    ambiguous = []
    for n in range(len(words), 0, -1):
        query = " ".join(words[:n])
        exact = [t for t in trackers if t["name"].lower() == query]
        if exact:
            return exact[0], words[n:], [], False
        hits = [t for t in trackers if _prefix(query, t["name"].lower())]
        if len(hits) == 1:
            return hits[0], words[n:], [], False
        if hits and not ambiguous:
            ambiguous = hits
    if ambiguous:
        return None, [], ambiguous, True
    for n in range(len(words), 0, -1):
        scored = sorted(((_score(" ".join(words[:n]), t["name"].lower()), t) for t in trackers), key=lambda p: -p[0])
        if scored and scored[0][0] >= 0.85 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.1):
            return scored[0][1], words[n:], [], False
    scored = sorted(((_score(words[0], t["name"].lower()), t) for t in trackers), key=lambda p: -p[0])
    return None, [], [t for s, t in scored if s >= 0.55][:3], False


def _prefix(query, name):
    return name.startswith(query) or (" " not in query and any(w.startswith(query) for w in name.split()))


def _score(query, name):
    candidates = [name] + name.split()
    return max(difflib.SequenceMatcher(None, query, c).ratio() for c in candidates)


def _guess_type(num):
    if num is None:
        return "check"
    return "count" if num["amount"] == int(num["amount"]) and num["sign"] != "=" else "number"
