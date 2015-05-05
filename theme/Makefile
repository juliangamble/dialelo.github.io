SCSSDIR ?= scss
CSSDIR = static/css

sass:
	@for i in $$(ls $(SCSSDIR)); do \
	    out="$(CSSDIR)/$${i%.*}.css"; \
	    sassc "$(SCSSDIR)/$$i" "$$out"; \
	    sed -i '$$d' "$$out"; \
	    rm -f "$$out.map"; \
	 done
	@echo 'SCSS files compiled'
