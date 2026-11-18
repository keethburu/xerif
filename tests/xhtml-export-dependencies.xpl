<?xml version="1.0" encoding="UTF-8"?>
<p:library xmlns:p="http://www.w3.org/ns/xproc"
  xmlns:c="http://www.w3.org/ns/xproc-step"
  xmlns:cx="http://xmlcalabash.com/ns/extensions"
  xmlns:epub="http://transpect.io/epubtools"
  xmlns:html="http://www.w3.org/1999/xhtml"
  xmlns:tei2html="http://transpect.io/tei2html"
  xmlns:tr="http://transpect.io"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <p:declare-step type="html:templates">
    <p:input port="source" primary="true"/>
    <p:input port="meta"/>
    <p:input port="paths"/>
    <p:output port="result"/>
    <p:option name="debug"/>
    <p:option name="debug-dir-uri"/>
    <p:option name="different-basename"/>
    <p:identity/>
  </p:declare-step>

  <p:declare-step type="tei2html:tei2html">
    <p:input port="source" primary="true"/>
    <p:input port="paths"/>
    <p:output port="result"/>
    <p:option name="srcpaths"/>
    <p:option name="debug"/>
    <p:option name="debug-dir-uri"/>
    <p:option name="status-dir-uri"/>
    <p:identity/>
  </p:declare-step>

  <p:declare-step type="tr:dynamic-transformation-pipeline">
    <p:input port="source" primary="true"/>
    <p:input port="paths"/>
    <p:input port="options"/>
    <p:input port="additional-inputs"/>
    <p:output port="result"/>
    <p:option name="load"/>
    <p:option name="fallback-xpl"/>
    <p:option name="debug"/>
    <p:option name="debug-dir-uri"/>
    <p:identity/>
  </p:declare-step>

  <p:declare-step type="epub:convert">
    <p:input port="source" primary="true"/>
    <p:input port="meta"/>
    <p:input port="conf" sequence="true"/>
    <p:output port="result" primary="true"/>
    <p:output port="report" sequence="true"><p:empty/></p:output>
    <p:option name="debug"/>
    <p:option name="debug-dir-uri"/>
    <p:option name="status-dir-uri"/>
    <p:option name="terminate-on-error"/>
    <p:xslt>
      <p:input port="stylesheet">
        <p:inline>
          <xsl:stylesheet version="2.0">
            <xsl:template match="/">
              <xsl:if test="not(html:html/@source-dir-uri = 'file:///private/manuscript/'
                            and html:html/html:head/html:meta[@name = 'source-dir-uri']/@content = 'file:///private/manuscript/')">
                <xsl:message terminate="yes">EPUB conversion must receive source-dir-uri.</xsl:message>
              </xsl:if>
              <c:result>proof.epub</c:result>
            </xsl:template>
          </xsl:stylesheet>
        </p:inline>
      </p:input>
      <p:input port="parameters"><p:empty/></p:input>
    </p:xslt>
  </p:declare-step>

  <p:declare-step type="tr:store-debug">
    <p:input port="source"/>
    <p:output port="result"/>
    <p:option name="pipeline-step"/>
    <p:option name="active"/>
    <p:option name="base-uri"/>
    <p:identity/>
  </p:declare-step>

  <p:declare-step type="cx:message">
    <p:input port="source"/>
    <p:output port="result"/>
    <p:option name="message"/>
    <p:identity/>
  </p:declare-step>
</p:library>
