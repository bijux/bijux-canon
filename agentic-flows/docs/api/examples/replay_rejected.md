# Replay Rejected Example
> Example of a replay rejection response.

request payload:
{"run_id":"run-123","expected_plan_hash":"plan-mismatch","acceptability_threshold":"exact_match","observer_mode":false}

response payload:
{"failure_class":"structural","reason_code":"contradiction_detected","violated_contract":"plan_hash","evidence_ids":[],"determinism_impact":"structural"}

HTTP status: 406

short explanation: replay rejected because the expected plan hash does not match the stored run.
