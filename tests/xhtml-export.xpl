<?xml version="1.0" encoding="UTF-8"?>
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc"
  xmlns:html="http://www.w3.org/1999/xhtml"
  xmlns:tx="http://transpect.io/xerif"
  version="1.0">

  <p:output port="result" sequence="true">
    <p:pipe step="local-base" port="result"/>
    <p:pipe step="portable-base" port="result"/>
  </p:output>
  <p:import href="../xpl/export-xhtml.xpl"/>

  <p:identity>
    <p:input port="source">
      <p:inline>
        <html:html xml:base="file:///private/manuscript/" xml:lang="en" dir="ltr">
          <html:head><html:title>Proof</html:title></html:head>
          <html:body>
            <html:a href="chapters/next.xhtml#start">Next chapter</html:a>
            <html:img src="images/cover.png" alt="Cover"/>
          </html:body>
        </html:html>
      </p:inline>
    </p:input>
  </p:identity>

  <tx:export-xhtml/>

  <p:compare name="local-base" fail-if-not-equal="true">
    <p:input port="alternate">
      <p:inline>
        <html:html xml:lang="en" dir="ltr">
          <html:head><html:title>Proof</html:title></html:head>
          <html:body>
            <html:a href="chapters/next.xhtml#start">Next chapter</html:a>
            <html:img src="images/cover.png" alt="Cover"/>
          </html:body>
        </html:html>
      </p:inline>
    </p:input>
  </p:compare>

  <p:identity name="portable">
    <p:input port="source">
      <p:inline>
        <html:html xml:base="../publication/">
          <html:body><html:a href="chapter.xhtml">Chapter</html:a></html:body>
        </html:html>
      </p:inline>
    </p:input>
  </p:identity>
  <tx:export-xhtml/>
  <p:compare name="portable-base" fail-if-not-equal="true">
    <p:input port="alternate">
      <p:pipe step="portable" port="result"/>
    </p:input>
  </p:compare>
</p:declare-step>
