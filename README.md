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

## Metadata mapping

The resolvers only fetch the metadata of an identifier; mapping it to record
metadata belongs to the model. Each resolver reads its mapper from
`RELATED_RESOURCES_<PROVIDER>_MAPPER` - a callable (or its import string)
`(metadata) -> (record metadata, list[ResolverProblem])`:

| Resolver | Config | The mapper gets |
|---|---|---|
| DataCite | `RELATED_RESOURCES_DATACITE_MAPPER` | the DataCite attributes object (`data.attributes` of the REST API) |
| Crossref | `RELATED_RESOURCES_CROSSREF_MAPPER` | the Crossref work (`message` of the REST API) |
| Handle | `RELATED_RESOURCES_HANDLE_MAPPER` | the `<head>` of the landing page (an lxml `HtmlElement`) |

ccmm-invenio sets all three to its CCMM mappings. Without a mapper, resolving an
identifier of that resolver fails with a `RuntimeError` naming the variable - set it,
or remove the resolver from `RELATED_RESOURCES_PERSISTENT_IDENTIFIER_RESOLVERS`.

To write a mapper, subclass `oarepo_related_resources.resolvers.ResolverMapping`: set
`provider`, fill `processed_metadata` in `resolve_metadata` and report what can not be
mapped with `_add_problem`. Decorate the partial `resolve_*` methods with
`oarepo_related_resources.resolvers.utils.handle_errors`, so that one failing value does
not lose the whole record. The same module has model-independent helpers for the
mapping (vocabulary lookups, `split_personal_name`, `normalize_date`, `validate_edtf`,
`escape_lucene`, …); building the record shape (e.g. the RDM `person_or_org`) is the
mapper's job. For example:

```python
from oarepo_related_resources.resolvers import ResolverMapping
from oarepo_related_resources.resolvers.utils import handle_errors


class CrossrefMapping(ResolverMapping):
    provider = "Crossref"

    def resolve_metadata(self):
        self.resolve_title()
        return self.processed_metadata, self.problems

    @handle_errors(alert_user=True)
    def resolve_title(self):
        self.processed_metadata["title"] = self.metadata["title"][0]


def map_crossref(work):  # RELATED_RESOURCES_CROSSREF_MAPPER = "my_model.mappings:map_crossref"
    return CrossrefMapping(work).resolve_metadata()
```

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

