local M = {}
local vc_config = require("vectorcode.config")
local notify_opts = vc_config.notify_opts

---@class VectorCodeCache
---@field enabled boolean
---@field retrieval VectorCodeResult[]?
---@field options VectorCodeConfig
---@field query_cb (fun(buf_number: integer): string)?
local default_vectorcode_cache = {
  enabled = true,
  retrieval = {},
  options = vc_config.get_user_config(),
}

---@param query_message string
---@param buf_nr integer
local function async_runner(query_message, buf_nr)
  if not vim.b[buf_nr].vectorcode_cache.enabled then
    return
  end
  vim.system(
    {
      "vectorcode",
      "query",
      "--pipe",
      "-n",
      tostring(vim.b[buf_nr].vectorcode_cache.options.n_query),
      query_message,
    },
    {},
    vim.schedule_wrap(function(obj)
      local ok, json =
        pcall(vim.json.decode, obj.stdout or "[]", { array = true, object = true })
      if ok then
        ---@type VectorCodeCache
        local cache = vim.api.nvim_buf_get_var(buf_nr, "vectorcode_cache")
        cache.retrieval = json
        vim.api.nvim_buf_set_var(buf_nr, "vectorcode_cache", cache)
        if cache.options.notify then
          vim.notify(
            ("Caching for buffer %d has completed."):format(buf_nr),
            vim.log.levels.INFO,
            notify_opts
          )
        end
      end
    end)
  )
end

---@param bufnr integer?
---@param opts VectorCodeConfig?
---@param query_cb (fun(buf_number: integer): string)?
---@param events string[]
function M.register_buffer(bufnr, opts, query_cb, events)
  events = events or { "BufWritePost", "InsertEnter", "BufReadPost" }
  if M.buf_is_registered(bufnr) then
    -- update the options and/or query_cb
    vim.schedule(function()
      vim.b[bufnr].vectorcode_cache.options =
        vim.tbl_deep_extend("force", vim.b[bufnr].vectorcode_cache.options, opts or {})
      if type(query_cb) == "function" then
        vim.b[bufnr].vectorcode_cache.query_cb = query_cb
      end
    end)
    return
  end
  query_cb = query_cb
    or function(buf_number)
      return table.concat(vim.api.nvim_buf_get_lines(buf_number, 0, -1, false), "\n")
    end
  opts = vim.tbl_deep_extend("keep", opts or {}, vc_config.get_user_config())
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  vim.schedule(function()
    ---@type VectorCodeCache
    vim.api.nvim_buf_set_var(bufnr, "vectorcode_cache", {
      enabled = true,
      retrieval = nil,
      options = opts,
      query_cb = query_cb,
    })
    vim.api.nvim_create_autocmd(events, {
      callback = function()
        assert(
          vim.b[bufnr].vectorcode_cache ~= nil,
          "buffer vectorcode cache not registered"
        )
        vim.schedule(function()
          local cb = vim.b[bufnr].vectorcode_cache.query_cb
          async_runner(cb(bufnr), bufnr)
        end)
      end,
      buffer = bufnr,
    })
  end)
end

---@param bufnr integer?
---@return boolean
M.buf_is_registered = function(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  return type(vim.b[bufnr].vectorcode_cache) == "table"
end

---@param bufnr integer?
---@return VectorCodeResult[]
M.query_from_cache = function(bufnr)
  local result = {}
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  if M.buf_is_registered(bufnr) then
    ---@type VectorCodeCache
    local vectorcode_cache = vim.api.nvim_buf_get_var(bufnr, "vectorcode_cache")
    result = vectorcode_cache.retrieval or {}
    if vectorcode_cache.options.notify then
      vim.notify(
        ("Retrieved %d documents from cache."):format(#result),
        vim.log.levels.INFO,
        notify_opts
      )
    end
  end
  return result
end

return M
