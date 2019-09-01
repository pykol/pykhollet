<?xml version='1.0'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
xmlns:db="http://docbook.org/ns/docbook">
  <xsl:import href="/usr/share/xml/docbook/stylesheet/docbook-xsl/fo/docbook.xsl"/>
  <xsl:param name="section.autolabel">1</xsl:param>

  <xsl:template match="appendix[@id='appendix-licence']//formalpara" mode="xref-to"><xsl:value-of select="1+count(preceding-sibling::formalpara)"/></xsl:template>

  <xsl:template match="appendix[@id='appendix-licence']//listitem" mode="xref-to"><xsl:choose><xsl:when test="not(ancestor::listitem)"><xsl:apply-templates select="ancestor::formalpara" mode="xref-to"/></xsl:when><xsl:otherwise><xsl:apply-templates select="ancestor::listitem[1]" mode="xref-to"/></xsl:otherwise></xsl:choose>(<xsl:apply-templates select="." mode="item-number"/>)</xsl:template>
</xsl:stylesheet>
