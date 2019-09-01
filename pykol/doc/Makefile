html/index.xhtml: index.xml ects.xml
	xsltproc --output $@ --xinclude /usr/share/xml/docbook/stylesheet/docbook-xsl/xhtml/docbook.xsl $<

index.fo: docbook-fo.xsl index.xml installation.xml ects.xml colloscopes.xml cc-by-sa-4.0.xml
	xsltproc --output $@ --xinclude $< $(word 2,$^)

index.pdf: index.fo
	fop -fo $< -pdf $@

index.odt: index.xinclude.xml
	pandoc $< -r docbook -w ODT -so $@

index.xinclude.xml: index.xml ects.xml
	xmllint --xinclude $< --output $@
