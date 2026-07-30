# agh-skos-mcp

MCP server for [SkOs](https://skos.agh.edu.pl) — the AGH University staff directory.
Lets an agent find people by name, unit, position, room, phone or collegial body, and
read their contact data.

## Tools

| Tool | What it does |
|---|---|
| `search_people` | Advanced search. Text filters (`nazwisko`, `imie`, `email`, `pokoj`, `telefon`) are case-insensitive prefix matches. Dictionary filters (`tytul`, `id_status`, `grupa`, `stanowisko`, `funkcja`, `jednostka`, `pawilon`, `cialo`) take a numeric id or a Polish label. When exactly one person matches, the full profile comes back in `person`. |
| `get_person` | Full profile by slug or url: units, position, group, function, room, phones, e-mail, www, collegial bodies. |
| `list_filter_options` | Allowed values of a dictionary filter, optionally narrowed by substring. |

No API key, no login — the server reads the same public pages the site serves to a browser.

## Requirements

[uv](https://docs.astral.sh/uv/). Nothing else; `uv` fetches Python and the dependencies.

```bash
git clone https://github.com/kbzowski/agh-skos-mcp
cd agh-skos-mcp
uv sync
```

## Adding to Claude Code

### Option 1 — `.mcp.json` (shared with the project)

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "agh-skos": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/agh-skos-mcp", "agh-skos-mcp"]
    }
  }
}
```

Claude Code picks it up on the next start and asks once whether to trust the server.
Commit the file to share the server with your team.

### Option 2 — CLI

```bash
# just for you, in every project
claude mcp add agh-skos --scope user -- uv run --directory /path/to/agh-skos-mcp agh-skos-mcp

# or write the .mcp.json above for the whole project
claude mcp add agh-skos --scope project -- uv run --directory /path/to/agh-skos-mcp agh-skos-mcp
```

Verify with `claude mcp list`, or `/mcp` inside a session.

### Without uv

`uv run` is only there to provide the one dependency (the `mcp` SDK) and keep it in sync with
the lockfile. If you would rather manage the environment yourself, install the package and
point Claude Code at the resulting executable:

```bash
python -m venv .venv && .venv/bin/pip install -e .   # .venv\Scripts\pip on Windows
claude mcp add agh-skos --scope user -- /path/to/agh-skos-mcp/.venv/bin/agh-skos-mcp
```

## Development

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # strict type check
uv run pytest                # unit tests, offline
uv run pytest -m network     # contract tests against the live directory
```

`ruff`, `mypy` and the offline tests also run on every push (see `.github/workflows/ci.yml`).

## How it works

SkOs is a Next.js front-end. The advanced search form is a plain `GET /search/`, and each
rendered page embeds its data as JSON in `__NEXT_DATA__` — that is what this server parses,
so there is no HTML scraping. Filter dictionaries come from the site's own `/a/select?id=…`
endpoint. E-mail addresses are stored obfuscated (a reversed `<a>` tag with `#` for `@`) and
are decoded on the way out.

One quirk worth knowing: when a query matches exactly one person, SkOs redirects from
`/search/` straight to the profile page. `search_people` detects that and returns the full
record instead of an empty result list.

## License

MIT
