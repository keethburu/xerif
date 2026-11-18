<?xml version="1.0" encoding="UTF-8"?>
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc"
  xmlns:c="http://www.w3.org/ns/xproc-step"
  xmlns:html="http://www.w3.org/1999/xhtml"
  xmlns:svg="http://www.w3.org/2000/svg"
  xmlns:tx="http://transpect.io/xerif"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  version="1.0">

  <p:output port="result" sequence="true">
    <p:pipe step="check-publication" port="result"/>
  </p:output>
  <p:option name="scratch-dir-uri" required="true"/>
  <p:import href="../xpl/html2epub.xpl"/>
  <p:import href="../xpl/tei2epub.xpl"/>
  <p:variable name="publication-dir-uri"
    select="if (ends-with($scratch-dir-uri, '/')) then $scratch-dir-uri else concat($scratch-dir-uri, '/')"/>
  <p:variable name="expected-directory" select="replace($scratch-dir-uri, '/$', '')"/>

  <p:store name="chapter" method="xhtml">
    <p:input port="source">
      <p:inline>
        <html:html><html:body><html:h1 id="start">Published chapter</html:h1></html:body></html:html>
      </p:inline>
    </p:input>
    <p:with-option name="href" select="resolve-uri('chapters/next.xhtml', $publication-dir-uri)"/>
  </p:store>

  <p:store name="cover">
    <p:input port="source">
      <p:inline>
        <svg:svg width="1" height="1"><svg:title>Published cover</svg:title></svg:svg>
      </p:inline>
    </p:input>
    <p:with-option name="href" select="resolve-uri('images/cover.svg', $publication-dir-uri)"/>
  </p:store>

  <p:identity name="paths">
    <p:input port="source">
      <p:inline><c:param-set><c:param name="basename" value="proof"/></c:param-set></p:inline>
    </p:input>
  </p:identity>

  <p:for-each name="check-publication">
    <p:iteration-source>
      <p:inline>
        <c:base converter="html" name="absolute" epub-base="file:///private/manuscript/">file:///private/manuscript/</c:base>
      </p:inline>
      <p:inline>
        <c:base converter="html" name="relative" epub-base="../manuscript/">../manuscript/</c:base>
      </p:inline>
      <p:inline>
        <c:base converter="tei" name="absolute" epub-base="file:///private/epub-output/proof.epub">file:///private/manuscript/</c:base>
      </p:inline>
      <p:inline>
        <c:base converter="tei" name="relative" epub-base="file:///private/epub-output/proof.epub">../manuscript/</c:base>
      </p:inline>
    </p:iteration-source>
    <p:output port="result"/>
    <p:variable name="source-base" select="string(/c:base)"/>
    <p:variable name="expected-epub-base" select="string(/c:base/@epub-base)"/>
    <p:variable name="converter" select="string(/c:base/@converter)"/>
    <p:variable name="filename" select="concat($converter, '-', /c:base/@name, '.xhtml')"/>

    <p:add-attribute name="metadata" match="/epub-config" attribute-name="expected-epub-base">
      <p:input port="source">
        <p:inline><epub-config><cover href="images/cover.svg"/></epub-config></p:inline>
      </p:input>
      <p:with-option name="attribute-value" select="$expected-epub-base"/>
    </p:add-attribute>

    <p:add-attribute match="/html:html" attribute-name="xml:base">
      <p:input port="source">
        <p:inline>
          <html:html xml:lang="en" dir="ltr" source-dir-uri="file:///private/manuscript/">
            <html:head>
              <html:title>Proof</html:title>
              <html:meta name="source-dir-uri" content="file:///private/manuscript/"/>
              <html:meta name="description" content="Published proof"/>
            </html:head>
            <html:body>
              <html:a href="chapters/next.xhtml#start">Next chapter</html:a>
              <html:img src="images/cover.svg" alt="Cover"/>
            </html:body>
          </html:html>
        </p:inline>
      </p:input>
      <p:with-option name="attribute-value" select="$source-base"/>
    </p:add-attribute>

    <p:choose>
      <p:when test="$converter = 'html'">
        <p:output port="result" primary="true">
          <p:pipe step="convert-html" port="html"/>
        </p:output>
        <tx:html2epub name="convert-html">
          <p:input port="params"><p:pipe step="paths" port="result"/></p:input>
          <p:input port="meta"><p:pipe step="metadata" port="result"/></p:input>
          <p:with-option name="debug" select="'no'"/>
        </tx:html2epub>
        <p:sink/>
      </p:when>
      <p:otherwise>
        <p:output port="result" primary="true">
          <p:pipe step="convert-tei" port="html"/>
        </p:output>
        <tx:tei2epub name="convert-tei">
          <p:input port="params"><p:pipe step="paths" port="result"/></p:input>
          <p:input port="meta"><p:pipe step="metadata" port="result"/></p:input>
          <p:with-option name="out-dir-uri" select="'file:///private/epub-output'"/>
          <p:with-option name="debug" select="'no'"/>
        </tx:tei2epub>
        <p:sink/>
      </p:otherwise>
    </p:choose>

    <p:store name="proof" method="xhtml">
      <p:with-option name="href" select="resolve-uri($filename, $publication-dir-uri)"/>
    </p:store>

    <p:wrap-sequence wrapper="c:publication">
      <p:input port="source">
        <p:pipe step="proof" port="result"/>
        <p:pipe step="chapter" port="result"/>
        <p:pipe step="cover" port="result"/>
      </p:input>
    </p:wrap-sequence>

    <p:load>
      <p:with-option name="href" select="
        if (deep-equal(
              for $uri in /c:publication/c:result return replace($uri, '^file:///', 'file:/'),
              for $path in ($filename, 'chapters/next.xhtml', 'images/cover.svg')
              return replace(concat($expected-directory, '/', $path), '^file:///', 'file:/')
            ))
        then /c:publication/c:result[1]
        else error(QName('http://transpect.io/xerif', 'tx:WRONG_PUBLICATION_DIRECTORY'),
                   'Fixture files must be stored in the requested publication directory.')"/>
    </p:load>

    <p:xslt>
      <p:input port="stylesheet">
        <p:inline>
          <xsl:stylesheet version="2.0">
            <xsl:template match="/">
              <xsl:variable name="root" select="html:html"/>
              <xsl:variable name="link" select="$root/html:body/html:a"/>
              <xsl:variable name="image" select="$root/html:body/html:img"/>
              <xsl:if test="//@source-dir-uri or //html:meta[@name = 'source-dir-uri']">
                <xsl:message terminate="yes">Serialized XHTML must omit source-dir-uri.</xsl:message>
              </xsl:if>
              <xsl:if test="$root/@xml:base or not($root/@xml:lang = 'en' and $root/@dir = 'ltr'
                            and $root/html:head/html:title = 'Proof'
                            and $root/html:head/html:meta[@name = 'description']/@content = 'Published proof'
                            and $link/@href = 'chapters/next.xhtml#start' and $image/@src = 'images/cover.svg')">
                <xsl:message terminate="yes">Serialized XHTML must preserve the title, language, direction, and publication-relative references and omit the source base.</xsl:message>
              </xsl:if>
              <xsl:variable name="target" select="resolve-uri($link/@href, base-uri($link))"/>
              <xsl:variable name="chapter" select="doc(substring-before($target, '#'))"/>
              <xsl:variable name="cover" select="doc(resolve-uri($image/@src, base-uri($image)))"/>
              <xsl:if test="not($chapter//html:h1[@id = substring-after($target, '#')] = 'Published chapter'
                            and $cover/svg:svg/svg:title = 'Published cover')">
                <xsl:message terminate="yes">The link fragment and image must resolve to the caller's published targets.</xsl:message>
              </xsl:if>
              <c:result>true</c:result>
            </xsl:template>
          </xsl:stylesheet>
        </p:inline>
      </p:input>
      <p:input port="parameters"><p:empty/></p:input>
    </p:xslt>
  </p:for-each>
</p:declare-step>
