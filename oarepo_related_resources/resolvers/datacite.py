#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of oarepo-related-resources (see https://github.com/oarepo/oarepo-related-resources).
#
# oarepo-related-resources is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
"""Related resources DataCite DOI resolver."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from flask import current_app
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.schemas.metadata import record_identifiers_schemes

from ..config import RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE
from .base import (
    DoiResolverBase,
    ResolverProblem,
)
from .utils import (
    build_person_or_org,
    escape_lucene,
    handle_errors,
    lookup_vocabulary_by_prop,
    lookup_vocabulary_by_prop_handle_multiple,
    resolve_language,
    split_personal_name,
    vocabulary_entry_exists,
)

if TYPE_CHECKING:
    from requests import Response


class DataciteResolver(DoiResolverBase):
    """Datacite resolver."""

    provider = "Datacite"

    not_found_message = _(
        "The identifier looks like a DOI, but it was not found in the DataCite registry."
    )
    unexpected_error_message = _(
        "Unexpected error while resolving the DOI. Please fill the metadata manually."
    )

    @override
    def get_metadata(self, response: Response) -> dict:
        return response.json()["data"]["attributes"]  # type: ignore[no-any-return]

    @override
    def resolve_metadata(self) -> tuple[dict[str, Any], list[ResolverProblem]]:
        """Map the resolver's metadata from identifier API response to the expected format."""
        self.resolve_title()
        self.resolve_creators()
        self.resolve_additional_titles()
        self.resolve_publication_date()
        self.resolve_resource_type()
        self.resolve_publisher()
        self.resolve_contributors()
        self.resolve_description()
        self.resolve_dates()
        self.resolve_subjects()
        self.resolve_language()
        self.resolve_related_identifiers()
        self.resolve_additional_descriptions()
        self.resolve_sizes()
        self.resolve_formats()
        self.resolve_version()
        self.resolve_rights()
        self.resolve_identifiers()
        return self.processed_metadata, self.problems

    @handle_errors()
    def resolve_additional_descriptions(self) -> None:
        """Extract and map non-abstract descriptions from DataCite metadata."""
        des_list = []
        for d in self.metadata.get("descriptions", []):
            _type = d.get("descriptionType")
            description = d.get("description")

            if (
                description
                and isinstance(_type, str)
                and _type != "Abstract"
                and isinstance(description, str)
            ):
                d_type = re.sub(r"(?<!^)([A-Z])", r"-\1", _type).lower()
                if not vocabulary_entry_exists("descriptiontypes", d_type):
                    continue
                description_obj: dict[str, Any] = {}
                description_obj["type"] = {"id": d_type}
                description_obj["description"] = description
                d_lang = d.get("lang")
                if not isinstance(d_lang, str):
                    continue
                lang = resolve_language(d_lang)
                if lang:
                    description_obj["lang"] = {"id": lang}
                des_list.append(description_obj)
        if des_list:
            self.processed_metadata["additional_descriptions"] = des_list

    @handle_errors()
    def resolve_description(self) -> None:
        """Extract the abstract description from DataCite metadata."""
        for d in self.metadata.get("descriptions", []):
            _type = d.get("descriptionType")
            description = d.get("description")
            if _type == "Abstract":
                self.processed_metadata["description"] = description
                break

    @handle_errors()
    def resolve_language(self) -> None:
        """Resolve and validate the language of the record."""
        datacite_language = self.metadata.get("language")
        language = resolve_language(datacite_language)
        if language:
            self.processed_metadata["languages"] = [{"id": language}]

    @handle_errors()
    def resolve_related_identifiers(self) -> None:
        """Resolve and validate related identifiers and their relation types."""
        result = []
        for rel in self.metadata.get("relatedIdentifiers", []):
            identifier = rel.get("relatedIdentifier")
            scheme = rel.get("relatedIdentifierType")
            rel_type = rel.get("relationType")
            if scheme:
                scheme = scheme.lower()
            obj = {"identifier": identifier, "scheme": scheme}
            resolved_rel_type = lookup_vocabulary_by_prop("relationtypes", rel_type)
            if resolved_rel_type is None:  # no duplicate values found in rdm fixtures
                continue
            obj["relation_type"] = {"id": resolved_rel_type}

            res_type = rel.get("resourceTypeGeneral")
            if res_type:
                # duplicate values possible here
                resolved_type = lookup_vocabulary_by_prop_handle_multiple(
                    "resourcetypes", res_type, prop="datacite_general"
                )
                if resolved_type is not None:
                    obj["resource_type"] = {"id": resolved_type}

            result.append(obj)

        if result:
            self.processed_metadata["related_identifiers"] = result

    @handle_errors()
    def resolve_publication_date(self) -> None:
        """Copy ``publicationYear`` from DataCite metadata into ``publication_date``."""
        publication_date = self.metadata.get("publicationYear")
        if publication_date:
            self.processed_metadata["publication_date"] = str(publication_date)

    @handle_errors()
    def resolve_dates(self) -> None:
        """Validate and map DataCite date entries to the target format."""
        dates_list = []
        for d in self.metadata.get("dates", []):
            date_object: dict[str, Any] = {}
            date = d.get("date")
            _type = d.get("dateType")
            # no duplicate values found in rdm fixtures
            # TODO: perhaps more effort to systematize missing vocabularies
            #  (eg. it logs error but does not return it user here)
            resolved_datatype = lookup_vocabulary_by_prop("datetypes", _type)
            if resolved_datatype is None:
                continue
            date_object["date"] = str(date)
            date_object["type"] = {"id": resolved_datatype}
            dates_list.append(date_object)
        if dates_list:
            self.processed_metadata["dates"] = dates_list

    @handle_errors()
    def resolve_rights(self) -> None:
        """Resolve and validate rights identifiers against the licenses vocabulary."""
        rights_list = []
        for r in self.metadata.get("rightsList", []):
            code = r.get("rightsIdentifier")
            if code and vocabulary_entry_exists("licenses", code):
                rights_list.append({"id": code})
        if rights_list:
            self.processed_metadata["rights"] = rights_list

    @handle_errors()
    def resolve_publisher(self) -> None:
        """Copy the ``publisher`` field from DataCite metadata when present."""
        if self.metadata.get("publisher"):
            self.processed_metadata["publisher"] = self.metadata.get("publisher")

    @handle_errors()
    def resolve_subjects(self) -> None:
        """Extract unique subject values from DataCite metadata."""
        subjects_list = []
        seen = set()
        for s in self.metadata.get("subjects", []):
            if not isinstance(s, dict):
                continue

            value = s.get("subject")
            if not value or not isinstance(value, str):
                continue
            if value in seen:
                continue
            seen.add(value)
            subjects_list.append({"subject": value})
        if subjects_list:
            self.processed_metadata["subjects"] = subjects_list

    @handle_errors(alert_user=True)
    def resolve_title(self) -> None:
        """Extract the main title from DataCite metadata and validate its length."""
        titles = [
            t["title"]
            for t in self.metadata.get("titles", [])
            if "title" in t and "titleType" not in t
        ]
        if titles:
            self.processed_metadata["title"] = titles[0]

    @handle_errors()
    def resolve_additional_titles(self) -> None:
        """Extract and map additional titles from DataCite metadata."""
        additional_titles = []
        for title in self.metadata.get("titles", []):
            title_obj = {}
            t_type = title.get("titleType")
            if t_type is None:  # it is main title
                continue
            resolved_type = lookup_vocabulary_by_prop(
                "titletypes", t_type
            )  # no duplicate values found in rdm fixtures
            if resolved_type is None:
                continue
            t_lang = None
            title_obj["title"] = title.get("title")
            title_obj["type"] = {"id": resolved_type}

            if "lang" in title:
                t_lang = resolve_language(title["lang"])
            if t_lang:
                title_obj["lang"] = {"id": t_lang}
            additional_titles.append(title_obj)

        if additional_titles:
            self.processed_metadata["additional_titles"] = additional_titles

    @handle_errors(alert_user=True)
    def resolve_creators(self) -> None:
        """Extract and map creator information from DataCite metadata."""
        creators = [
            self._resolve_datacite_author(creator, "creator")
            for creator in self.metadata.get("creators", [])
        ]
        creators = [c for c in creators if c is not None]
        if creators:
            self.processed_metadata["creators"] = creators

    @handle_errors()
    def resolve_contributors(self) -> None:
        """Extract and map contributor information including roles and affiliations."""
        contributor_list = []
        for contributor in self.metadata.get("contributors", []):
            entry = self._resolve_datacite_author(contributor, "contributor")
            if not entry:
                continue
            # Resolve contributor role
            role = contributor.get("contributorType")
            resolved_role = lookup_vocabulary_by_prop(
                "contributorsroles", role
            )  # no contributorroles vocabulary in rdm fixtures
            if resolved_role:
                entry["role"] = {"id": resolved_role}
            contributor_list.append(entry)

        if contributor_list:
            self.processed_metadata["contributors"] = contributor_list

    @handle_errors()
    def resolve_resource_type(self) -> None:
        """Resolve and map the DataCite resource type to a vocabulary identifier."""
        resource_type = self.metadata.get("types", {})
        vocabulary_id = "resourcetypes"
        _type = resource_type.get("resourceTypeGeneral") or "Other"

        escaped = escape_lucene(_type)
        if escaped == "Image":
            self.processed_metadata["resource_type"] = {"id": "image"}
            return
        resolved_type = lookup_vocabulary_by_prop_handle_multiple(
            vocabulary_id, escaped.lower()
        )
        if not resolved_type:
            self._add_problem(
                _(
                    "The provided resource type %s could not be parsed. The default value %s has been applied."
                )
                % (_type, RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE),
            )
            self.processed_metadata["resource_type"] = {
                "id": RELATED_RESOURCES_DEFAULT_RESOURCE_TYPE
            }
            return
        self.processed_metadata["resource_type"] = {"id": resolved_type}

    @handle_errors()
    def resolve_identifiers(self) -> None:
        """Resolve and map identifiers from DataCite metadata."""
        identifiers = [
            {
                "identifier": id_with_scheme["identifier"],
                "scheme": id_with_scheme["identifierType"].lower(),
            }
            for id_with_scheme in self.metadata.get("identifiers", [])
            if id_with_scheme["identifierType"].lower() in record_identifiers_schemes
        ]
        if identifiers:
            self.processed_metadata["identifiers"] = identifiers

    @handle_errors()
    def resolve_sizes(self) -> None:
        """Copy the ``sizes`` field from the DataCite metadata when present."""
        val = self.metadata.get("sizes", None)
        if val:
            self.processed_metadata["sizes"] = val

    @handle_errors()
    def resolve_formats(self) -> None:
        """Copy the ``formats`` field from the DataCite metadata when present."""
        val = self.metadata.get("formats", None)
        if val:
            self.processed_metadata["formats"] = val

    @handle_errors()
    def resolve_version(self) -> None:
        """Copy the ``version`` field from the DataCite metadata when present."""
        val = self.metadata.get("version", None)
        if val:
            self.processed_metadata["version"] = val

    @handle_errors()
    def _resolve_datacite_affiliations(self, affiliations: list | None) -> list:
        """Extract and normalize affiliation entries while removing duplicates."""
        affiliations_list = []
        seen = set()

        for a in affiliations or []:
            if isinstance(a, str):
                if a in seen:
                    continue
                seen.add(a)
                affiliations_list.append({"name": a})
            elif isinstance(a, dict):
                a_scheme = a.get("affiliationIdentifierScheme")
                if a_scheme == "ROR":
                    a_identifier = a.get("affiliationIdentifier")
                    if not a_identifier or a_identifier in seen:
                        continue
                    affiliations_list.append({"id": a_identifier})
                    seen.add(a_identifier)
                else:
                    name = a.get("name")
                    if not name or not isinstance(name, str):
                        continue
                    if name in seen:
                        continue
                    seen.add(name)

                    affiliations_list.append({"name": name})

        return affiliations_list

    def _resolve_datacite_author(
        self, author: dict[str, Any], type_: str
    ) -> dict[str, Any] | None:
        author_type = (author.get("nameType") or "personal").lower()
        given = author.get("givenName")
        family = author.get("familyName")
        name = author.get("name")

        if name is None:  # should never happen
            self._add_problem(_("Missing %ss name: %s.") % (type_, author))
            return None

        if author_type == "personal":
            parsed_family, parsed_given = split_personal_name(name)
            family = family or parsed_family
            given = given or (parsed_given or None)

        identifiers = self._resolve_datacite_name_identifiers(
            name_identifiers=author.get("nameIdentifiers", [])
        )
        affiliations = self._resolve_datacite_affiliations(
            author.get("affiliation", [])
        )
        return build_person_or_org(
            name=name,
            type_=author_type,
            given=given,
            family=family,
            identifiers=identifiers if isinstance(identifiers, list) else None,
            affiliations=affiliations,
        )

    @handle_errors()
    def _resolve_datacite_name_identifiers(
        self, *, name_identifiers: list | None
    ) -> list:
        """Resolve and normalize name identifiers including ORCID handling."""
        from oarepo_related_resources.services import resolve_orcid

        identifiers = []
        seen = []
        for ni in name_identifiers or []:
            identifier = ni.get("nameIdentifier")
            if identifier in seen:  # needs to be unique
                continue
            seen.append(identifier)
            scheme = ni.get("nameIdentifierScheme")
            if scheme:
                scheme = scheme.lower()
            if not identifier or not scheme:
                continue
            if scheme == "orcid":
                try:
                    identifier_dict = resolve_orcid(
                        orcid=identifier,
                        vocabulary="names",
                        parent=ni,
                        create_vocabulary_record=True,
                        check_existing=True,
                    )
                    identifier = identifier_dict["id"]
                except Exception:
                    current_app.logger.exception(
                        "Error resolving ORCID identifier '%s'.",
                        identifier,
                    )
                    continue
            obj = {"identifier": identifier}

            obj["scheme"] = scheme
            identifiers.append(obj)
        return identifiers
