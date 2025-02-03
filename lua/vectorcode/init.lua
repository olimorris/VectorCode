local M = {}

local vc_config = require("vectorcode.config")
local get_config = vc_config.get_user_config

local notify_opts = vc_config.notify_opts

---@class VectorCodeResult
---@field path string
---@field document string

M.query = vc_config.check_cli_wrap(
  ---@param query_message string|string[]
  ---@param opts VectorCodeConfig?
  ---@return VectorCodeResult[]
  function(query_message, opts)
    opts = vim.tbl_deep_extend("force", get_config(), opts or {})
    if opts.n_query == 0 then
      if opts.notify then
        vim.notify("n_query is 0. Not sending queries.")
      end
      return {}
    end
    ---@type string?
    local raw_response = ""

    if opts.notify then
      vim.notify(
        ("Started retrieving %s documents."):format(tostring(opts.n_query)),
        vim.log.levels.INFO,
        notify_opts
      )
    end
    local args = { "query", "--pipe", "-n", tostring(opts.n_query) }
    if type(query_message) == "string" then
      query_message = { query_message }
    end
    vim.list_extend(args, query_message)

    if opts.exclude_this then
      vim.list_extend(args, { "--exclude", vim.api.nvim_buf_get_name(0) })
    end
    local job = require("plenary.job"):new({
      command = "vectorcode",
      args = args,
      on_exit = function(self, code, signal)
        if code ~= 0 then
          raw_response = nil
        else
          raw_response = table.concat(self:result(), "")
        end
      end,
      and_then_on_failure = function()
        raw_response = nil
      end,
    })
    job:sync(opts.timeout_ms)

    local decoded_response = {}
    if raw_response ~= nil and raw_response ~= "" then
      decoded_response = vim.json.decode(raw_response, { object = true, array = true })
      if opts.notify then
        vim.notify(
          ("Retrieved %s documents."):format(tostring(#decoded_response)),
          vim.log.levels.INFO,
          notify_opts
        )
      end
    end

    return decoded_response
  end
)

M.vectorise = vc_config.check_cli_wrap(
  ---@param files string|string[]
  ---@param project_root string?
  function(files, project_root)
    local args = { "--pipe", "vectorise" }
    if project_root ~= nil then
      vim.list_extend(args, { "--project_root", project_root })
    elseif
      M.check("config", function(obj)
        if obj.code == 0 then
          project_root = obj.stdout
        end
      end)
    then
      vim.list_extend(args, { "--project_root", project_root })
    end
    if type(files) == "string" then
      files = { files }
    end
    local valid_files = {}
    for k, v in pairs(files) do
      if vim.fn.filereadable(v) == 1 then
        vim.list_extend(valid_files, { files[k] })
      end
    end
    if #valid_files > 0 then
      vim.list_extend(args, valid_files)
    else
      return
    end
    if get_config().notify then
      vim.schedule(function()
        vim.notify(
          ("Vectorising %s"):format(table.concat(files, ", ")),
          vim.log.levels.INFO,
          notify_opts
        )
      end)
    end
    require("plenary.job")
      :new({
        command = "vectorcode",
        args = args,
        on_exit = function(job, return_code)
          if get_config().notify then
            if return_code == 0 then
              vim.notify(
                "Indexing successful.",
                vim.log.levels.INFO,
                { title = "VectorCode" }
              )
            else
              vim.notify(
                "Indexing failed.",
                vim.log.levels.WARN,
                { title = "VectorCode" }
              )
            end
          end
        end,
      })
      :start()
  end
)

---@param check_item string?
---@param stdout_cb fun(stdout: vim.SystemCompleted)?
---@return boolean
function M.check(check_item, stdout_cb)
  if not vc_config.has_cli() then
    return false
  end
  check_item = check_item or "config"
  local return_code
  vim
    .system({ "vectorcode", "check", check_item }, {}, function(out)
      return_code = out.code
      if type(stdout_cb) == "function" then
        stdout_cb(out)
      end
    end)
    :wait()
  return return_code == 0
end

M.setup = vc_config.setup
return M
