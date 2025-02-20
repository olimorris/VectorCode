return function()
  return {
    function()
      local message = "VectorCode: "
      ---@type VectorCode.Cache
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
