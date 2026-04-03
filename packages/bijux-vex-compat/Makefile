PROJECT_SLUG := bijux-vex-compat

include ../../makes/shared/python-package.mk

PUBLISH_PACKAGE_NAME    := bijux-vex
PUBLISH_UPLOAD_ENABLED  := 0

include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/publish.mk

$(VENV):
	@echo "→ Creating virtualenv with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv $(VENV)

install: $(VENV)
	@echo "→ Installing build dependencies..."
	@$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel

build publish publish-test release-dry: install

clean:
	@echo "→ Cleaning compatibility package artifacts..."
	@$(RM) $(VENV) "$(PROJECT_ARTIFACTS_DIR)" build dist *.egg-info .cache || true

.PHONY: clean install
