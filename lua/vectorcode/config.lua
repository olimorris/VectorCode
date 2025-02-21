---@type VectorCode.Opts
local config = {
  async_opts = {
    debounce = 10,
    events = { "BufWritePost", "InsertEnter", "BufReadPost" },
    exclude_this = true,
    n_query = 1,
    notify = false,
    query_cb = require("vectorcode.utils").make_surrounding_lines_cb(-1),
    run_on_register = false,
    single_job = false,
  },
  events = { "BufWritePost", "InsertEnter", "BufReadPost" },
  exclude_this = true,
  n_query = 1,
  notify = true,
  timeout_ms = 5000,
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
    ---@param opts VectorCode.Opts?
    function(opts)
      opts = opts or {}
      if opts and opts.events then
        vim.deprecate(
          "`opts.events`",
          "`opts.async_opts.events`",
          "0.3.7",
          "VectorCode",
          true
        )
      end
      setup_config = vim.tbl_deep_extend("force", config, opts or {})
      for k, v in pairs(setup_config.async_opts) do
        if
          setup_config[k] ~= nil
          and (opts.async_opts == nil or opts.async_opts[k] == nil)
        then
          -- NOTE: a lot of options are mutual between `setup_config` and `async_opts`.
          -- If users do not explicitly set them `async_opts`, copy them from `setup_config`.
          setup_config.async_opts = vim.tbl_deep_extend(
            "force",
            setup_config.async_opts,
            { [k] = setup_config[k] }
          )
        end
      end
    end
  ),

  ---@return VectorCode.Opts
  get_user_config = function()
    return vim.deepcopy(setup_config, true)
  end,
  ---@return VectorCode.QueryOpts
  get_query_opts = function()
    return {
      exclude_this = setup_config.exclude_this,
      n_query = setup_config.n_query,
      notify = setup_config.notify,
      timeout_ms = setup_config.timeout_ms,
    }
  end,
  notify_opts = notify_opts,

  ---@return boolean
  has_cli = has_cli,

  check_cli_wrap = check_cli_wrap,
}
