<?xml version="1.0" encoding="UTF-8"?>
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc"
  xmlns:c="http://www.w3.org/ns/xproc-step"
  xmlns:dbk="http://docbook.org/ns/docbook"
  xmlns:html="http://www.w3.org/1999/xhtml"
  xmlns:s="http://purl.oclc.org/dsdl/schematron"
  xmlns:svrl="http://purl.oclc.org/dsdl/svrl"
  xmlns:tr="http://transpect.io"
  xmlns:tx="http://transpect.io/xerif"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <p:output port="result"/>
  <p:option name="scratch-dir-uri" required="true"/>
  <p:import href="../xpl/htmlreport.xpl"/>
  <p:import href="../xpl/export-xhtml.xpl"/>
  <p:variable name="directory-uri"
    select="if (ends-with($scratch-dir-uri, '/')) then $scratch-dir-uri else concat($scratch-dir-uri, '/')"/>

  <p:identity name="hub">
    <p:input port="source">
      <p:inline>
        <dbk:hub>
          <dbk:info>
            <dbk:keywordset role="hub">
              <dbk:keyword role="source-dir-uri">file:///private/manuscript/</dbk:keyword>
            </dbk:keywordset>
          </dbk:info>
        </dbk:hub>
      </p:inline>
    </p:input>
  </p:identity>

  <tx:export-xhtml>
    <p:input port="source">
      <p:inline>
        <html:html xml:base="file:///private/manuscript/" source-dir-uri="file:///private/manuscript/">
          <html:head>
            <html:title>Report fixture</html:title>
            <html:meta name="source-dir-uri" content="file:///private/manuscript/"/>
          </html:head>
          <html:body>
            <html:p id="reported-paragraph" srcpath="Stories/Story_u1.xml?xpath=/Story[1]/ParagraphStyleRange[1]">Caption with image</html:p>
          </html:body>
        </html:html>
      </p:inline>
    </p:input>
  </tx:export-xhtml>

  <tx:htmlreport>
    <p:input port="paths">
      <p:inline><c:param-set><c:param name="interface-language" value="en"/></c:param-set></p:inline>
    </p:input>
    <p:input port="reports">
      <p:inline>
        <svrl:schematron-output tr:rule-family="flat-hub">
          <svrl:successful-report id="multi_para_caption_with_image" role="error" location="/dbk:hub/dbk:para[1]">
            <svrl:text>
              <s:span class="srcpath">file:///private/manuscript/Stories/Story_u1.xml?xpath=/Story[1]/ParagraphStyleRange[1]</s:span>
              <html:span class="issue">Several caption paras and image contained</html:span>
            </svrl:text>
          </svrl:successful-report>
        </svrl:schematron-output>
      </p:inline>
    </p:input>
    <p:with-option name="source-dir-uri"
      select="string(/*/dbk:info/dbk:keywordset[@role = 'hub']/dbk:keyword[@role = 'source-dir-uri'])">
      <p:pipe step="hub" port="result"/>
    </p:with-option>
    <p:with-option name="debug" select="'no'"/>
    <p:with-option name="status-dir-uri" select="resolve-uri('status', $directory-uri)"/>
  </tx:htmlreport>

  <p:store name="report" method="xhtml">
    <p:with-option name="href" select="resolve-uri('report.xhtml', $directory-uri)"/>
  </p:store>

  <p:load>
    <p:with-option name="href" select="/c:result">
      <p:pipe step="report" port="result"/>
    </p:with-option>
  </p:load>

  <p:xslt>
    <p:input port="stylesheet">
      <p:inline>
        <xsl:stylesheet version="2.0">
          <xsl:template match="/">
            <xsl:if test="not(//html:p[@id = 'reported-paragraph']//html:span[tokenize(@class, '\s+') = 'BC_tooltip']
                              //html:div[tokenize(@class, '\s+') = 'BC_message-text']
                              [contains(., 'Several caption paras and image contained')])">
              <xsl:message terminate="yes">The caption diagnostic must be located on the reported paragraph.</xsl:message>
            </xsl:if>
            <xsl:if test="//@source-dir-uri or //html:meta[@name = 'source-dir-uri']
                          or (some $value in (//@*, //text()) satisfies contains($value, '/private/manuscript/'))">
              <xsl:message terminate="yes">The serialized report must omit the private source directory.</xsl:message>
            </xsl:if>
            <c:result>true</c:result>
          </xsl:template>
        </xsl:stylesheet>
      </p:inline>
    </p:input>
    <p:input port="parameters"><p:empty/></p:input>
  </p:xslt>
</p:declare-step>
