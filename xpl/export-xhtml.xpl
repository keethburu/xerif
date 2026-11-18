<?xml version="1.0" encoding="UTF-8"?>
<p:declare-step xmlns:p="http://www.w3.org/ns/xproc"
  xmlns:html="http://www.w3.org/1999/xhtml"
  xmlns:tx="http://transpect.io/xerif"
  version="1.0" type="tx:export-xhtml">

  <p:input port="source"/>
  <p:output port="result"/>

  <p:delete match="/html:html/@xml:base | @source-dir-uri | html:meta[@name = 'source-dir-uri']"/>
</p:declare-step>
