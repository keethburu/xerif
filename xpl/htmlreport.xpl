<?xml version="1.0" encoding="UTF-8"?>
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc"
  xmlns:c="http://www.w3.org/ns/xproc-step" 
  xmlns:tr="http://transpect.io"
  xmlns:hub="http://transpect.io/hub"
  xmlns:docx2hub="http://transpect.io/docx2hub"
  xmlns:xml2tex="http://transpect.io/xml2tex"
  xmlns:hub2htm="http://transpect.io/hub2htm"
  xmlns:html="http://www.w3.org/1999/xhtml"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tx="http://transpect.io/xerif"
  version="1.0"
  name="htmlreport" 
  type="tx:htmlreport">
  
  <p:documentation>
    Converts TEI XML to HTML and creates an HTML report with existing
    SVRL reports.
  </p:documentation>
  
  <p:input port="source" primary="true">
    <p:documentation>
      Expects an HTML Document
    </p:documentation>
  </p:input>
  
  <p:input port="paths" primary="false"/>
  
  <p:input port="reports" primary="false" sequence="true"/>

  <p:output port="result" primary="true"/>
    
  <p:option name="debug" select="'yes'"/>
  <p:option name="debug-dir-uri" select="'debug'"/>
  <p:option name="status-dir-uri" select="'status'"/>
  <p:option name="source-dir-uri" select="''"/>
  
  <p:import href="http://transpect.io/htmlreports/xpl/patch-svrl.xpl"/>
  <p:import href="export-xhtml.xpl"/>

  <p:add-attribute name="report-source-directory" match="/html:meta" attribute-name="content">
    <p:input port="source">
      <p:inline><html:meta name="source-dir-uri"/></p:inline>
    </p:input>
    <p:with-option name="attribute-value" select="$source-dir-uri"/>
  </p:add-attribute>

  <p:insert name="report-input" match="/html:html/html:head[not(html:meta[@name = 'source-dir-uri'])]" position="last-child">
    <p:input port="source">
      <p:pipe step="htmlreport" port="source"/>
    </p:input>
    <p:input port="insertion" select="/html:meta[normalize-space(@content)]">
      <p:pipe step="report-source-directory" port="result"/>
    </p:input>
  </p:insert>
  
  <tr:patch-svrl name="report">
    <p:input port="reports">
      <p:pipe port="reports" step="htmlreport"/>
    </p:input>
    <p:input port="params">
      <p:pipe port="paths" step="htmlreport"/>
    </p:input>
    <p:with-option name="report-title" select="'report'"/>
    <p:with-option name="debug" select="$debug"/>
    <p:with-option name="debug-dir-uri" select="$debug-dir-uri"/>
    <p:with-option name="status-dir-uri" select="$status-dir-uri"/>
  </tr:patch-svrl>

  <p:xslt>
    <p:input port="stylesheet">
      <p:inline>
        <xsl:stylesheet version="2.0">
          <xsl:param name="source-dir-uri"/>
          <xsl:variable name="directory"
            select="replace(replace($source-dir-uri, '^file:(///|/)([^/]|$)', '/$2', 'i'), '/+$', '')"/>

          <xsl:template match="@* | node()">
            <xsl:copy>
              <xsl:apply-templates select="@* | node()"/>
            </xsl:copy>
          </xsl:template>

          <!-- The renderer can prepend a remote source directory already present in the locator. -->
          <xsl:function name="tx:strip-source-directory" as="xs:string">
            <xsl:param name="value" as="xs:string"/>
            <xsl:variable name="locator" select="replace($value, '^file:(///|/)([^/]|$)', '/$2', 'i')"/>
            <xsl:sequence select="
              if ($directory = '') then $value
              else if (replace($locator, '/+$', '') = $directory) then ''
              else if (starts-with($locator, concat($directory, '/')))
              then tx:strip-source-directory(substring($locator, string-length($directory) + 2))
              else $value"/>
          </xsl:function>

          <xsl:template match="html:div[@class = 'BC_fallback']/html:p[@class = 'BC_fallback-messages']
                               /html:span[@class = 'BC_srcpath']/text()">
            <xsl:value-of select="tx:strip-source-directory(.)"/>
          </xsl:template>
        </xsl:stylesheet>
      </p:inline>
    </p:input>
    <p:input port="parameters"><p:empty/></p:input>
    <p:with-param name="source-dir-uri"
      select="string((/html:html/html:head/html:meta[@name = 'source-dir-uri']/@content)[1])">
      <p:pipe step="report-input" port="result"/>
    </p:with-param>
  </p:xslt>

  <tx:export-xhtml/>
 
</p:declare-step>
