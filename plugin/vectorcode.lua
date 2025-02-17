local notify_opts = require("vectorcode.config").notify_opts

vim.api.nvim_create_user_command("VectorCode", function(args)
  if args.fargs[1] == "register" then
    local bufnr = vim.api.nvim_get_current_buf()
    require("vectorcode.cacher").register_buffer(bufnr, { run_on_register = true })
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
