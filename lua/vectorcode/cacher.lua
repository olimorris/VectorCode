local M = {}
local vc_config = require("vectorcode.config")
local notify_opts = vc_config.notify_opts

---@class VectorCodeCache
---@field enabled boolean
---@field retrieval VectorCodeResult[]?
---@field options VectorCodeConfig
---@field query_cb fun(buf_number: integer): string
---@field jobs table<integer, boolean>
---@field last_run integer?
local default_vectorcode_cache = {
  enabled = true,
  retrieval = {},
  options = vc_config.get_user_config(),
  jobs = {},
}

---@param query_message string|string[]
---@param buf_nr integer
local function async_runner(query_message, buf_nr)
  if not vim.b[buf_nr].vectorcode_cache.enabled then
    return
  end
  local cache = vim.api.nvim_buf_get_var(buf_nr, "vectorcode_cache")
  vim.api.nvim_buf_set_var(buf_nr, "vectorcode_cache", cache)
  local args = {
    "query",
    "--pipe",
    "-n",
    tostring(cache.options.n_query),
  }

  if type(query_message) == "string" then
    query_message = { query_message }
  end
  vim.list_extend(args, query_message)

  if cache.exclude_this then
    vim.list_extend(args, { "--exclude", vim.api.nvim_buf_get_name(buf_nr) })
  end
  local job = require("plenary.job"):new({
    command = "vectorcode",
    args = args,
    on_start = function() end,
    on_exit = function(self, code, signal)
      if not M.buf_is_registered(buf_nr) then
        return
      end

      vim.schedule(function()
        ---@type VectorCodeCache
        local cache = vim.api.nvim_buf_get_var(buf_nr, "vectorcode_cache")
        cache.jobs[self.pid] = nil
        vim.api.nvim_buf_set_var(buf_nr, "vectorcode_cache", cache)
      end)
      local ok, json = pcall(
        vim.json.decode,
        table.concat(self:result()) or "[]",
        { array = true, object = true }
      )
      if not ok or code ~= 0 then
        vim.schedule(function()
          if vim.api.nvim_buf_get_var(buf_nr, "vectorcode_cache").options.notify then
            vim.notify(
              "Retrieval failed:\n" .. table.concat(self:result()),
              vim.log.levels.WARN,
              notify_opts
            )
          end
        end)
        return
      end
      vim.schedule(function()
        ---@type VectorCodeCache
        local cache = vim.api.nvim_buf_get_var(buf_nr, "vectorcode_cache")
        cache.retrieval = json or {}
        vim.api.nvim_buf_set_var(buf_nr, "vectorcode_cache", cache)
        if cache.options.notify then
          vim.notify(
            ("Caching for buffer %d has completed."):format(buf_nr),
            vim.log.levels.INFO,
            notify_opts
          )
        end
      end)
    end,
  })
  vim.schedule(function()
    job:start()
    ---@type VectorCodeCache
    local cache = vim.api.nvim_buf_get_var(buf_nr, "vectorcode_cache")
    cache.jobs[job.pid] = true
    if cache.options.notify then
      vim.notify(
        ("Caching for buffer %d has started."):format(buf_nr),
        vim.log.levels.INFO,
        notify_opts
      )
    end
    cache.last_run = vim.uv.clock_gettime("realtime").sec
    vim.api.nvim_buf_set_var(buf_nr, "vectorcode_cache", cache)
  end)
end

