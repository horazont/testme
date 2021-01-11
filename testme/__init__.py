import base64

import environ

import flask
import flask_babel
import flask_wtf.csrf
import flaskext.markdown
import werkzeug.routing

from flask import render_template

from .infra import db, babel
from .main import bp as bp_main
from .editor import bp as bp_editor
from .questionnaire import bp as bp_questionnaire


class IDConverter(werkzeug.routing.BaseConverter):
    regex = r"(?:[a-zA-Z0-9_-]+=*)"

    def to_python(self, v: str) -> bytes:
        if v.endswith("="):
            raise werkzeug.routing.ValidationError
        missing = 4 - (len(v) % 4)
        full = v + "=" * missing
        result = base64.urlsafe_b64decode(full)
        if full != base64.urlsafe_b64encode(result).decode("ascii"):
            raise werkzeug.routing.ValidationError
        return result

    def to_url(self, v: bytes) -> str:
        return base64.urlsafe_b64encode(v).decode("ascii").rstrip("=")


@environ.config(prefix="TESTME")
class AppConfig:
    db_uri = environ.var()
    secret_key = environ.var()
    external_prefix = environ.var()


def create_app():
    config = environ.to_config(AppConfig)

    app = flask.Flask(__name__)
    app.url_map.converters["id"] = IDConverter
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = config.db_uri
    app.config["SECRET_KEY"] = config.secret_key
    app.config["EXTERNAL_PREFIX"] = config.external_prefix

    db.init_app(app)
    babel.init_app(app)
    flask_wtf.csrf.CSRFProtect(app)
    flaskext.markdown.Markdown(
        app,
        safe_mode=True,
        output_format="html5",
    )

    app.register_blueprint(bp_main)
    app.register_blueprint(bp_editor, url_prefix='/edit')
    app.register_blueprint(bp_questionnaire, url_prefix='/q')

    @app.template_filter(name="format_percent")
    def format_percent(p, **kwargs):
        return flask_babel.format_percent(p, **kwargs)

    return app
