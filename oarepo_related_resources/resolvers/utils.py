#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources resolvers utils."""

from __future__ import annotations

import re
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

import langcodes
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_i18n import lazy_gettext as _
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.models import VocabularyType
from marshmallow import ValidationError
from marshmallow_utils.fields import EDTFDateString
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from collections.abc import Callable

    from oarepo_related_resources.resolvers import MetadataResolver


def escape_lucene(s: str) -> str:
    """Escape special characters in a string for safe use in Lucene queries."""
    return re.sub(r'([+\-!(){}\[\]^"~*?:\\/])', r"\\\1", s)


def split_personal_name(name: str) -> tuple[str, str]:
    """Split a "Family, Given" string into (family, given). Empty given if no comma."""
    if "," in name:
        family, given = (part.strip() for part in name.split(",", 1))
        return family, given
    return name.strip(), ""


def build_person_or_org(  # noqa PLR0913
    *,
    name: str | None,
    type_: str = "personal",
    given: str | None = None,
    family: str | None = None,
    identifiers: list | None = None,
    affiliations: list | None = None,
) -> dict:
    """Build an RDM creator/contributor entry.

    Returns ``{"person_or_org": {...}}`` with optional ``"affiliations"``. Optional
    fields are omitted when falsy, matching Invenio RDM's tolerated shape.
    """
    person: dict = {"name": name, "type": type_}
    if given:
        person["given_name"] = given
    if family:
        person["family_name"] = family
    if identifiers:
        person["identifiers"] = identifiers
    entry: dict = {"person_or_org": person}
    if affiliations:
        entry["affiliations"] = affiliations
    return entry


def resolve_language(language: str | None) -> str | None:
    """Map a 2/3-letter language code to its alpha-3 form, validated against the languages vocabulary."""
    if not language:
        return None
    try:
        longer_code = langcodes.Language.get(language.lower()).to_alpha3()
    except Exception:
        current_app.logger.exception("Failed to map language code '%s' to alpha-3.", language)
        return None
    if not vocabulary_entry_exists("languages", longer_code):
        return None
    return str(longer_code)


def validate_edtf(date: str) -> Exception | None:
    """Return None if `date` parses as EDTF, otherwise the ValidationError raised by deserialization."""
    try:
        EDTFDateString().deserialize(date)
    except ValidationError as e:
        return e  # type: ignore[no-any-return]
    return None


def vocabulary_entry_exists(vocabulary_id: str, key: str) -> bool:
    """Return True if `key` resolves to an entry in `vocabulary_id`.

    The vocabulary read result is discarded — only the presence/absence of
    the entry matters. Any exception is logged and yields False.
    """
    try:
        vocabulary_service.read(system_identity, (vocabulary_id, key))  # type: ignore[arg-type]
    except Exception:
        current_app.logger.exception(
            "Record '%s' was not found in the '%s' vocabulary.",
            key,
            vocabulary_id,
        )
        return False
    return True


def search_vocabulary_by_prop(
    vocabulary_id: str,
    value: str,
    *,
    prop: str = "datacite",
) -> list[dict[str, Any]] | None:
    """Return vocabulary search hits matching ``props.<prop>:"value"``."""
    escaped = escape_lucene(value)
    try:
        VocabularyType.query.filter_by(id=vocabulary_id).one()  # type: ignore[reportAttributeAccessIssue]
    except NoResultFound:
        current_app.logger.exception(
            "Error searching for '%s' in vocabulary of type '%s', the vocabulary type not resolvable.",
            value,
            vocabulary_id,
        )
        return None
    voc = vocabulary_service.search(
        system_identity,
        type=vocabulary_id,
        params={"q": f'props.{prop}:"{escaped}"'},
    )

    return voc.to_dict()["hits"]["hits"]  # type: ignore[no-any-return]


def lookup_vocabulary_by_prop(
    vocabulary_id: str,
    value: str,
    *,
    prop: str = "datacite",
) -> str | None:
    """Look up a single vocabulary entry by searching `props.<prop>` for `value`.

    Returns the matching entry's id when exactly one hit is found. Returns
    None on zero or multiple hits, or on any underlying exception — both
    failure modes are logged. Callers should treat None as "skip this item".
    """
    hits = search_vocabulary_by_prop(vocabulary_id, value, prop=prop)
    if not hits:
        current_app.logger.exception(
            "Record '%s' was not found in the '%s' vocabulary.",
            value,
            vocabulary_id,
        )
        return None
    if len(hits) > 1:
        current_app.logger.exception(
            "No unambiguous value could be resolved for vocabulary value %s.",
            value,
        )
        return None
    return cast("str", hits[0]["id"])


def lookup_vocabulary_by_prop_handle_multiple(
    vocabulary_id: str,
    value: str,
    *,
    prop: str = "datacite",
    handle_multiple_fn: Callable[[list[dict[str, Any]]], str] = lambda hits: cast("str", hits[0]["id"]),
) -> str | None:
    """Look up a single vocabulary entry by searching `props.<prop>` for `value`.

    Returns the matching entry's id when exactly one hit is found. Returns
    None on zero. handle_multiple_fn parameter specifies what happens when more than one entry is found.
    The first one is returned by default.
    """
    hits = search_vocabulary_by_prop(vocabulary_id, value, prop=prop)
    if not hits:
        current_app.logger.exception(
            "Record '%s' was not found in the '%s' vocabulary.",
            value,
            vocabulary_id,
        )
        return None
    if len(hits) > 1:
        return handle_multiple_fn(hits)
    return cast("str", hits[0]["id"])


def handle_errors(alert_user: bool = False) -> Any:
    """Decorate a resolver method to swallow and log any raised exception.

    On exception the wrapped function returns ``None`` instead of propagating.
    When ``alert_user`` is True, a ResolverProblem is also appended to the
    resolver's ``problems`` list so it surfaces in the resolver output.
    """

    def decorator(func: Any) -> Any:
        """Wrap the given function with error handling logic."""

        @wraps(func)
        def inner(self: MetadataResolver, *args: Any, **kwargs: Any) -> Any | None:
            """Execute the wrapped function with safe error handling."""
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if alert_user:
                    from .base import ResolverProblemLevel

                    self._add_problem(
                        _("Unexpected error while parsing the metadata."),
                        level=ResolverProblemLevel.ERROR,
                        exc=e,
                    )
                current_app.logger.exception("Function '%s' failed with error: '%s'.", func.__name__, e)  # noqa: TRY401
            return None  # discard

        return inner

    return decorator
