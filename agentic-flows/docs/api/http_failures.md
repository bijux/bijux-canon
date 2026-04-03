# HTTP failure mapping
> HTTP status mapping for failure classes.

| FailureClass | HTTP status | Retryable (yes/no) |
| --- | --- | --- |
| ResolutionFailure | 400 | no |
| ExecutionFailure | 500 | no |
| RetrievalFailure | 502 | yes |
| ReasoningFailure | 422 | no |
| VerificationFailure | 409 | no |
| SemanticViolationError | 406 | no |
