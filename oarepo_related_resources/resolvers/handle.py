#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources Handle resolver."""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING

import dateutil  # type: ignore[import-untyped]
import langcodes
from dateutil.parser import ParserError  # type: ignore[import-untyped]
from flask import current_app
from idutils.normalizers import normalize_handle
from idutils.validators import is_handle
from invenio_access.permissions import system_identity
from invenio_i18n import lazy_gettext as _
from invenio_vocabularies.proxies import current_service as vocabulary_service
from lxml import html
from marshmallow import ValidationError
from marshmallow_utils.fields import EDTFDateString

from ..resolvers import MetadataResolver
from .base import (
    CREATORS_PLACEHOLDER,
    PUBLICATION_DATE_PLACEHOLDER,
    RESOURCE_TYPE_PLACEHOLDER,
    TITLE_PLACEHOLDER,
    ResolverProblem,
    ResolverProblemLevel,
    get_invalid_publication_date_message,
    get_validation_failed_on_date_format_message,
)
from .utils import handle_errors

if TYPE_CHECKING:
    from lxml.etree import _Element
MIN_TITLE_LENGTH = 3
MIN_YEAR = 1900
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_GONE = 410


def parse_date(date: str) -> tuple[str, list[str]]:
    """Parse and normalize a date string."""
    error_messages = []

    # 0000 is a special case happening a lot in LINDAT data that passes EDTF schema validation
    if re.match(r"^\d{4}$", date) and not (
        int(date) > MIN_YEAR and int(date) <= datetime.datetime.now(datetime.UTC).year
    ):
        return PUBLICATION_DATE_PLACEHOLDER, [get_invalid_publication_date_message(date)]
    try:
        parsed_date = EDTFDateString().deserialize(date)
    except ValidationError:
        try:
            parsed_date = dateutil.parser.parse(date, fuzzy=True)
            parsed_date = datetime.datetime.strftime(parsed_date, "%Y-%m-%d")
            error_messages.append(get_validation_failed_on_date_format_message(date))
        except ParserError:
            error_messages.append(get_invalid_publication_date_message(date))
            parsed_date = PUBLICATION_DATE_PLACEHOLDER
    return str(parsed_date), error_messages


