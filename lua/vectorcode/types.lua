---@class VectorCode.Result
---@field path string
---@field document string

---@class VectorCode.Cache
---@field enabled boolean
---@field jobs table<string, boolean>
---@field last_run integer?
---@field options VectorCode.RegisterOpts
---@field retrieval VectorCode.Result[]?

---@class VectorCode.QueryOpts
---@field exclude_this boolean
---@field n_query integer
---@field notify boolean
---@field timeout_ms number

---@class VectorCode.Opts : VectorCode.QueryOpts
---@field async_opts VectorCode.RegisterOpts

---@class VectorCode.RegisterOpts: VectorCode.QueryOpts
---@field debounce integer
---@field events string|string[]
---@field single_job boolean
---@field query_cb VectorCode.QueryCallback
---@field run_on_register boolean
