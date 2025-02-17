---@class VectorCodeConfig
---@field n_query integer?
---@field notify boolean?
---@field timeout_ms number?
---@field exclude_this boolean?
---@field events string|string[]|nil
local config = {
  n_query = 1,
  notify = true,
  timeout_ms = 5000,
  exclude_this = true,
  events = { "BufWritePost", "InsertEnter", "BufReadPost" },
}

local setup_config = vim.deepcopy(config, true)
local notify_opts = { title = "VectorCode" }

---@param opts {notify:boolean}?
local has_cli = function(opts)
  opts = opts or { notify = false }
  local ok = vim.fn.executable("vectorcode") == 1
  if not ok and opts.notify then
    vim.notify("VectorCode CLI is not executable!", vim.log.levels.ERROR, notify_opts)
  end
  return ok
end

---@generic T: function
---@param func T
---@return T
local check_cli_wrap = function(func)
  if not has_cli() then
    vim.notify("VectorCode CLI is not executable!", vim.log.levels.ERROR, notify_opts)
  end
  return func
end
return {
  get_default_config = function()
    return vim.deepcopy(config, true)
  end,

  setup = check_cli_wrap(
    ---@param opts VectorCodeConfig?
    function(opts)
      setup_config = vim.tbl_deep_extend("force", config, opts or {})
    end
  ),

  get_user_config = function()
    return vim.deepcopy(setup_config, true)
  end,
  notify_opts = notify_opts,

  ---@return boolean
  has_cli = has_cli,

  check_cli_wrap = check_cli_wrap,
}
