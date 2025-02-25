.PHONY: multitest

multitest:
	@for i in {11..13}; do \
		pdm use python3.$$i; \
		pdm lock --group dev; \
		pdm install; \
		pdm run pytest; \
	done

