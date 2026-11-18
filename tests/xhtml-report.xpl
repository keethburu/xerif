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
  <p:option name="source-dir-uri" select="'file:///private/manuscript/'"/>
  <p:import href="../xpl/htmlreport.xpl"/>
  <p:import href="../xpl/export-xhtml.xpl"/>
  <p:variable name="directory-uri"
    select="if (ends-with($scratch-dir-uri, '/')) then $scratch-dir-uri else concat($scratch-dir-uri, '/')"/>

  <p:template name="fixture">
    <p:input port="source"><p:empty/></p:input>
    <p:input port="template">
      <p:inline>
        <c:fixture>
          <dbk:hub>
            <dbk:info>
              <dbk:keywordset role="hub">
                <dbk:keyword role="source-dir-uri">{$source-dir-uri}</dbk:keyword>
              </dbk:keywordset>
            </dbk:info>
          </dbk:hub>
          <html:html source-dir-uri="{$source-dir-uri}">
            <html:head>
              <html:title>Report fixture</html:title>
              <html:meta name="source-dir-uri" content="{$source-dir-uri}"/>
            </html:head>
            <html:body>
              <html:p id="reported-paragraph" srcpath="Stories/Story_u1.xml?xpath=/Story[1]/ParagraphStyleRange[1]">Caption with image</html:p>
            </html:body>
          </html:html>
          <svrl:schematron-output tr:rule-family="flat-hub">
            <svrl:successful-report id="multi_para_caption_with_image" role="error" location="/dbk:hub/dbk:para[1]">
              <svrl:text>
                <s:span class="srcpath">{$exact-locator}</s:span>
                <html:span class="issue">Several caption paras and image contained</html:span>
              </svrl:text>
            </svrl:successful-report>
            <svrl:successful-report id="table_in_heading" role="warning" location="/dbk:hub/dbk:title[1]">
              <svrl:text>
                <s:span class="srcpath">{$source-dir-uri}</s:span>
                <html:span class="issue">Table in heading</html:span>
              </svrl:text>
            </svrl:successful-report>
            <svrl:successful-report id="missing_story" role="warning" location="/dbk:hub/dbk:para[2]">
              <svrl:text>
                <s:span class="srcpath">{$missing-locator}</s:span>
                <html:span class="issue">Unavailable story</html:span>
              </svrl:text>
            </svrl:successful-report>
            <svrl:successful-report id="public_location" role="warning" location="/dbk:hub/dbk:para[3]">
              <svrl:text>
                <s:span class="srcpath">https://editorial.example/private/book-guide/</s:span>
                <html:span class="issue">Published reference</html:span>
              </svrl:text>
            </svrl:successful-report>
          </svrl:schematron-output>
        </c:fixture>
      </p:inline>
    </p:input>
    <p:input port="parameters"><p:empty/></p:input>
    <p:with-param name="source-dir-uri" select="$source-dir-uri"/>
    <p:with-param name="exact-locator"
      select="concat(if (starts-with($source-dir-uri, 'file:')) then $source-dir-uri else '',
                     'Stories/Story_u1.xml?xpath=/Story[1]/ParagraphStyleRange[1]')"/>
    <p:with-param name="missing-locator"
      select="concat(replace($source-dir-uri, '^file:/+', 'file:/'), 'Stories/Missing.xml')"/>
  </p:template>

  <tx:export-xhtml>
    <p:input port="source" select="/c:fixture/html:html">
      <p:pipe step="fixture" port="result"/>
    </p:input>
  </tx:export-xhtml>

  <tx:htmlreport>
    <p:input port="paths">
      <p:inline><c:param-set><c:param name="interface-language" value="en"/></c:param-set></p:inline>
    </p:input>
    <p:input port="reports" select="/c:fixture/svrl:schematron-output">
      <p:pipe step="fixture" port="result"/>
    </p:input>
    <p:with-option name="source-dir-uri"
      select="string(/c:fixture/dbk:hub/dbk:info/dbk:keywordset[@role = 'hub']/dbk:keyword[@role = 'source-dir-uri'])">
      <p:pipe step="fixture" port="result"/>
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
          <xsl:param name="source-dir-uri"/>
          <xsl:template match="/">
            <xsl:if test="not(//html:p[@id = 'reported-paragraph']//html:span[tokenize(@class, '\s+') = 'BC_tooltip']
                              //html:div[tokenize(@class, '\s+') = 'BC_message-text']
                              [contains(., 'Several caption paras and image contained')])">
              <xsl:message terminate="yes">The caption diagnostic must be located on the reported paragraph.</xsl:message>
            </xsl:if>
            <xsl:variable name="fallback" select="//html:p[tokenize(@class, '\s+') = 'BC_fallback-messages']"/>
            <xsl:if test="not($fallback[contains(., 'Table in heading')]/html:span[@class = 'BC_srcpath'][. = '']
                           and $fallback[contains(., 'Unavailable story')]/html:span[@class = 'BC_srcpath'][. = 'Stories/Missing.xml'])">
              <xsl:message terminate="yes">Fallback diagnostics must retain their message and any relative location.</xsl:message>
            </xsl:if>
            <xsl:if test="not($fallback[contains(., 'Published reference')]/html:span[@class = 'BC_srcpath']
                              = 'https://editorial.example/private/book-guide/')">
              <xsl:message terminate="yes">The fallback report must preserve the public locator.</xsl:message>
            </xsl:if>
            <xsl:if test="//@source-dir-uri or //html:meta[@name = 'source-dir-uri']
                          or (some $value in (//@*, //text()) satisfies contains($value, $source-dir-uri))">
              <xsl:message terminate="yes">The serialized report must omit the private source directory.</xsl:message>
            </xsl:if>
            <c:result>true</c:result>
          </xsl:template>
        </xsl:stylesheet>
      </p:inline>
    </p:input>
    <p:input port="parameters"><p:empty/></p:input>
    <p:with-param name="source-dir-uri" select="$source-dir-uri"/>
  </p:xslt>
</p:declare-step>
