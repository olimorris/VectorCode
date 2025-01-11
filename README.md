# VectorCode

VectorCode is a code repository indexing tool. It helps you write better prompt
for your coding LLMs by indexing and providing information about the code
repository you're working on. This repository also contains the corresponding
neovim plugin because that's what I used to write this tool.

> [!NOTE]
> This project is in beta quality and only implements very basic retrieval and
> embedding functionalities. There's plenty of rooms for improvements and any
> help is welcomed.

> [!NOTE]
> [Chromadb](https://www.trychroma.com/), the vector database backend behind
> this project, supports multiple embedding engines. I developed this tool using
> Ollama but if you encounter any issues with a different embedding function,
> please open an issue (or even better, a pull request :D).

<!-- mtoc-start -->

* [Prerequisites](#prerequisites)
* [Installation](#installation)
  * [NeoVim users: ](#neovim-users-)
* [Configuration](#configuration)
  * [CLI tool](#cli-tool)
* [Usage ](#usage-)
  * [CLI tool](#cli-tool-1)
    * [Vectorising documents](#vectorising-documents)
    * [Querying from a collection](#querying-from-a-collection)
    * [Listing all collections ](#listing-all-collections-)
    * [Removing a collection ](#removing-a-collection-)
  * [NeoVim plugin](#neovim-plugin)
  * [For Developers](#for-developers)
    * [`vectorise`](#vectorise)
    * [`query`](#query)
    * [`ls`](#ls)
    * [`drop`](#drop)
* [TODOs](#todos)

<!-- mtoc-end -->

## Prerequisites


- A working instance of [Chromadb](https://www.trychroma.com/). A local docker
  image will suffice.
- An embedding tool supported by [Chromadb](https://www.trychroma.com/), which 
you can find out more from 
[here](https://docs.trychroma.com/docs/embeddings/embedding-functions) and 
[here](https://docs.trychroma.com/integrations/chroma-integrations)

## Installation


I recommend using [pipx](https://github.com/pypa/pipx). This will take care of
the depenencies of `vectorcode` and create a dedicated virtual environment
without messing up your system Python.

Run the following command:
```bash 
pipx install vectorcode
```

### NeoVim users: 

This repo doubles as a neovim plugin. Use your favourite plugin manager to
install.

For `lazy.nvim`: 
```lua
{
  "Davidyz/VectorCode",
  dependencies = { "nvim-lua/plenary.nvim" },
  opts = { n_query = 1 },
}
```

## Configuration

### CLI tool
This tool uses a json file to store the configuration. It's located at
`$HOME/.config/vectorcode/config.json`.

```json 
{
    "embedding_function": 'SomeEmbeddingFunction',
    "embedding_params": {
    }
    "host": "localhost",  
    "port": 8000,
}
```
- `embedding_function`: One of the embedding functions supported by [Chromadb](https://www.trychroma.com/) 
  (find more [here](https://docs.trychroma.com/docs/embeddings/embedding-functions) and 
  [here](https://docs.trychroma.com/integrations/chroma-integrations)). For
  example, Chromadb supports Ollama as `chromadb.utils.embedding_functions.OllamaEmbeddingFunction`,
  and the corresponding value for `embedding_function` would be `OllamaEmbeddingFunction`.
- `embedding_params`: Whatever initialisation parameters your embedding function
  takes. For `OllamaEmbeddingFunction`, if you set `embedding_params` to:
  ```json
  {
    "url": "http://127.0.0.1:11434/api/embeddings",
    "model_name": "nomic-embed-text"
  }
  ```
  Then the embedding function object will be initialised as
  `OllamaEmbeddingFunction(url="http://127.0.0.1:11434/api/embeddings",
  model_name="nomic-embed-text")`.
- `host` and `port`: Chromadb server host and port.

For the convenience of deployment, environment variables in the
configuration values will be automatically expanded so that you can override
thing at run time without modifying the json.

Also, some of the built-in embedding functions supported by Chromadb requires
external library (such as `openai`) that are not included in the dependency
list. This is what Chromadb did, so I did the same. If you installed
`vectorcode` via `pipx`, you can install extra libraries by running the
following command:
```bash 
pipx inject vectorcode openai
```
And `openai` will be added to the virtual environment of `vectorcode`.

## Usage 
### CLI tool
>This is an incomplete list of command-line options. You can always use
`vectorcode -h` to view the full list of arguments.

This tool creates a `collection` (just like tables in traditional databases) for each 
project. The collections are identified by project root, which, by default, is
the current working directory. You can override this by using the `--project_root
<path_to_your_project_root>` argument.

#### Vectorising documents
```bash
vectorcode vectorise src/*.py
```
"Orphaned documents" that has been removed in your filesystem but still "exists"
in the database will be automatically cleaned.

#### Querying from a collection
```bash 
vectorcode query "some query message"
```
It returns one query result by default. To increase the number of response, use
`-n`: 
```bash 
vectorcode query "some query message" -n 5
```

#### Listing all collections 
```bash 
vectorcode ls 
```

#### Removing a collection 

```bash 
vectorcode drop 
```

For `vectorise`, `query` and `ls`, adding `--pipe` or `-p` flag will convert the
output into a structured format. This is explained in detail [here](#for-developers).

### NeoVim plugin
> In this document I will be using [qwen2.5-coder](https://github.com/QwenLM/Qwen2.5-Coder) 
> as an example. Adjust your config when needed.

This is **NOT** a completion plugin, but a helper that facilitates prompting. It
provides APIs so that your completion engine (such as 
[cmp-ai](https://github.com/tzachar/cmp-ai)) can leverage the repository-level
context.

Using [cmp-ai](https://github.com/tzachar/cmp-ai) as an example, the
[configuration](https://github.com/tzachar/cmp-ai?tab=readme-ov-file#setup)
provides a `prompt` option, with which you can customize the prompt sent to the
LLM for each of the completion.

By consulting the [qwen2.5-coder documentation](https://github.com/QwenLM/Qwen2.5-Coder?tab=readme-ov-file#3-file-level-code-completion-fill-in-the-middle)
, we know that a trivial prompt can be constructed as the
following:
```lua 
prompt = function(lines_before, lines_after)
    return '<|fim_prefix|>' 
        .. lines_before 
        .. '<|fim_suffix|>' 
        .. lines_after 
        .. '<|fim_middle|>'
end
```

However, the information from such a context is limited to the document itself.
By utilising VectorCode and this plugin, you'll be able to construct contexts
that contain repository-level information:
```lua
prompt = function(lines_before, lines_after)
    local file_context = ""
    for _, source in
        -- Use the current document as the query
        -- You can adjust this to match your needs.
        pairs(require("vectorcode").query(lines_before .. " " .. lines_after))
    do
        file_context = file_context
            .. "<|file_sep|>"  
            .. source.path
            .. "\n"
            .. source.document
            .. "\n"
    end
    return file_context
        ..'<|fim_prefix|>' 
        .. lines_before 
        .. '<|fim_suffix|>' 
        .. lines_after 
        .. '<|fim_middle|>'
```
Note that, the use of `<|file_sep|>` is documented in 
[qwen2.5-coder documentation](https://github.com/QwenLM/Qwen2.5-Coder?tab=readme-ov-file#3-file-level-code-completion-fill-in-the-middle) 
and is likely to be model-specific. You may need to figure out the best prompt
structure for your own model.

The number of files returned by the `query` function call can be configured
either by the `setup` function, or passed as an argument to the `query` call
which overrides the `setup` setting for this call:
```lua 
require("vectorcode").query(some_query_message, {n_query=5})
```

> [!NOTE]
> The retrieval process will inevitably slow down the completion.

### For Developers

When the `--pipe` flag is set, the output of the CLI tool will be structured
into some sort of JSON string.

#### `vectorise`
The number of added, updated and removed entries will be printed.
```json
{
    "add": int,
    "update": int,
    "removed": int,
}
```
- `add`: number of added documents;
- `update`: number of updated (existing) documents;
- `removed`: number of removed documents due to original documents being
  deleted.

#### `query`
A JSON array of query results of the following format will be printed:
```json
{
    "path": str,
    "document": str,
}
```

- `path`: path to the file;
- `document`: content of the file.

#### `ls`
A JSON array of collection information of the following format will be printed:
```json 
{
    "project-root": str,
    "user": str,
    "hostname": str,
    "collection_name": str,
    "size": int,
}
```

- `project_root`: path to the project directory (your code repository);
- `user`: your *nix username, which are automatically added when vectorising to
  avoid collision;
- `hostname`: your *nix hostname. The purpose of this field is the same as the
  `user` field;
- `collection_name`: the unique identifier of the collection in the database.
  This is the first 63 characters of the sha256 hash of the absolute path of the
  project root.
- `size`: number of documents in the collection.
#### `drop`
The `drop` command doesn't offer a `--pipe` model output at the moment.

## TODOs
- [ ] NeoVim lua API with cache to skip the retrieval when a project has not
  been indexed;
- [ ] query by filepath;
- [ ] respect `.gitignore`;
- [ ] implement some sort of project-root anchors (such as `.git` or a custom
  `.vectorcode.json`) that enhances automatic project-root detection.
