return {
  chat = {
    ---@param component_cb (fun(result:VectorCodeResult):string)?
    make_slash_command = function(component_cb)
      return {
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
            local query_result = vc_cache.make_prompt_component(bufnr, component_cb)
            local id = tostring(query_result.count) .. " file(s) from codebase"
            codebase_prompt = codebase_prompt .. query_result.content
            chat:add_message(
              { content = codebase_prompt, role = "user" },
              { visible = false, id = id }
            )
            chat.references:add({
              source = "VectorCode",
              name = "VectorCode",
              id = id,
            })
          end
        end,
      }
    end,
  },
}
