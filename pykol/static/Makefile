.PHONY: all

all: pykol-full.js style.css

pykol-full.js: jquery/jquery.js jquery-ui/jquery-ui.min.js js/jquery.formset.js \
  js/combobox.js js/menu.js
	uglifyjs $^ -c -o $@

.PHONY: style.css
style.css: style.scss
	scss -t compressed --sourcemap=none $< $@
