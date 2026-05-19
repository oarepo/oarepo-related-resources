#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from oarepo_related_resources.resolvers import CrossrefResolver, DataciteResolver, HandleResolver


def test_datacite_resolver_builds_expected_upstream_url(app, zenodo_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = DataciteResolver()
    assert (
        resolver._create_fetch_url(zenodo_doi)  # noqa SLF001
        == "https://api.datacite.org/dois/10.5281/zenodo.19032692"
    )


def test_crossref_resolver_builds_expected_upstream_url(app, crossref_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = CrossrefResolver()
    assert (
        resolver._create_fetch_url(crossref_doi)  # noqa SLF001
        == "https://api.crossref.org/works/doi/10.1575/1912/1099"
    )


def test_handle_resolver_builds_expected_upstream_url(app, handle):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = HandleResolver()
    assert (
        resolver._create_fetch_url(handle)  # noqa SLF001
        == "https://hdl.handle.net/11234/1-6144"
    )
