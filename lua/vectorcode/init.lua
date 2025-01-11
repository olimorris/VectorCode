local M = {}

---@class VectorCodeConfig
---@field n_query integer
local config = { n_query = 1 }

---@class VectorCodeResult
---@field path string
---@field document string

---@param query_message string
---@param opts VectorCodeConfig?
---@return VectorCodeResult[]
M.query = function(query_message, opts)
  opts = vim.tbl_deep_extend("force", config, opts or {})
  if opts.n_query == 0 then
    return {}
  end
  ---@type string?
  local raw_response = ""

  require("plenary.job")
    :new({
      command = "vectorcode",
      args = { "query", "--pipe", "-n", tostring(opts.n_query), query_message },
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
    :sync()

  if raw_response == nil then
    return {}
  end

  return vim.json.decode(raw_response, { object = true, array = true })
end

---@param files string|string[]
---@param project_root string?
M.vectorise = function(files, project_root)
  local args = { "--pipe", "vectorise" }
  if project_root ~= nil then
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
  require("plenary.job")
    :new({
      command = "vectorcode",
      args = args,
      on_exit = function(job, return_code)
        if return_code == 0 then
          vim.notify(
            "Indexing successful.",
            vim.log.levels.INFO,
            { title = "VectorCode" }
          )
        else
          vim.notify("Indexing failed.", vim.log.levels.WARN, { title = "VectorCode" })
        end
      end,
    })
    :start()
end

---@param opts VectorCodeConfig
M.setup = function(opts)
  if vim.fn.executable("vectorcode") ~= 1 then
    vim.notify(
      "vectorcode executable is not installed.",
      vim.log.levels.ERROR,
      { title = "VectorCode" }
    )
  end

  config = vim.tbl_deep_extend("force", config, opts or {})
end
return M