---@param bufnr integer?
---@param opts VectorCodeConfig?
---@param query_cb VectorCodeQueryCallback?
---@param events string[]?
---@param debounce integer?
function M.register_buffer(bufnr, opts, query_cb, events, debounce)
  debounce = debounce or 10
  if bufnr == 0 or bufnr == nil then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if M.buf_is_registered(bufnr) then
    -- update the options and/or query_cb
    vim.schedule(function()
      local cache = vim.b[bufnr].vectorcode_cache
      cache.options = vim.tbl_deep_extend("force", cache.options, opts or {})
      if type(query_cb) == "function" then
        cache.query_cb = query_cb
      end
      vim.api.nvim_buf_set_var(
        bufnr or vim.api.nvim_get_current_buf(),
        "vectorcode_cache",
        cache
      )
    end)
  else
    query_cb = query_cb or require("vectorcode.utils").surrounding_lines_cb(-1)
    opts = vim.tbl_deep_extend("keep", opts or {}, vc_config.get_user_config())
    vim.schedule(function()
      ---@type VectorCodeCache
      vim.api.nvim_buf_set_var(bufnr, "vectorcode_cache", {
        enabled = true,
        retrieval = nil,
        options = opts,
        query_cb = query_cb,
        jobs = {},
      })
    end)
  end
  events = events or { "BufWritePost", "InsertEnter", "BufReadPost" }
  vim.schedule(function()
    vim.api.nvim_create_autocmd(events, {
      group = vim.api.nvim_create_augroup(
        ("VectorCodeCacheGroup%d"):format(bufnr),
        { clear = true }
      ),
      callback = function()
        assert(
          vim.b[bufnr].vectorcode_cache ~= nil,
          "buffer vectorcode cache not registered"
        )
        vim.schedule(function()
          local cache = vim.api.nvim_buf_get_var(bufnr, "vectorcode_cache") ---@cast cache VectorCodeCache
          if
            cache.last_run == nil
            or (vim.uv.clock_gettime("realtime").sec - cache.last_run) > debounce
          then
            local cb = cache.query_cb
            async_runner(cb(bufnr), bufnr)
          end
        end)
      end,
      buffer = bufnr,
    })
  end)
end

---@param bufnr integer?
---@param opts VectorCodeConfig?
function M.deregister_buffer(bufnr, opts)
  opts = opts or vc_config.get_user_config()
  if bufnr == nil or bufnr == 0 then
    bufnr = vim.api.nvim_get_current_buf()
  end
  if M.buf_is_registered(bufnr) then
    vim.api.nvim_del_augroup_by_name(("VectorCodeCacheGroup%d"):format(bufnr))
    vim.api.nvim_buf_set_var(bufnr, "vectorcode_cache", nil)
    if opts.notify then
      vim.notify(
        ("VectorCode Caching has been unregistered for buffer %d."):format(bufnr),
        vim.log.levels.INFO,
        notify_opts
      )
    end
  else
    vim.notify(
      ("VectorCode Caching hasn't been registered for buffer %d."):format(bufnr),
      vim.log.levels.ERROR,
      notify_opts
    )
  end
end

---@param bufnr integer?
---@return boolean
M.buf_is_registered = function(bufnr)
  if bufnr == 0 or bufnr == nil then
    bufnr = vim.api.nvim_get_current_buf()
  end
  return type(vim.b[bufnr].vectorcode_cache) == "table"
end

---@param bufnr integer?
---@return VectorCodeResult[]
M.query_from_cache = function(bufnr)
  local result = {}
  if bufnr == 0 or bufnr == nil then
    bufnr = vim.api.nvim_get_current_buf()
  end
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

function M.lualine()
  return {
    function()
      local message = "VectorCode: "
      ---@type VectorCodeCache
      local cache = vim.b.vectorcode_cache
      if cache.enabled then
        if cache.retrieval ~= nil then
          message = message .. tostring(#cache.retrieval)
        end
        if #(vim.tbl_keys(cache.jobs)) > 0 then
          message = message .. "  "
        else
          message = message .. "  "
        end
      else
        message = message .. " "
      end
      return message
    end,
    cond = function()
      return vim.b.vectorcode_cache ~= nil
    end,
  }
end

---@param check_item string?
---@param on_success fun()?
---@param on_failure fun()?
function M.async_check(check_item, on_success, on_failure)
  check_item = check_item or "config"
  local return_code
  vim.system({ "vectorcode", "check", check_item }, {}, function(out)
    if out.code == 0 and type(on_success) == "function" then
      on_success()
    elseif out.code ~= 0 and type(on_failure) == "function" then
      on_failure()
    end
  end)
  return return_code == 0
end
return M