class HandleResolver(MetadataResolver):
    """Resolver for Handle persistent identifiers."""

    name = "Handle"

    def resolve_metadata(self, metadata_tree: _Element) -> tuple[dict, list[ResolverProblem]]:
        """Extract metadata fields from the parsed HTML tree."""
        problem_list: list[ResolverProblem] = []
        metadata = {}
        metadata["title"] = self.resolve_main_title(tree=metadata_tree, problems=problem_list)
        metadata["creators"] = self.resolve_creators(tree=metadata_tree, problems=problem_list)
        metadata["publication_date"] = self.resolve_publication_date(tree=metadata_tree, problems=problem_list)
        # there are dataset related tags, dataset_creator, dataset_license, dataset_keyword ..
        # but they are used also on things that aren't datasets
        metadata["resource_type"] = {"id": RESOURCE_TYPE_PLACEHOLDER}

        additional_desc = self.resolve_additional_description(tree=metadata_tree, problems=problem_list)
        if len(additional_desc) > 0:
            metadata["additional_descriptions"] = additional_desc

        return metadata, problem_list

    def normalize(self, identifier: str) -> str:
        """Normalize the identifier by lowercasing it for case-insensitive Handle comparison."""
        return super().normalize(identifier).lower()

    def generate_id(self, identifier: str) -> str:
        """Generate an internal identifier from a Handle URL."""
        pattern = r"https?://hdl.handle.net/(.+)"
        m = re.match(pattern, identifier)
        if m:
            return f"handle/{m.group(1)}"
        raise ValueError(f"Could not generate pid from url: {identifier}")

    def exists(self, identifier: str) -> bool:
        """Check if the Handle exists by performing an HTTP request to the Handle registry."""
        handle_url = current_app.config.get("HANDLE_URL")
        handle = normalize_handle(identifier)
        url = f"{handle_url}/{handle}"
        response = self.session.get(url=url, timeout=self.resolve_timeout, allow_redirects=False)
        return bool(HTTP_OK <= response.status_code < HTTP_BAD_REQUEST)

    def can_resolve(self, identifier: str) -> bool:
        """Determine whether the given URL is a valid and supported Handle identifier."""
        persistent_url = self.normalize(identifier)
        return bool(is_handle(persistent_url)) and "https://hdl.handle.net" in persistent_url

    def resolve(self, identifier: str) -> tuple[dict | None, list[ResolverProblem]]:
        """Resolve metadata for a Handle URL by fetching and parsing its HTML representation."""
        handle = normalize_handle(identifier)
        handle_url = current_app.config.get("HANDLE_URL")

        response = self.session.get(  # redirect is hardcoded at 3
            url=f"{handle_url}/{handle}", timeout=self.resolve_timeout
        )

        if response.status_code != HTTP_OK:
            if response.status_code == HTTP_NOT_FOUND:
                return {}, [
                    ResolverProblem(
                        resolver=self.name,
                        message=str(
                            _(
                                "The identifier looks like a Handle, but \
                        it was not found in the Handle registry."
                            )
                        ),
                        level=ResolverProblemLevel.ERROR,
                    )
                ]
            current_app.logger.error(
                "Unexpected error while resolving the Handle. Response code: %s, content: %s",
                response.status_code,
                response.content,
            )
            return {}, [
                ResolverProblem(
                    resolver=self.name,
                    message=str(
                        _(
                            "Unexpected error while resolving the Handle. Please fill the metadata manually.",
                        )
                    ),
                    level=ResolverProblemLevel.ERROR,
                )
            ]

        tree = html.fromstring(response.content)
        tree = tree.xpath("/html/head")[0]

        return self.resolve_metadata(metadata_tree=tree)

    @handle_errors(error_placeholder=TITLE_PLACEHOLDER, alert_user=True)
    def resolve_main_title(self, *, tree: _Element, problems: list) -> str:
        """Resolve title from handle."""
        titles = tree.xpath('//meta[@name="citation_title"]/@content') or tree.xpath('//meta[@name="title"]/@content')
        if titles:
            return str(titles[0])
        problems.append(
            ResolverProblem(
                resolver=self.name,
                message=str(_("Missing title.")),
                level=ResolverProblemLevel.WARNING,
            )
        )
        return TITLE_PLACEHOLDER

    @handle_errors(error_placeholder=CREATORS_PLACEHOLDER, alert_user=True)
    def resolve_creators(self, *, tree: _Element, problems: list) -> list:
        """Resolve creators from handle."""
        creators = tree.xpath('//meta[@name="citation_author"]/@content')
        if not creators:
            problems.append(
                ResolverProblem(
                    resolver=self.name,
                    message=str(_("Missing creators.")),
                    level=ResolverProblemLevel.WARNING,
                )
            )
            return CREATORS_PLACEHOLDER
        creator_list = []

        for creator in creators:
            creator_obj = {}

            creator_type = "personal" if "," in creator else "organizational"  # best guess from looking at LINDAT data
            creator_obj["name"] = creator
            creator_obj["type"] = creator_type

            if creator_type == "personal":
                splt = [part.strip() for part in creator.split(",", 1)]
                creator_obj["given_name"] = splt[1]
                creator_obj["family_name"] = splt[0]

            creator_list.append({"person_or_org": creator_obj})

        return creator_list

    @handle_errors(PUBLICATION_DATE_PLACEHOLDER, alert_user=True)
    def resolve_publication_date(self, *, tree: _Element, problems: list) -> str:
        """Resolve publication date from handle."""
        dates = (
            tree.xpath('//meta[@name="citation_publication_date"]/@content')
            or tree.xpath('//meta[@name="publication_date"]/@content')
            or tree.xpath('//meta[@name="citation_date"]/@content')
        )

        if not dates:
            problems.append(
                ResolverProblem(
                    resolver=self.name,
                    level=ResolverProblemLevel.WARNING,
                    message=str(_("Publication date missing.")),
                )
            )
            return PUBLICATION_DATE_PLACEHOLDER

        date = dates[0]
        parsed_date, error_messages = parse_date(date)
        problems.extend(
            ResolverProblem(
                resolver=self.name,
                level=ResolverProblemLevel.WARNING,
                message=em,
            )
            for em in error_messages
        )
        return parsed_date

    @handle_errors()
    def resolve_additional_description(self, *, tree: _Element, problems: list) -> list:
        """Resolve additional description from handle."""
        _ = problems
        descriptions = tree.xpath('//meta[@name="DCTERMS.abstract"]')
        des_list = []
        for d in descriptions:
            description = d.get("content")

            if description:
                description_obj = {}
                if len(description) < MIN_TITLE_LENGTH:
                    continue
                d_lang = d.get("xml:lang")
                lang = self.resolve_language(language=d_lang)
                if lang:
                    description_obj["lang"] = {"id": lang}
                description_obj["type"] = {"id": "abstract"}
                description_obj["description"] = description
                des_list.append(description_obj)

        return des_list

    # TODO: copy paste from datacite
    @handle_errors()
    def resolve_language(self, language: str | None) -> str | None:
        """Resolve language vocabulary."""
        longer_code = ""
        if language:
            try:
                longer_code = langcodes.Language.get(language.lower()).to_alpha3()
                vocabulary_service.read(system_identity, ("languages", longer_code))  # type: ignore[arg-type]

            except Exception as e:
                _ = e
                current_app.logger.exception(
                    "Record '%s' was not found in the '%s' vocabulary.",
                    longer_code,
                    "languages",
                )
            else:
                return str(longer_code)

        return None
