# Project Overview

`bijux-canon-ingest` is the package that prepares content for the rest of the
system. It takes messy document inputs, runs deterministic transforms, and
produces retrieval-oriented structures without absorbing responsibilities that
belong to the index or runtime packages.

## The job to keep in mind

This package should make it easy to explain:

- how a document was cleaned or chunked
- how ingest configuration shaped the result
- how retrieval-ready output was assembled before index execution takes over

## What belongs here

- deterministic document transforms
- ingest-local retrieval assembly and helper models
- package-local CLI and HTTP boundaries
- ingest-specific adapters, observability, safeguards, and support utilities

## What does not belong here

- vector execution engines or cross-package index authority
- runtime-wide replay, persistence, or execution governance
- repository tooling and general monorepo infrastructure

## Why the source tree is broad

The package contains both strongly domain-specific modules and a few support
areas that are still package-local for now. Some subpackages, such as `fp/`,
`result/`, `streaming/`, `tree/`, `safeguards/`, and parts of `integrations/`,
may eventually deserve extraction if multiple canonical packages need the same
abstractions. Until then, they should stay dependency-light and clearly scoped.
