
## Misuse Cases (Gallery)
STATUS: EXPLANATORY

- Partial evidence reuse: citing spans from a different corpus snapshot → provenance mismatch; verification fails.
- Span shifting: altering cited spans to different offsets → span/hash mismatch; claim rejected.
- Replay with modified artifacts: change evidence or manifest → replay refuses or fingerprint drift triggers failure.
- Fake tool outputs: tool_returned without matching tool_called → verifier rejects due to linkage failure.
- Version spoofing: bump trace_schema_version without migration → trace rejected outright.
