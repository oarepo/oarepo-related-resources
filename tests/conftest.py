import pytest
from flask import Flask


class _DummyDomain:
    def gettext(self, message, **variables):
        if variables:
            return message % variables
        return message

    def ngettext(self, singular, plural, n, **variables):
        message = singular if n == 1 else plural
        if variables:
            return message % variables
        return message


class _DummyBabel:
    domain = _DummyDomain()


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["PERSISTENT_IDENTIFIER_RESOLVERS"] = [
        "oarepo_related_resources.resolvers.DataciteResolver",
        "oarepo_related_resources.resolvers.CrossrefResolver",
        "oarepo_related_resources.resolvers.HandleResolver",
    ]
    app.config["DATACITE_URL"] = "https://api.datacite.test/dois"
    app.config["CROSSREF_URL"] = "https://api.crossref.test/works/doi"
    app.config["HANDLE_URL"] = "https://hdl.handle.net"
    app.extensions["babel"] = _DummyBabel()
    with app.app_context():
        yield app
