#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources Handle resolver."""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING, Any, override

import dateutil  # type: ignore[import-untyped]
from dateutil.parser import ParserError  # type: ignore[import-untyped]
from idutils.normalizers import normalize_handle
from idutils.validators import is_handle
from invenio_i18n import lazy_gettext as _
from lxml import html

from ..config import RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE
from .base import (
    MetadataResolver,
)
from .utils import (
    build_person_or_org,
    handle_errors,
    resolve_language,
    split_personal_name,
    validate_edtf,
)

if TYPE_CHECKING:
    from requests import Response

MIN_YEAR = 1900
HTTP_BAD_REQUEST = 400


class HandleResolver(MetadataResolver):
    """Resolver for Handle persistent identifiers."""

    provider = "Handle"

    lowercase = True
    exists_allow_redirects = False
    resolves_identifier_url_format = staticmethod(lambda url: bool(is_handle(url)) and "https://hdl.handle.net" in url)
    normalize_identifier = staticmethod(normalize_handle)

    not_found_message = _("The identifier looks like a Handle, but it was not found in the Handle registry.")
    unexpected_error_message = _("Unexpected error while resolving the Handle. Please fill the metadata manually.")

    fields_to_resolve = (
        "title",
        "creators",
        "publication_date",
        "resource_type",
        "additional_descriptions",
    )

    def _fetch_response_alive(self, status_code: int) -> bool:
        """Handle considers any 2xx/3xx response (incl. redirects) as live."""
        return 200 <= status_code < HTTP_BAD_REQUEST  # noqa PLR2004

    @override
    def get_metadata(self, response: Response) -> Any:
        tree = html.fromstring(response.content)
        return tree.xpath("/html/head")[0]

    @handle_errors(alert_user=True)
    def resolve_title(self) -> None:
        """Extract the main title from Handle HTML metadata."""
        titles = self.metadata.xpath('//meta[@name="citation_title"]/@content') or self.metadata.xpath(
            '//meta[@name="title"]/@content'
        )
        if titles:
            self.processed_metadata["title"] = titles[0]

    @handle_errors(alert_user=True)
    def resolve_creators(self) -> None:
        """Extract and map creator information from Handle HTML metadata."""
        creators = self.metadata.xpath('//meta[@name="citation_author"]/@content')
        creator_list = []
        for creator in creators:
            # best guess from looking at LINDAT data
            if "," in creator:
                family, given = split_personal_name(creator)
                creator_list.append(build_person_or_org(name=creator, family=family, given=given))
            else:
                creator_list.append(build_person_or_org(name=creator, type_="organizational"))

        if creator_list:
            self.processed_metadata["creators"] = creator_list

    @handle_errors(alert_user=True)
    def resolve_publication_date(self) -> None:
        """Extract and validate the publication date from Handle HTML metadata."""
        dates = (
            self.metadata.xpath('//meta[@name="citation_publication_date"]/@content')
            or self.metadata.xpath('//meta[@name="publication_date"]/@content')
            or self.metadata.xpath('//meta[@name="citation_date"]/@content')
        )
        if not dates:
            return

        parsed = self._parse_loose_date(dates[0])
        if parsed:
            self.processed_metadata["publication_date"] = parsed

    # TODO: by schema too? -> just set default value for load
    @handle_errors()
    def resolve_resource_type(self) -> None:
        """Set the resource type placeholder for Handle records."""
        # there are dataset related tags, dataset_creator, dataset_license, dataset_keyword ..
        # but they are used also on things that aren't datasets
        self.processed_metadata["resource_type"] = {"id": RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE}

    @handle_errors()
    def resolve_additional_descriptions(self) -> None:
        """Extract and map additional descriptions from Handle HTML metadata."""
        descriptions = self.metadata.xpath('//meta[@name="DCTERMS.abstract"]')
        des_list = []
        for d in descriptions:
            description = d.get("content")

            if description:
                description_obj = {}
                d_lang = d.get("xml:lang")
                lang = resolve_language(d_lang)
                if lang:
                    description_obj["lang"] = {"id": lang}
                description_obj["type"] = {"id": "abstract"}
                description_obj["description"] = description
                des_list.append(description_obj)

        if des_list:
            self.processed_metadata["additional_descriptions"] = des_list

    # TODO: perhaps move to schema
    def _parse_loose_date(self, date: str) -> str | None:
        """Parse a free-form date string, falling back to dateutil with a warning."""
        # 0000 is a special case happening a lot in LINDAT data that passes EDTF schema validation
        if re.match(r"^\d{4}$", date) and not (MIN_YEAR < int(date) <= datetime.datetime.now(datetime.UTC).year):
            self._add_problem(_("Invalid publication date format: %(date)s.", date=date))
            return None
        if validate_edtf(date) is None:
            return date
        try:
            parsed = dateutil.parser.parse(date, fuzzy=True)
        except ParserError:
            self._add_problem(_("Invalid publication date format: %(date)s.", date=date))
            return None
        self._add_problem(
            _(
                "Publication date format did not pass validation; format: %(date)s.",
                date=date,
            ),
        )
        return datetime.datetime.strftime(parsed, "%Y-%m-%d")
