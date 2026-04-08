SECURITY_PIP_AUDIT_TEXT_COMMAND ?= "$(VENV_PYTHON)" -m bijux_canon_dev.security.pip_audit_gate

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/bijux-py/security.mk
