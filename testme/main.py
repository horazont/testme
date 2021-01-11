import wtforms

import flask
import flask_wtf

from flask import render_template, redirect, url_for

from .infra import db
from . import model

bp = flask.Blueprint('main', __name__)


class NewForm(flask_wtf.FlaskForm):
    action_new = wtforms.SubmitField("Neuer Test")


@bp.route("/", methods=["GET", "POST"])
def index():
    form = NewForm()

    if form.validate_on_submit():
        questionnaire = model.Questionnaire()
        questionnaire.id_ = model.generate_id()
        questionnaire.edit_id = model.generate_id()
        questionnaire.title = "Unbenannt"
        db.session.add(questionnaire)
        db.session.commit()

        return redirect(url_for("editor.root",
                                id_=questionnaire.id_,
                                edit_id=questionnaire.edit_id))

    return render_template("index.html", form=form)
