# Observability

## Capture
Capture collects runtime signals into structured trace data for a single flow run. It focuses on recording events, timestamps, and environment fingerprints in a consistent sequence. Capture does not evaluate or interpret the meaning of events, and it does not enforce policy outcomes.

## Storage
Storage persists trace data, artifacts, and related metadata for later replay and analysis. It guarantees durable, queryable records with stable schema contracts. Storage does not perform analysis or classification of determinism, and it does not mutate datasets.

## Analysis
Analysis compares traces, detects drift, and computes replay deltas for verification. It summarizes changes into structured outputs that can be consumed by higher-level decision logic. Analysis does not write to storage and does not change the underlying trace data.

## Classification
Classification assigns determinism classes, entropy sources, and fingerprints to recorded events. It provides consistent labels for interpretation and reporting across the system. Classification does not execute flows and does not decide acceptability.
