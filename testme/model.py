import contextlib
import secrets

import sqlalchemy
from sqlalchemy import (
    Column,
    Integer,
    Unicode,
    ForeignKey,
    BINARY,
    UnicodeText,
    UniqueConstraint,
    Boolean,
    Float,
)
from sqlalchemy.orm import (
    relationship,
)
from sqlalchemy.ext.declarative import declarative_base


@contextlib.contextmanager
def session_scope(sessionmaker):
    """Provide a transactional scope around a series of operations."""
    session = sessionmaker()
    try:
        yield session
    except:  # NOQA
        session.rollback()
        raise
    finally:
        session.close()


def get_generic_engine(uri: str) -> sqlalchemy.engine.Engine:
    engine = sqlalchemy.create_engine(uri)

    if uri.startswith("sqlite://"):
        # https://stackoverflow.com/questions/1654857/
        @sqlalchemy.event.listens_for(engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            # disable pysqlite's emitting of the BEGIN statement entirely.
            # also stops it from emitting COMMIT before any DDL.
            dbapi_connection.isolation_level = None
            # holy smokes, enforce foreign keys!!k
            dbapi_connection.execute('pragma foreign_keys=ON')

        @sqlalchemy.event.listens_for(engine, "begin")
        def do_begin(conn):
            # emit our own BEGIN
            conn.execute("BEGIN")

    return engine


class Base(declarative_base()):
    __abstract__ = True
    __table_args__ = {}


_ID_SIZE = 8
IDType = BINARY(_ID_SIZE)


def generate_id():
    return secrets.token_bytes(_ID_SIZE)


class Questionnaire(Base):
    __tablename__ = "questionnaire"

    id_ = Column(
        "id",
        IDType,
        primary_key=True,
        nullable=False,
    )

    edit_id = Column(
        "edit_id",
        IDType,
        nullable=False,
    )

    title = Column(
        "title",
        Unicode(256),
        nullable=False,
    )


class Profile(Base):
    __tablename__ = "profile"

    id_ = Column(
        "id",
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )

    qid = Column(
        "qid",
        IDType,
        ForeignKey(Questionnaire.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    title = Column(
        "title",
        Unicode(256),
        nullable=False,
    )

    description = Column(
        "description",
        UnicodeText(),
        nullable=False,
    )


class Question(Base):
    __tablename__ = "question"
    __table_args__ = (
        UniqueConstraint(
            "qid", "order",
        ),
        {},
    )

    id_ = Column(
        "id",
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )

    qid = Column(
        "qid",
        IDType,
        ForeignKey(Questionnaire.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    order = Column(
        "order",
        Integer(),
        nullable=False,
    )

    title = Column(
        "title",
        Unicode(256),
        nullable=False,
    )

    body = Column(
        "body",
        UnicodeText(),
        nullable=True,
    )

    multiple_choice = Column(
        "multiple_choice",
        Boolean(),
        nullable=False,
    )

    allow_none = Column(
        "allow_none",
        Boolean(),
        nullable=False,
    )

    shuffled = Column(
        "shuffled",
        Boolean(),
        nullable=False,
    )


class Choice(Base):
    __tablename__ = "choice"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "order",
        ),
        {},
    )

    id_ = Column(
        "id",
        Integer,
        primary_key=True,
        nullable=False,
        autoincrement=True,
    )

    question_id = Column(
        "question_id",
        Integer,
        ForeignKey(Question.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    order = Column(
        "order",
        Integer(),
        nullable=False,
    )

    body = Column(
        "body",
        UnicodeText(),
        nullable=False,
    )


class ChoiceProfileWeight(Base):
    __tablename__ = "choice_profile_matrix"

    choice_id = Column(
        "choice_id",
        Integer,
        ForeignKey(Choice.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    profile_id = Column(
        "profile_id",
        Integer,
        ForeignKey(Profile.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        primary_key=True,
    )

    weight = Column(
        "weight",
        Float(),
        nullable=False,
    )

    @classmethod
    def upsert(cls, session, choice_id, profile_id, weight):
        session.flush()
        last = 2
        for i in range(last + 1):
            try:
                instance = session.query(
                    cls,
                ).filter(
                    cls.choice_id == choice_id,
                    cls.profile_id == profile_id,
                ).one()
            except sqlalchemy.orm.exc.NoResultFound:
                try:
                    instance = cls()
                    instance.choice_id = choice_id
                    instance.profile_id = profile_id
                    instance.weight = weight
                    session.add(instance)
                    session.flush()
                    return instance
                except sqlalchemy.exc.IntegrityError:
                    if last == i:
                        raise
            else:
                instance.weight = weight
                session.add(instance)
                return instance
        raise RuntimeError(
            "failed to execute upsert for unknown reason"
        )


class Participant(Base):
    __tablename__ = "participant"

    id_ = Column(
        "id",
        IDType,
        primary_key=True,
        nullable=False,
    )

    qid = Column(
        "qid",
        IDType,
        ForeignKey(Questionnaire.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    name = Column(
        "name",
        Unicode(128),
        nullable=False,
    )


class Answer(Base):
    __tablename__ = "answer"

    participant_id = Column(
        "participant_id",
        IDType,
        ForeignKey(Participant.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    choice_id = Column(
        "choice_id",
        Integer,
        ForeignKey(Choice.id_,
                   ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )
