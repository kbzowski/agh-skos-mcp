# agh-skos-mcp

MCP server for [SkOs](https://skos.agh.edu.pl) — the AGH University staff directory.
No API key, no login.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `search_people` | `nazwisko`, `imie`, `email`, `pokoj`, `telefon` (prefix, case-insensitive) · `tytul`, `id_status`, `grupa`, `stanowisko`, `funkcja`, `jednostka`, `pawilon`, `cialo` (id or Polish label) · `limit` | `total`, `results[]` (name, title, url, units), `person` — full profile, set only when exactly one person matched |
| `get_person` | `person` — slug or url, e.g. `krzysztof-bzowski-7674` | id, name, title, emails, phones, www, workplaces (unit, job, group, function, room), collegial bodies |
| `list_filter_options` | `field`, `contains` | `[{value, label}]` |

An ambiguous label raises an error listing the candidates. A query with no filters is rejected.

## Add to Claude Code

Requires [uv](https://docs.astral.sh/uv/).

`.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "agh-skos": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/kbzowski/agh-skos-mcp", "agh-skos-mcp"]
    }
  }
}
```

Or via CLI:

```bash
claude mcp add agh-skos --scope user -- uvx --from git+https://github.com/kbzowski/agh-skos-mcp agh-skos-mcp
```

Check with `claude mcp list` or `/mcp`.

## Development

```bash
git clone https://github.com/kbzowski/agh-skos-mcp && cd agh-skos-mcp
uv sync

uv run ruff check . && uv run ruff format .
uv run mypy
uv run pytest              # offline
uv run pytest -m network   # against the live directory
```

`uvx` caches its build. To run your working copy:

```bash
claude mcp add agh-skos --scope user -- uv run --directory /path/to/agh-skos-mcp agh-skos-mcp
```

## Implementation notes

- Data comes from the `__NEXT_DATA__` JSON embedded in each rendered page, not from HTML scraping.
- Filter dictionaries come from the site's `/a/select?id=…` endpoint.
- E-mails are stored obfuscated (reversed `<a>` tag, `#` for `@`) and decoded on the way out.
- A search matching exactly one person redirects `/search/` → profile page; `search_people` follows it and returns the full record in `person`.

## License

MIT
