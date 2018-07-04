.PHONY: all

all: pykol-full.js

pykol-full.js: jquery/jquery.js jquery-ui/jquery-ui.min.js js/jquery.formset.js \
  js/combobox.js js/menu.js
	uglifyjs $^ -c -o $@
