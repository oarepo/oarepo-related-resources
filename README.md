# oarepo-related-resources

A library for importing metadata from persistent identifiers (DOI and Handle)
into Invenio/OARepo applications.

## What it does

- supports DataCite, Crossref, and Handle resolvers,
- fetches and normalizes metadata such as titles, creators, dates, descriptions,
  and resource types,
- reports non-fatal import problems together with the imported metadata,
- provides an ORCID importer and ROR affiliation/funder resolution.

## Registering the extension

Register the extension in the application's `pyproject.toml`:

```toml
[project.entry-points."invenio_base.api_apps"]
related_resources_import_extension = "oarepo_related_resources.ext:RelatedResourcesImportExtension"

[project.entry-points."invenio_base.apps"]
related_resources_import_extension = "oarepo_related_resources.ext:RelatedResourcesImportExtension"
```

The extension registers the `/related-records` resource and the
`current_orcid_importer` proxy.

## HTTP API

The resource accepts an authenticated `POST` request at `/related-records`:

```json
{
  "identifier": "https://doi.org/10.5281/zenodo.19032692"
}
```

The identifier may also be supplied without its DOI or Handle URL prefix. A
successful response contains normalized metadata and any non-fatal problems:

```json
{
  "metadata": {
    "title": "...",
    "creators": [],
    "publication_date": "...",
    "resource_type": {"id": "..."}
  },
  "import_errors": [],
  "validation_errors": []
}
```

`import_errors` contains resolver problems. `validation_errors` contains errors
from loading the resolved metadata into the configured record schema.

Typical HTTP errors are:

- `403` — the caller is not allowed to import related resources;
- `404` — unsupported or non-existent identifier;
- the upstream response status — an upstream resolver request failed;
- `500` — an unexpected processing error.

## Resolver problems

Resolver methods return metadata together with a list of `ResolverProblem`
objects. Each problem contains:

```json
{
  "resolver": "DataCite",
  "message": "...",
  "level": "info",
  "original_exception": null
}
```

The available levels are `info`, `warning`, and `error`. These problems are
non-fatal unless the resolver itself cannot produce a response. `error` level
problems are also sent to the application logger; applications configured with
Sentry/GlitchTip logging can report them there.

## ORCID importer

Use the extension proxy after the application has been initialized:

```python
from oarepo_related_resources.proxies import current_orcid_importer

person = current_orcid_importer.resolve(
    "0000-0001-2345-6789",
    vocabulary="names",
)
```

The importer reads the configured ORCID public dump and can resolve ROR
identifiers for affiliations and funders.

