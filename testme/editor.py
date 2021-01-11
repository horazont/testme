import enum

import sqlalchemy.orm.exc

import wtforms
import wtforms.validators

import flask

from flask import (
    abort, render_template, redirect, url_for, request, current_app
)
from flask_wtf import FlaskForm

from .infra import db
from . import model


ACTION_KEY_SAVE_AND_RETURN = "save_and_return"
ACTION_KEY_GOTO_QUESTION = "goto_question"
ACTION_KEY_ADD_CHOICE = "add_choice"
ACTION_KEY_ADD_QUESTION = "add_question"


bp = flask.Blueprint('editor', __name__)


class QuestionActionForm(FlaskForm):
    id_ = wtforms.IntegerField(
        widget=wtforms.widgets.HiddenInput(),
    )

    order = wtforms.IntegerField(
        widget=wtforms.widgets.HiddenInput(),
    )

    action_move_top = wtforms.SubmitField(
        "↟"
    )

    action_move_up = wtforms.SubmitField(
        "↑"
    )

    action_move_down = wtforms.SubmitField(
        "↓"
    )

    action_move_bottom = wtforms.SubmitField(
        "↡"
    )

    action_delete = wtforms.SubmitField(
        "🗑"
    )


class ProfileForm(FlaskForm):
    id_ = wtforms.IntegerField(
        widget=wtforms.widgets.HiddenInput(),
    )

    title = wtforms.StringField(
        "Titel",
    )

    body = wtforms.TextAreaField(
        "Beschreibung",
    )

    action_delete = wtforms.SubmitField(
        "Löschen"
    )


class RootForm(FlaskForm):
    title = wtforms.StringField(
        "Titel",
        validators=[wtforms.validators.DataRequired()],
    )

    questions = wtforms.FieldList(
        wtforms.FormField(QuestionActionForm)
    )

    profiles = wtforms.FieldList(
        wtforms.FormField(ProfileForm),
    )

    action_save = wtforms.SubmitField(
        "Speichern",
    )

    action_save_and_start = wtforms.SubmitField(
        "Speichern und starten",
    )

    action_goto_question = wtforms.IntegerField(
        "✎",
    )

    action_add_question = wtforms.SubmitField(
        "Frage hinzufügen"
    )

    action_add_profile = wtforms.SubmitField(
        "Profil hinzufügen"
    )


