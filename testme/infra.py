import flask_sqlalchemy
import flask_babel

import testme.model


db = flask_sqlalchemy.SQLAlchemy(metadata=testme.model.Base.metadata)
babel = flask_babel.Babel()


@babel.localeselector
def selected_locale():
    return "de_DE"
