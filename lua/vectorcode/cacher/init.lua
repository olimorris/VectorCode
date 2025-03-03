vim.deprecate(
  'require("vectorcode.cacher")',
  'require("vectorcode.config").get_cacher_backend()',
  "0.5.0",
  "VectorCode",
  true
)

return require("vectorcode.cacher.default")
