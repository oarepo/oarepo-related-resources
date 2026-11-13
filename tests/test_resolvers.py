# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

from __future__ import annotations

from unittest.mock import Mock

import pytest

from oarepo_related_resources.resolvers import (
    CrossrefResolver,
    DataciteResolver,
    HandleResolver,
    ResolverMapping,
)
from oarepo_related_resources.resolvers.base import ResolverProblem, ResolverProblemLevel
from oarepo_related_resources.resolvers.utils import handle_errors


class TitleMapping(ResolverMapping):
    """A mapping with one working and one failing step."""

    provider = "Test"

    def resolve_metadata(self):
        """Run both steps."""
        self.resolve_title()
        self.resolve_broken()
        return self.processed_metadata, self.problems

    @handle_errors()
    def resolve_title(self):
        """Map the title, report a missing year."""
        self.processed_metadata["title"] = self.metadata["title"]
        if not self.metadata.get("year"):
            self._add_problem("no year")

    @handle_errors(alert_user=True)
    def resolve_broken(self):
        """Fail."""
        raise ValueError("broken")


def test_resolver_mapping(app):
    """A failing step is skipped (and reported with alert_user), the problems carry the provider."""
    metadata, problems = TitleMapping({"title": "A title"}).resolve_metadata()

    assert metadata == {"title": "A title"}
    assert [(p.resolver, p.level, p.message) for p in problems] == [
        ("Test", ResolverProblemLevel.WARNING, "no year"),
        ("Test", ResolverProblemLevel.ERROR, "Unexpected error while parsing the metadata."),
    ]
    assert isinstance(problems[1].original_exception, ValueError)


def test_resolver_mapping_instances_do_not_share_state(app):
    first, second = TitleMapping({"title": "1"}), TitleMapping({"title": "2"})
    first.resolve_metadata()
    assert second.problems == []
    assert second.processed_metadata == {}


RESOLVERS = [
    (DataciteResolver, "RELATED_RESOURCES_DATACITE_MAPPER"),
    (CrossrefResolver, "RELATED_RESOURCES_CROSSREF_MAPPER"),
    (HandleResolver, "RELATED_RESOURCES_HANDLE_MAPPER"),
]


def test_datacite_resolver_builds_expected_upstream_url(app, zenodo_doi):
    """`DATACITE_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = DataciteResolver()
    assert (
        resolver._create_fetch_url(zenodo_doi)
        == "https://api.datacite.org/dois/10.5281/zenodo.19032692?affiliation=true"
    )


def test_doi_lowercase(app):
    assert DataciteResolver().normalize_identifier("https://doi.org/10.1234/UPPERCASE") == "10.1234/uppercase"


def test_crossref_resolver_builds_expected_upstream_url(app, crossref_doi):
    """`CROSSREF_URL` + normalized DOI suffix produces the upstream API URL."""
    resolver = CrossrefResolver()
    assert resolver._create_fetch_url(crossref_doi) == "https://api.crossref.org/works/doi/10.1575/1912/1099"


def test_handle_resolver_builds_expected_upstream_url(app, handle):
    """`HANDLE_URL` + normalized handle produces the upstream URL."""
    resolver = HandleResolver()
    assert resolver._create_fetch_url(handle) == "https://hdl.handle.net/11234/1-6144"


@pytest.mark.parametrize(("resolver_cls", "config_key"), RESOLVERS)
def test_resolver_mapper_config_key(app, resolver_cls, config_key):
    assert resolver_cls().mapper_config_key == config_key


@pytest.mark.parametrize(("resolver_cls", "config_key"), RESOLVERS)
def test_resolver_uses_configured_mapper(app, monkeypatch, resolver_cls, config_key):
    """The resolver's metadata is mapped by its RELATED_RESOURCES_<PROVIDER>_MAPPER (an object or import string)."""
    problem = ResolverProblem(resolver=resolver_cls.provider, message="dropped", level=ResolverProblemLevel.INFO)
    mapper = Mock(return_value=({"title": "Mapped"}, [problem]))
    monkeypatch.setitem(app.config, config_key, mapper)
    resolver = resolver_cls()
    resolver.metadata = {"raw": "metadata"}

    assert resolver.resolve_metadata() == ({"title": "Mapped"}, [problem])
    mapper.assert_called_once_with({"raw": "metadata"})


@pytest.mark.parametrize(("resolver_cls", "config_key"), RESOLVERS)
def test_resolver_without_mapper(app, monkeypatch, resolver_cls, config_key):
    """Without a mapping the resolver fails with a message naming the config."""
    monkeypatch.delitem(app.config, config_key, raising=False)
    resolver = resolver_cls()
    resolver.metadata = {}

    with pytest.raises(RuntimeError, match=config_key):
        resolver.resolve_metadata()
