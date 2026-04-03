# Troubleshooting

## VDB Connection Fails

**What happened**: The vector store backend could not connect.  
**Fix**:

1. Verify the backend is installed (`pip install "bijux-vex[vdb]"`).
2. Check the URI or file path.
3. Run `bijux vex vdb status --vector-store <name>`.

## ANN Not Installed

**What happened**: ANN execution requested but the ANN runner is unavailable.  
**Fix**:

1. Use `--execution-contract deterministic`.
2. Use exact mode or install the ANN backend for your environment.

## Embedding Provider Missing

**What happened**: `--embed-model` specified but provider not installed.  
**Fix**:

1. Install embeddings extras: `pip install "bijux-vex[embeddings]"`.
2. Provide a registered provider name.

## Determinism Refused

**What happened**: Deterministic contract requested with a non-deterministic backend.  
**Fix**:

1. Use exact mode (`--execution-contract deterministic`).
2. Avoid ANN until it is marked stable.

## Unknown Vector Store

**What happened**: `--vector-store` name not registered.  
**Fix**:

1. Check `bijux vex capabilities`.
2. Install the plugin that provides the backend.
