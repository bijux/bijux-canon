# ND Quality Metrics — Intuitive Guide

Rank instability

- Question it answers: “Would the order change if I reran this?”
- Good value: close to zero.
- If bad: enable witness mode or raise recall.

Distance margin

- Question it answers: “How separated are the top results?”
- Good value: larger margins feel safer.
- If bad: lower `k` or switch to exact for verification.

Similarity entropy

- Question it answers: “Are the results all basically the same?”
- Good value: moderate entropy (not uniform noise).
- If bad: tune parameters or review the corpus quality.
