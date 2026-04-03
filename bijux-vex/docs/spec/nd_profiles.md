# ND Search Profiles

ND search profiles provide explicit, user-friendly quality controls without requiring ANN expertise.

Profiles map to backend parameters. Current defaults (reference runner):

- `fast`: low latency, lower recall  
  - `M=8`, `ef_search=20`
- `balanced`: default quality/latency tradeoff  
  - `M=16`, `ef_search=50`
- `accurate`: higher recall, higher latency  
  - `M=32`, `ef_search=100`

Additional knobs:

- `nd_target_recall`: raises `ef_search` to meet a recall target where possible.
- `nd_latency_budget_ms`: caps `ef_search` for latency targets. If this reduces quality, the downgrade is logged.

If a backend cannot honor these settings, it must refuse or log an explicit downgrade.