def get_questionaire(id_: bytes, edit_id: bytes) -> model.Questionnaire:
    try:
        return db.session.query(
            model.Questionnaire
        ).filter(
            model.Questionnaire.id_ == id_,
            model.Questionnaire.edit_id == edit_id,
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return abort(404, 'no such questionnaire')


def manage_ordered_items(form_entries, items, apply_fun):
    item_map = {item.id_: item for item in items}
    output_order = list(item_map)
    move_action = None
    if items:
        least_order = min(c.order for c in items)
        next_order = max(c.order for c in items) + 1
    else:
        least_order = 0
        next_order = 0

    for posted_choice in form_entries:
        id_ = posted_choice.id_.data
        target = item_map[id_]
        if posted_choice.action_move_top.data:
            move_action = (MoveAction.MOVE_TOP, id_)
        elif posted_choice.action_move_bottom.data:
            move_action = (MoveAction.MOVE_BOTTOM, id_)
        elif posted_choice.action_move_up.data:
            move_action = (MoveAction.MOVE_UP, id_)
        elif posted_choice.action_move_down.data:
            move_action = (MoveAction.MOVE_DOWN, id_)
        elif posted_choice.action_delete.data:
            db.session.delete(target)
            output_order.remove(id_)
            continue

        apply_fun(target, posted_choice)
        db.session.add(target)
        # move ID to the end of the list
        output_order.remove(id_)
        output_order.append(id_)

    if move_action is not None:
        type_, target_id = move_action
        if type_ == MoveAction.MOVE_TOP:
            output_order.remove(target_id)
            output_order.insert(0, target_id)
        elif type_ == MoveAction.MOVE_BOTTOM:
            output_order.remove(target_id)
            output_order.append(target_id)
        else:
            offset = -1 if type_ == MoveAction.MOVE_UP else 1
            index = output_order.index(target_id)
            if not (
                    (offset == -1 and index == 0) or
                    (offset == 1 and index == len(output_order) - 1)):
                new_index = index + offset
                del output_order[index]
                output_order.insert(new_index, target_id)

        # execute reorder by rewriting order field
        if len(output_order) < least_order:
            # renumber from zero because we have enough space to do so
            next_order = 0

        for i, id_ in enumerate(output_order, next_order):
            target = item_map[id_]
            target.order = i
            db.session.add(target)

        next_order = next_order + len(output_order)
    else:
        # apply order from form
        for posted_choice in form_entries:
            target = item_map[posted_choice.id_.data]
            target.order = posted_choice.order.data

    return next_order


@bp.route("/<id:id_>/<id:edit_id>", methods=["GET", "POST"])
def root(id_: bytes, edit_id: bytes):
    qn = get_questionaire(id_, edit_id)

    profiles = list(db.session.query(
        model.Profile,
    ).filter(
        model.Profile.qid == id_,
    ).order_by(
        model.Profile.id_.asc(),
    ))

    questions_with_count = list(db.session.query(
        model.Question, sqlalchemy.func.count(model.Choice.id_),
    ).select_from(
        model.Question,
    ).outerjoin(
        model.Choice,
    ).filter(
        model.Question.qid == id_,
    ).group_by(
        model.Question.id_,
    ).order_by(
        model.Question.order.asc(),
    ))

    participants = list(db.session.query(
        model.Participant.id_, model.Participant.name,
    ).filter(
        model.Participant.qid == id_,
    ))

    questions = [q for q, _ in questions_with_count]
    questions_extra = {
        q.id_: {
            "title": q.title,
            "choices": choice_count,
        }
        for q, choice_count in questions_with_count
    }

    action_url = url_for(".root", id_=id_, edit_id=edit_id)

    form = RootForm()
    if form.validate_on_submit():
        qn.title = form.title.data
        db.session.add(qn)

        def apply_question_update(question, posted_question):
            pass

        next_order = manage_ordered_items(
            form.questions,
            questions,
            apply_question_update,
        )

        profile_map = {profile.id_: profile for profile in profiles}
        for posted_profile in form.profiles.entries:
            target = profile_map[posted_profile.id_.data]

            if posted_profile.action_delete.data:
                db.session.delete(target)
            else:
                target.title = posted_profile.title.data
                target.description = posted_profile.body.data
                db.session.add(target)

        if form.action_add_question.data:
            new_question = model.Question()
            new_question.qid = qn.id_
            new_question.title = "Unbenannt"
            new_question.body = "Text eingeben"
            new_question.multiple_choice = False
            new_question.shuffled = False
            new_question.order = next_order
            new_question.allow_none = False
            db.session.add(new_question)
            db.session.commit()
            return redirect(url_for(
                ".question",
                qid=id_,
                edit_id=edit_id,
                question_id=new_question.id_,
            ))

        if form.action_add_profile.data:
            new_profile = model.Profile()
            new_profile.qid = qn.id_
            new_profile.title = "Unbenannt"
            new_profile.description = "Beschreibung eingeben"
            db.session.add(new_profile)

        db.session.commit()
        if form.action_goto_question.data is not None:
            return redirect(url_for(
                ".question",
                qid=id_, edit_id=edit_id,
                question_id=form.action_goto_question.data,
            ))

        if form.action_save_and_start.data:
            return redirect(url_for(
                "questionnaire.start",
                qid=id_,
            ))

        return redirect(action_url)

    elif request.method != "POST":
        form.title.data = qn.title
        for profile in profiles:
            entry = form.profiles.append_entry()
            entry.id_.data = profile.id_
            entry.title.data = profile.title
            entry.body.data = profile.description

        for question in questions:
            entry = form.questions.append_entry()
            entry.id_.data = question.id_
            entry.order.data = question.order

    return render_template(
        "edit.html",
        action_url=action_url,
        id_=id_,
        edit_id=edit_id,
        form=form,
        questions=questions,
        questions_extra=questions_extra,
        participants=participants,
        external_url="{}{}".format(
            current_app.config["EXTERNAL_PREFIX"],
            url_for("questionnaire.start", qid=id_)
        ),
    )


class WeightForm(FlaskForm):
    profile_id = wtforms.IntegerField(
        widget=wtforms.widgets.HiddenInput(),
    )

    weight = wtforms.DecimalField(
        "Punkte",
        places=2,
    )


class ChoiceForm(FlaskForm):
    id_ = wtforms.IntegerField(
        widget=wtforms.widgets.HiddenInput(),
    )

    body = wtforms.TextAreaField(
        "Inhalt",
        validators=[wtforms.validators.DataRequired()],
    )

    order = wtforms.IntegerField(
        widget=wtforms.widgets.HiddenInput(),
    )

    weights = wtforms.FieldList(
        wtforms.FormField(WeightForm)
    )

    action_move_top = wtforms.SubmitField(
        "↟"
    )

    action_move_up = wtforms.SubmitField(
        "↑"
    )

    action_move_down = wtforms.SubmitField(
        "↓"
    )

    action_move_bottom = wtforms.SubmitField(
        "↡"
    )

    action_delete = wtforms.SubmitField(
        "🗑"
    )


class QuestionForm(FlaskForm):
    title = wtforms.StringField(
        "Titel",
        validators=[wtforms.validators.DataRequired()],
    )

    body = wtforms.TextAreaField(
        "Inhalt",
        validators=[wtforms.validators.DataRequired()],
    )

    multiple_choice = wtforms.BooleanField(
        "Mehrere Antworten erlaubt",
    )

    allow_none = wtforms.BooleanField(
        "Keine Antwort erlaubt (nur für multiple-choice)"
    )

    shuffled = wtforms.BooleanField(
        "Antworten in zufälliger Reihenfolge anzeigen",
    )

    choices = wtforms.FieldList(
        wtforms.FormField(ChoiceForm),
    )

    action_save = wtforms.SubmitField(
        "Speichern",
    )

    action_save_and_return = wtforms.SubmitField(
        "Speichern und zurück",
    )

    action_add_choice = wtforms.SubmitField(
        "Antwortmöglichkeit hinzufügen",
    )


class MoveAction(enum.Enum):
    MOVE_TOP = "top"
    MOVE_UP = "up"
    MOVE_DOWN = "down"
    MOVE_BOTTOM = "bottom"


@bp.route("/<id:qid>/<id:edit_id>/question/<int:question_id>",
          methods=["GET", "POST"])
def question(qid, edit_id, question_id):
    qn = get_questionaire(qid, edit_id)
    try:
        question = db.session.query(
            model.Question,
        ).filter(
            model.Question.id_ == question_id,
            model.Question.qid == qid,
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return abort(404, 'no such question')

    profiles = list(db.session.query(
        model.Profile,
    ).filter(
        model.Profile.qid == qid,
    ).order_by(
        model.Profile.id_.asc(),
    ))
    valid_profiles = set(p.id_ for p in profiles)

    choices = list(db.session.query(
        model.Choice,
    ).filter(
        model.Choice.question_id == question_id,
    ).order_by(
        model.Choice.order.asc(),
    ))

    weight_matrix = {}
    for choice_id, profile_id, weight in db.session.query(
                model.ChoiceProfileWeight.choice_id,
                model.ChoiceProfileWeight.profile_id,
                model.ChoiceProfileWeight.weight,
            ).select_from(
                model.Choice
            ).join(
                model.Profile,
                model.Profile.qid == qid,
            ).outerjoin(
                model.ChoiceProfileWeight,
                sqlalchemy.and_(
                    model.Choice.id_ == model.ChoiceProfileWeight.choice_id,
                    model.Profile.id_ == model.ChoiceProfileWeight.profile_id,
                ),
            ).filter(
                model.Choice.question_id == question_id,
            ):
        weight_matrix.setdefault(choice_id, {})[profile_id] = weight

    form = QuestionForm()
    if form.validate_on_submit():
        question.title = form.title.data
        question.body = form.body.data
        question.multiple_choice = form.multiple_choice.data
        question.allow_none = form.allow_none.data
        question.shuffled = form.shuffled.data
        db.session.add(question)

        def apply_choice_update(choice, posted_choice):
            choice.body = posted_choice.body.data
            for profile in posted_choice.weights:
                profile_id = profile.profile_id.data
                if profile_id not in valid_profiles:
                    continue
                model.ChoiceProfileWeight.upsert(
                    db.session,
                    choice.id_,
                    profile_id,
                    float(profile.weight.data),
                )

        next_order = manage_ordered_items(
            form.choices,
            choices,
            apply_choice_update,
        )

        if form.action_add_choice.data:
            new_choice = model.Choice()
            new_choice.question_id = question.id_
            new_choice.body = "Text eingeben"
            new_choice.order = next_order
            db.session.add(new_choice)

        db.session.commit()

        if form.action_save_and_return.data:
            return redirect(url_for(
                ".root",
                id_=qid, edit_id=edit_id,
            ))

        return redirect(url_for(
            ".question",
            qid=qid, edit_id=edit_id,
            question_id=question_id,
        ))
    elif request.method != "POST":
        form.title.data = question.title
        form.body.data = question.body
        form.multiple_choice.data = question.multiple_choice
        form.allow_none.data = question.allow_none
        form.shuffled.data = question.shuffled

        for choice in choices:
            entry = form.choices.append_entry()
            entry.id_.data = choice.id_
            entry.order.data = choice.order
            entry.body.data = choice.body

            for profile in profiles:
                weight_entry = entry.weights.append_entry()
                weight_entry.profile_id.data = profile.id_
                weight_entry.weight.data = weight_matrix.get(
                    choice.id_, {}
                ).get(profile.id_, 0.0)

    return render_template(
        "edit_question.html",
        form=form,
        qid=qid,
        edit_id=edit_id,
        profiles=profiles,
    )
