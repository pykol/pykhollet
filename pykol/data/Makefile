.PHONY: all

all: NomenclatureColles.xml GrillesECTS.xml

%.xml: %.xinclude.xml
	xmllint --xinclude $< | xmllint --nsclean --format --output $@ -
