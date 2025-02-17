local xml2lua = require("codecompanion.utils.xml.xml2lua")
return {
  name = "vectorcode",
  cmds = { { "vectorcode", "query", "--pipe" } },
  handlers = {
    ---@param self CodeCompanion.Tools
    setup = function(self)
      local tool = self.tool
      local n_query = tool.request.action.count
      local keywords =
        vim.json.decode(tool.request.action.query, { object = true, array = true })
      vim.list_extend(tool.cmds[1], { "-n", tostring(n_query) })
      vim.list_extend(tool.cmds[1], keywords)
    end,
  },
  schema = {
    {
      tool = {
        _attr = { name = "vectorcode" },
        action = {
          _attr = { type = "query" },
          query = '["keyword1", "keyword2"]',
          count = 5,
        },
      },
    },
    {
      tool = {
        _attr = { name = "vectorcode" },
        action = {
          _attr = { type = "query" },
          query = '["keyword1"]',
          count = 2,
        },
      },
    },
  },
  system_prompt = function(schema)
    return string.format(
      [[### VectorCode, a repository indexing and query tool.

1. **Purpose**: This gives you the ability to access the repository to find information that you may not know.

2. **Usage**: Return an XML markdown code block that retrieves relevant documents corresponding to the generated query.

3. **Key Points**:
  - **Use at your discretion** when you feel you don't have enough information about the repository or project
  - Ensure XML is **valid and follows the schema**
  - **Don't escape** special characters
  - Make sure the tools xml block is **surrounded by ```xml**
  - seperate phrases into distinct keywords when appropriate
  - For a symbol defined/declared in a different file, this tool may be able to find the definition. Add the name of the symbol to the query keywords if needed
  - the query should be a JSON array of strings. Each string is either a word or a phrase
  - The embeddings are generated from source code, so using keywords that may be used as a variable name may help with the retrieval
  - The path of a retrieved file will be wrapped in `<path>` and `</path>` tags. Its content will be right after the `</path>` tag, wrapped by `<content>` and `</content>` tags

4. **Actions**:

a) **Query for 5 documents using 2 keywords: `keyword1` and `keyword2`**:

```xml
%s
```

b) **Query for 2 documents using one keyword: `keyword1`**:

```xml
%s
```

Remember:
- Minimize explanations unless prompted. Focus on generating correct XML.]],
      xml2lua.toXml({ tools = { schema[1] } }),
      xml2lua.toXml({ tools = { schema[2] } })
    )
  end,
  output = {
    error = function(self, cmd, stderr)
      if type(stderr) == "table" then
        stderr = table.concat(stderr, "\n")
      end

      self.chat:add_message({
        role = "user",
        content = string.format(
          [[After the VectorCode tool completed, there was an error:
<error>
%s
</error>
]],
          stderr
        ),
      }, { visible = false })

      self.chat:add_message({
        role = "user",
        content = "I've shared the error message from the VectorCode tool with you.\n",
      }, { visible = false })
    end,
    success = function(self, cmd, stdout)
      local retrievals = {}
      if type(stdout) == "table" then
        retrievals =
          vim.json.decode(table.concat(stdout, "\n"), { array = true, object = true })
      end

      for _, file in ipairs(retrievals) do
        self.chat:add_message({
          role = "user",
          content = string.format(
            [[Here is a file the VectorCode tool retrieved:
<path>
%s
</path>
<content>
%s
</content>
]],
            file.path,
            file.document
          ),
        }, { visible = false })
      end

      self.chat:add_message({
        role = "user",
        content = "I've shared the content from the VectorCode tool with you.\n",
      }, { visible = false })
    end,
  },
}
