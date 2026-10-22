# Legal documents

The public `/privacy` and `/terms` pages render `privacy.md` and `terms.md` from this folder (Markdown: headings,
paragraphs, lists, bold, links). Until a file exists the page says the document is being finalised.

When a document changes, also raise its version in the backend settings (`TERMS_VERSION` or `PRIVACY_VERSION`; `GET /me/consent` returns the current
`terms_version` and `privacy_version`), so signed-in people are asked to agree again.
