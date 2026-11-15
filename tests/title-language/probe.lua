-- Observe the language IDs on actual shipped glyph nodes, after Babel and shaping.
local out = assert(io.open('glyph-languages.tsv', 'w'))
local page = 0
local function walk(head)
  for n in node.traverse(head) do
    if n.id == node.id('glyph') then
      local context = node.has_attribute(n, luatexbase.attributes.languageTestContext)
      if context then
        out:write(page, '\t', context, '\t', n.lang, '\t', utf8.char(n.char), '\n')
      end
    elseif n.id == node.id('hlist') or n.id == node.id('vlist') then
      walk(n.head)
    end
  end
end
luatexbase.add_to_callback('pre_shipout_filter', function(head)
  page = page + 1
  walk(head)
  out:flush()
  return true
end, 'title-language-observer')
