import collections
import itertools
import random

import sqlalchemy.orm
import sqlalchemy.sql

import wtforms

import flask
import flask_wtf
from flask import render_template, abort, redirect, url_for

from .infra import db
from . import model

bp = flask.Blueprint("questionnaire", __name__)


class StartForm(flask_wtf.FlaskForm):
    name = wtforms.StringField(
        "Nenne deinen Namen",
        validators=[wtforms.validators.DataRequired()],
    )

    action_start = wtforms.SubmitField(
        "Test starten"
    )


def get_questionnaire(qid: bytes) -> model.Questionnaire:
    try:
        return db.session.query(model.Questionnaire).filter(
            model.Questionnaire.id_ == qid,
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return abort(404, "no such questionnaire")


def get_question(qid: bytes, question_id: int) -> model.Questionnaire:
    try:
        return db.session.query(model.Question).filter(
            model.Question.id_ == question_id,
            model.Question.qid == qid,
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return abort(404, "no such questionnaire")


def get_participant(qid: bytes, participant_id: bytes) -> model.Questionnaire:
    try:
        return db.session.query(model.Participant).filter(
            model.Participant.id_ == participant_id,
            model.Participant.qid == qid,
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return abort(401, "no such participant")


def get_first_question_id(qid: bytes) -> int:
    return db.session.query(
        model.Question.id_,
    ).filter(
        model.Question.qid == qid,
    ).order_by(
        model.Question.order.asc(),
    ).limit(1).one()[0]


@bp.route("/<id:qid>/start", methods=["GET", "POST"])
def start(qid):
    qn = get_questionnaire(qid)
    try:
        get_first_question_id(qid)
    except sqlalchemy.orm.exc.NoResultFound:
        return abort(500, "invalid questionnaire")

    form = StartForm()
    if form.validate_on_submit():
        new_participant = model.Participant()
        new_participant.id_ = model.generate_id()
        new_participant.qid = qid
        new_participant.name = form.name.data
        db.session.add(new_participant)
        db.session.commit()

        return redirect(url_for(
            ".question_autoroute",
            qid=qid,
            participant_id=new_participant.id_,
        ))

    return render_template(
        "drachen_start.html",
        qid=qid,
        title=qn.title,
        form=form,
    )


def get_next_question_id(qid: bytes, current_order: int) -> int:
    try:
        return db.session.query(
            model.Question.id_
        ).filter(
            model.Question.qid == qid,
            model.Question.order > current_order
        ).order_by(
            model.Question.order.asc(),
        ).limit(1).one()[0]
    except sqlalchemy.orm.exc.NoResultFound:
        return None


@bp.route("/<id:qid>/<id:participant_id>/q", methods=["GET"])
def question_autoroute(qid, participant_id):
    participant = get_participant(qid, participant_id)
    try:
        last_question_order, = db.session.query(
            model.Question.order,
        ).select_from(
            model.Answer
        ).join(
            model.Choice,
        ).join(
            model.Question,
        ).filter(
            model.Answer.participant_id == participant_id,
        ).order_by(
            model.Question.order.desc()
        ).limit(1).one()
    except sqlalchemy.orm.exc.NoResultFound:
        next_question_id = get_first_question_id(qid)
    else:
        next_question_id = get_next_question_id(qid, last_question_order)
        if next_question_id is None:
            # test complete!
            return redirect(url_for(
                ".complete",
                qid=qid,
                participant_id=participant_id,
            ))
    return redirect(url_for(
        ".question",
        qid=qid,
        participant_id=participant_id,
        question_id=next_question_id,
    ))


class SingleChoiceQuestionForm(flask_wtf.FlaskForm):
    choices = wtforms.RadioField()

    action_submit = wtforms.SubmitField(
        "Weiter"
    )

    def set_choices(self, choices):
        self.choices.choices = choices


class MultipleChoiceQuestionForm(flask_wtf.FlaskForm):
    choices = wtforms.SelectMultipleField(
        coerce=int,
        option_widget=wtforms.widgets.CheckboxInput(),
    )

    action_submit = wtforms.SubmitField(
        "Weiter"
    )

    def set_choices(self, choices):
        self.choices.choices = choices


@bp.route("/<id:qid>/<id:participant_id>/q/<int:question_id>",
          methods=["GET", "POST"])
def question(qid, participant_id, question_id):
    qn = get_questionnaire(qid)
    question = get_question(qid, question_id)
    participant = get_participant(qid, participant_id)

    choices = list(db.session.query(
        model.Choice.id_, model.Choice.body
    ).filter(
        model.Choice.question_id == question_id,
    ).order_by(model.Choice.order.asc()))

    if question.shuffled:
        random.shuffle(choices)

    is_complete = False
    if question.multiple_choice:
        form = MultipleChoiceQuestionForm()
        if not question.allow_none:
            form.choices.validators = form.choices.validators + (
                wtforms.validators.DataRequired(),
            )
        form.set_choices(choices)
        if form.validate_on_submit():
            db.session.query(
                model.Answer
            ).filter(
                model.Answer.participant_id == participant_id,
                model.Answer.choice_id.in_([c[0] for c in choices])
            ).delete(synchronize_session=False)

            for choice_id in form.choices.data:
                answer = model.Answer()
                answer.choice_id = choice_id
                answer.participant_id = participant_id
                db.session.add(answer)

            db.session.commit()
            is_complete = True
    else:
        form = SingleChoiceQuestionForm()
        form.set_choices(choices)
        if form.validate_on_submit():
            db.session.query(
                model.Answer
            ).filter(
                model.Answer.participant_id == participant_id,
                model.Answer.choice_id.in_([c[0] for c in choices])
            ).delete(synchronize_session=False)

            answer = model.Answer()
            answer.choice_id = form.choices.data
            answer.participant_id = participant_id
            db.session.add(answer)

            db.session.commit()
            is_complete = True

    if is_complete:
        next_question_id = get_next_question_id(qid, question.order)
        if next_question_id is None:
            return redirect(url_for(
                ".complete",
                qid=qid,
                participant_id=participant_id,
            ))

        return redirect(url_for(
            ".question",
            qid=qid,
            participant_id=participant_id,
            question_id=next_question_id,
        ))

    return render_template(
        "drachen_question.html",
        form=form,
        qn_title=qn.title,
        question_title=question.title,
        question_text=question.body,
        multiple_choice=question.multiple_choice,
        allow_none=question.multiple_choice and question.allow_none,
    )


@bp.route("/<id:qid>/<id:participant_id>/result")
def complete(qid: bytes, participant_id: bytes):
    qn = get_questionnaire(qid)
    participant = get_participant(qid, participant_id)

    profiles = list(db.session.query(
        model.Profile,
    ).filter(
        model.Profile.qid == qid
    ))

    max_scores_by_question = db.session.query(
        model.Question.id_,
        model.Profile.id_,
        sqlalchemy.sql.case(
            [
                (model.Question.multiple_choice,
                 sqlalchemy.func.sum(model.ChoiceProfileWeight.weight)),
            ],
            else_=sqlalchemy.func.max(model.ChoiceProfileWeight.weight),
        )
    ).select_from(
        model.Question,
    ).join(
        model.Profile,
        model.Profile.qid == model.Question.qid,
    ).join(
        model.Choice,
        model.Choice.question_id == model.Question.id_,
    ).join(
        model.ChoiceProfileWeight,
        sqlalchemy.and_(
            model.ChoiceProfileWeight.choice_id == model.Choice.id_,
            model.ChoiceProfileWeight.profile_id == model.Profile.id_,
        )
    ).filter(
        model.Question.qid == qid,
    ).group_by(
        model.Question.id_,
        model.Profile.id_,
    )

    max_scores = collections.Counter()
    for _, profile_id, score in max_scores_by_question:
        max_scores[profile_id] += score

    obtained_scores = dict(db.session.query(
        model.Profile.id_,
        sqlalchemy.func.sum(model.ChoiceProfileWeight.weight),
    ).select_from(
        model.Answer,
    ).join(
        model.Profile,
        model.Profile.qid == qid,
    ).join(
        model.ChoiceProfileWeight,
        sqlalchemy.and_(
            model.ChoiceProfileWeight.profile_id == model.Profile.id_,
            model.ChoiceProfileWeight.choice_id == model.Answer.choice_id,
        ),
    ).group_by(
        model.Profile.id_,
    ).filter(
        model.Answer.participant_id == participant_id,
    ))

    profile_info = []
    for profile in profiles:
        try:
            score = (obtained_scores.get(profile.id_, 0) /
                     max_scores[profile.id_])
        except ZeroDivisionError:
            score = 0

        profile_info.append(
            {
                "title": profile.title,
                "body": profile.description,
                "score": score,
            }
        )

    profile_info.sort(key=lambda x: x["score"], reverse=True)

    questions_and_answers = list(db.session.query(
        model.Question.id_,
        model.Question.title,
        sqlalchemy.sql.case(
            [(model.Answer.participant_id != None,  # noqa:e711
              model.Choice.body)],
            else_=None,
        ),
    ).select_from(
        model.Question,
    ).join(
        model.Choice,
    ).outerjoin(
        model.Answer,
        sqlalchemy.and_(
            model.Answer.choice_id == model.Choice.id_,
            model.Answer.participant_id == participant_id,
        )
    ).filter(
        model.Question.qid == qid,
    ).order_by(
        model.Question.order.asc(),
        model.Choice.order.asc(),
    ))

    questions = []
    for question_id, question_data in itertools.groupby(
            questions_and_answers,
            key=lambda x: x[0]):
        question_data = list(question_data)
        question_title = question_data[0][1]
        questions.append(
            (question_title, [
                answer_text for _, _, answer_text in question_data
                if answer_text is not None
            ])
        )

    return render_template(
        "drachen_result_detail.html",
        profiles=profile_info,
        name=participant.name,
        qn_title=qn.title,
        questions=questions,
    )
