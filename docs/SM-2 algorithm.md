# 💻 JLPT SRS CLI - SM-2 Algorithm

> Reference for the spaced-repetition scheduler built in **Phase 2** ([[Phase 2 - SRS Core]], `src/jlpt/srs.py`). Summarised from Umang Sinha's write-up (dev.to, see Source) and cross-checked against the classic SuperMemo SM-2.

---

## Why spaced repetition

Human memory decays fast - Ebbinghaus's "forgetting curve" shows retention dropping sharply over days unless the memory is reinforced. That gives two failure modes:

- **Review too early** and you waste time on something you still know.
- **Review too late** and you have already forgotten it.

The optimal move is to review each item **just before you would forget it**. Spacing the reviews out - each successful recall pushing the next review further away - is the core idea.

A fixed schedule (day 1, day 3, day 7, ...) ignores that cards differ in difficulty: some stick instantly, others need repeated effort. **SM-2's insight is to give every card its own tiny learning model** and schedule that card from its own history.

## What SM-2 tracks (per card)

Three numbers per card, plus the grade you give each review. These map directly onto our schema:

| SM-2 term | Our column | Meaning |
|-----------|------------|---------|
| repetition count | `cards.repetitions` | consecutive successful reviews so far |
| interval | `cards.interval` | days until this card is next due |
| easiness factor (EF) | `cards.ease_factor` | how easy the card is *for you*; starts at **2.5** |
| recall grade | `reviews.grade` | quality of one recall, `0` to `5` |
| next due | `cards.due_date` | `today` plus the new interval |

This is exactly why the [[JLPT SRS CLI - Data Model]] puts the scheduling state on `cards` (current model) and the per-review grade on `reviews` (history).

## The grade scale (0 to 5)

You score each recall from 0 to 5:

- **5** - recalled perfectly.
- **4** - correct, but with hesitation.
- **3** - correct, but difficult.
- **2 or lower** - failure (the card is treated as forgotten).

The dividing line: **grade 3 or higher is a pass; grade below 3 is a fail.**

## The scheduling rules

On each review, in order:

```text
review(card, q):            # q = grade 0..5

    if q is below 3:        # forgotten -> relearn from scratch
        repetitions = 0
        interval    = 1
        # (EF left unchanged in this variant - see Decisions)
        stop here

    # passed (q is 3 or higher): grow the interval
    if repetitions is 0:    interval = 1        # first success
    elif repetitions is 1:  interval = 6        # second success
    else:                   interval = interval * EF   # then round (see Decisions)

    repetitions = repetitions + 1

    # update easiness AFTER using the old EF for the interval
    EF = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    if EF is below 1.3:  EF = 1.3               # floor

    due_date = today + interval days
```

Two things to notice: a **fail resets** the card (repetitions to 0, interval to 1) so it comes back tomorrow; and the **interval uses the current EF**, then EF is updated for next time.

## The easiness-factor update

```text
EF = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
constraint:  EF never drops below 1.3
```

Intuition: recall a card easily and its EF ticks **up**, so its intervals grow faster and it fades into the background. Struggle with a card and its EF ticks **down**, so it resurfaces more often. The **1.3 floor** stops a hard card's intervals from collapsing to nothing.

## Worked example (EF 2.5, every review passed)

```text
interval:  1 -> 6 -> 15 -> 37 -> 92   (days)
             (6 x 2.5 = 15,  15 x 2.5 = 37.5,  37 x 2.5 = 92.5)
```

The gaps expand rapidly - well-learned cards are seen rarely. (This particular sequence uses **truncation**, e.g. 37.5 becomes 37; with rounding you would get 38. That choice is a Decision below.)

## Reference implementation (from the article, Go)

```go
type Card struct {
    Repetition int
    Interval   int
    EF         float64
}

func Review(card *Card, quality int) {
    if quality < 3 {
        card.Repetition = 0
        card.Interval = 1
        return
    }
    if card.Repetition == 0 {
        card.Interval = 1
    } else if card.Repetition == 1 {
        card.Interval = 6
    } else {
        card.Interval = int(float64(card.Interval) * card.EF)
    }
    card.Repetition++
    ef := card.EF + (0.1 - float64(5-quality)*(0.08+float64(5-quality)*0.02))
    if ef < 1.3 {
        ef = 1.3
    }
    card.EF = ef
}
```

## How it maps to our Phase 2 (`src/jlpt/srs.py`)

- Implement this as a **pure function**: input the current `(ease_factor, interval, repetitions)`, the `grade`, and `today`; output the next `(ease_factor, interval, repetitions, due_date)`. Inject `today` so the tests are deterministic.
- **No persistence here.** Writing the new state back to `cards` and inserting the `reviews` row is the Phase 3 review loop's job; Phase 2 is only the maths + its unit tests.
- Test the canonical sequence, the 1.3 floor, and the failure reset - the [[Phase 2 - SRS Core]] plan lists these.

## Decisions to settle for our build

These are the places the article's variant and the classic SM-2 differ - decide each consciously:

1. **EF on failure.** The article's code returns early on a fail, so **EF is not updated** when you forget a card. Classic SM-2 updates EF on *every* review. *Recommendation for v1:* follow the article - EF only moves on a pass; a fail just reschedules. Simpler and fine for a personal deck.
2. **Round vs truncate the interval.** The article casts to `int` (**truncates**: 37.5 becomes 37). Classic SM-2 uses `round()`. Our Phase 2 plan currently says `round()`. Pick one and **test a `.5` case** so the choice is explicit (and remember Python's `round()` is banker's rounding).
3. **Grade origin.** The grade `0-5` is **derived by the Phase 3 quiz** from your typed answer and attempts (1st try → 5, retry → 3, wrong → fail), then stored in `reviews.grade`; the scheduler just consumes it - it neither knows nor cares that the grade is auto-derived rather than self-rated.

## Source

- Original: <https://www.umangsinha.in/blog/the-sm2-algorithm>
- Classic reference: SuperMemo SM-2 (Piotr Woźniak, 1987).

## See Also
- [[Phase 2 - SRS Core]] · [[JLPT SRS CLI - Data Model]] · [[JLPT SRS CLI - MOC]]
