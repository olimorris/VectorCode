local M = {}

local function traverse(node, cb)
  if node == nil then
    return
  end
  if node.result ~= nil then
    traverse(node.result, cb)
  end
  if vim.isarray(node) then
    for k, v in pairs(node) do
      traverse(v, cb)
    end
    return
  end
  if vim.isarray(node.children) then
    for k, v in pairs(node.children) do
      traverse(v, cb)
    end
  end
  if not vim.list_contains({ 15, 16, 20, 21, 25 }, node.kind) then
    -- exclude certain kinds.
    if cb then
      cb(node)
    end
  end
end

---@alias VectorCode.QueryCallback fun(bufnr:integer?):string|string[]

---Retrieves all LSP document symbols from the current buffer, and use the symbols
---as query messages. Fallbacks to `make_surrounding_lines_cb` if
---`textDocument_documentSymbol` is not accessible.
---@return VectorCode.QueryCallback
function M.make_lsp_document_symbol_cb()
  return function(bufnr)
    if bufnr == 0 or bufnr == nil then
      bufnr = vim.api.nvim_get_current_buf()
    end
    local has_documentSymbol = false
    for _, client in ipairs(vim.lsp.get_clients({ bufnr = bufnr })) do
      if client.server_capabilities.documentSymbolProvider then
        has_documentSymbol = true
      end
    end
    if not has_documentSymbol then
      return M.make_surrounding_lines_cb(-1)(bufnr)
    end

    local result, err = vim.lsp.buf_request_sync(
      0,
      vim.lsp.protocol.Methods.textDocument_documentSymbol,
      { textDocument = vim.lsp.util.make_text_document_params(bufnr) }
    )
    if result ~= nil then
      local symbols = {}
      traverse(result, function(node)
        if node.name ~= nil then
          vim.list_extend(symbols, { node.name })
        end
      end)
      return symbols
    else
      return M.make_surrounding_lines_cb(20)(bufnr)
    end
  end
end

---Use the lines above and below the current line as the query messages.
---@param num_of_lines integer The number of lines to include in the query.
---@return VectorCode.QueryCallback
function M.make_surrounding_lines_cb(num_of_lines)
  return function(bufnr)
    if bufnr == 0 or bufnr == nil then
      bufnr = vim.api.nvim_get_current_buf()
    end
    if num_of_lines <= 0 then
      return table.concat(vim.api.nvim_buf_get_lines(bufnr, 0, -1, false), "\n")
    end
    local cursor_line = vim.api.nvim_win_get_cursor(0)[1]
    local start_line = cursor_line - math.floor(num_of_lines / 2)
    if start_line < 1 then
      start_line = 1
    end
    return table.concat(
      vim.api.nvim_buf_get_lines(
        bufnr,
        start_line - 1,
        start_line + num_of_lines - 1,
        false
      ),
      "\n"
    )
  end
end

return M
