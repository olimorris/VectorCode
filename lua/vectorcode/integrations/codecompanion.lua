return {
  chat = {
    slash_command = {
      description = "Add relevant files from the codebase.",
      ---@param chat CodeCompanion.Chat
      callback = function(chat)
        local codebase_prompt = ""
        local ok, vc_cache = pcall(require, "vectorcode.cacher")
        if ok then
          local bufnr = chat.context.bufnr
          if not vc_cache.buf_is_registered(bufnr) then
            return
          end
          codebase_prompt =
            "The following are relevant files from the repository. Use them as extra context."
          local query_result = vc_cache.query_from_cache(bufnr)
          local id = tostring(#query_result) .. " file(s) from codebase"
          for _, file in pairs(query_result) do
            codebase_prompt = codebase_prompt
              .. "<|file_sep|>"
              .. file.path
              .. "\n"
              .. file.document
          end
          chat:add_message(
            { content = codebase_prompt, role = "user" },
            { visible = false, id = id }
          )
          chat.references:add({
            source = "codebase",
            name = "VectorCode",
            id = id,
          })
        end
      end,
    },
  },
}
