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
return {
  get_default_config = function()
    return vim.deepcopy(config, true)
  end,

  ---@param opts VectorCodeConfig?
  setup = function(opts)
    setup_config = vim.tbl_deep_extend("force", config, opts or {})
  end,

  get_user_config = function()
    return vim.deepcopy(setup_config, true)
  end,
  notify_opts = { title = "VectorCode" },
}
