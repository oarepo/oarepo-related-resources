#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Tests for resolver utilities."""

from unittest.mock import Mock

from oarepo_related_resources.resolvers import utils
from oarepo_related_resources.resolvers.base import ResolverProblemLevel


@utils.handle_errors(alert_user=True)
def failing_resolver_method(self):
    raise ValueError("broken metadata")


def test_handle_errors(app):
    resolver = Mock()

    assert failing_resolver_method(resolver) is None
    assert str(resolver._add_problem.call_args.args[0]) == "Unexpected error while parsing the metadata."
    assert resolver._add_problem.call_args.kwargs["level"] == ResolverProblemLevel.ERROR
    assert str(resolver._add_problem.call_args.kwargs["exc"]) == "broken metadata"


def test_search_vocabulary_by_prop(app, monkeypatch):
    hits = [{"id": "dataset"}, {"id": "data"}]
    vocabulary_service = Mock()
    vocabulary_service.search.return_value.to_dict.return_value = {"hits": {"hits": hits}}
    monkeypatch.setattr(utils, "vocabulary_service", vocabulary_service)
    monkeypatch.setattr(utils.VocabularyType, "query", Mock())

    assert utils.search_vocabulary_by_prop("resourcetypes", "Data+Set") == hits


def test_lookup_vocabulary_by_prop(app, monkeypatch):
    monkeypatch.setattr(
        utils,
        "search_vocabulary_by_prop",
        Mock(
            side_effect=[
                [{"id": "one"}],
                [{"id": "first"}, {"id": "second"}],
                [{"id": "longer"}, {"id": "id"}],
            ]
        ),
    )

    assert utils.lookup_vocabulary_by_prop("types", "one") == "one"
    assert utils.lookup_vocabulary_by_prop("types", "ambiguous") is None
    assert utils.lookup_vocabulary_by_prop_handle_multiple("types", "multiple") == "id"


def test_resolve_language(app, monkeypatch):
    monkeypatch.setattr(utils, "vocabulary_entry_exists", Mock(side_effect=[True, False]))

    assert utils.resolve_language(None) is None
    assert utils.resolve_language("en") == "eng"
    assert utils.resolve_language("de") is None


def test_resolve_invalid_language(app, monkeypatch):
    monkeypatch.setattr(utils.langcodes.Language, "get", Mock(side_effect=ValueError))

    assert utils.resolve_language("invalid") is None
