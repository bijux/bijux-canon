# ND Failure Story

A product team switches to ANN for scale. Latency improves, but recommendations become unstable. Users notice inconsistent results, and the team can’t reproduce the issue.

The root cause is an undeclared randomness source and a drifting index. With Bijux‑Vex, ND would have required explicit randomness declarations, recorded the index hash, and flagged the drift early.
