html/index.xhtml: index.xml ects.xml
	xsltproc --output $@ --xinclude /usr/share/xml/docbook/stylesheet/docbook-xsl/xhtml/docbook.xsl $<

index.fo: index.xml installation.xml ects.xml colloscopes.xml
	xsltproc --output $@ --xinclude /usr/share/xml/docbook/stylesheet/docbook-xsl/fo/docbook.xsl $<

index.pdf: index.fo
	fop -fo $< -pdf $@

index.odt: index.xinclude.xml
	pandoc $< -r docbook -w ODT -so $@

index.xinclude.xml: index.xml ects.xml
	xmllint --xinclude $< --output $@
