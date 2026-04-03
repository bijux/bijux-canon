# Mutation Configuration

MUTMUT     := $(ACT)/mutmut

.PHONY: mutation mutation-clean mutation-mutmut

mutation:
	@echo "→ Running mutation testing"
	@$(MAKE) mutation-clean
	@$(MAKE) mutation-mutmut
	@echo "✔ Mutation testing completed"

mutation-clean:
	@echo "→ Cleaning mutation test artifacts"
	@$(RM) .mutmut-cache

mutation-mutmut:
	@echo "→ [Mutmut] Running mutation tests"
	@$(MUTMUT) run

##@ Mutation
mutation: ## Run mutation tests with Mutmut
mutation-clean: ## Remove mutation testing artifacts (.mutmut-cache)
mutation-mutmut: ## Run mutation testing with Mutmut
