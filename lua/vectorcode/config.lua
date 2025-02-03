---@class VectorCodeConfig
---@field n_query integer?
---@field notify boolean?
---@field timeout_ms number?
---@field exclude_this boolean?
local config = {
  n_query = 1,
  notify = true,
  timeout_ms = 5000,
  exclude_this = true,
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

  ---@param opts VectorCodeConfig?
  setup = check_cli_wrap(function(opts)
    setup_config = vim.tbl_deep_extend("force", config, opts or {})
    vim.api.nvim_create_user_command("VectorCode", function(args)
      if args.fargs[1] == "register" then
        local bufnr = vim.api.nvim_get_current_buf()
        require("vectorcode.cacher").register_buffer(bufnr)
        vim.notify(
          ("Buffer %d has been registered for VectorCode."):format(bufnr),
          vim.log.levels.INFO,
          notify_opts
        )
      elseif args.fargs[1] == "deregister" then
        local buf_nr = vim.api.nvim_get_current_buf()
        require("vectorcode.cacher").deregister_buffer(buf_nr, { notify = true })
      else
        vim.notify(
          ([[Command "VectorCode %s" was not recognised.]]):format(args.args),
          vim.log.levels.ERROR,
          notify_opts
        )
      end
    end, {
      nargs = 1,
      complete = function(arglead, cmd, cursorpos)
        if require("vectorcode.cacher").buf_is_registered(0) then
          return { "register", "deregister" }
        else
          return { "register" }
        end
      end,
    })
  end),

  get_user_config = function()
    return vim.deepcopy(setup_config, true)
  end,
  notify_opts = notify_opts,

  ---@return boolean
  has_cli = has_cli,

  check_cli_wrap = check_cli_wrap,
}
