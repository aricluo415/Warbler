"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


# One DirectMessage Per Friend
# DirectMessage.msgs -> [(me:hi),(you:whats up), ]


class DirectMessage(db.Model):
    """Connection of a user_from <-> user_to."""

    __tablename__ = 'direct_messages'

    id = db.Column(db.Integer, primary_key=True)

    user_from_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade")
    )

    user_to_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade")
    )

    msg = db.Column(db.Text)

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow()
    )

# app.py -> text_msg = MsgWithinDM("HELLO", creator = g.user.id)
# dm =DirectMessage.query.get(users_from_id = g.user.id, user_to_id = other_user)
# dm.msg.append(text_msg)

# g.user.dm.msg[0] g.user.dm[1]


class Follows(db.Model):
    """Connection of a follower <-> followed_user."""

    __tablename__ = 'follows'

    user_being_followed_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    user_following_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )


class Likes(db.Model):
    """ Connection of user <-> liked messages """

    __tablename__ = 'likes'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete="cascade"),
        primary_key=True,
    )


class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    image_url = db.Column(
        db.Text,
        default="/static/images/default-pic.png",
    )

    header_image_url = db.Column(
        db.Text,
        default="/static/images/warbler-hero.jpg"
    )

    bio = db.Column(
        db.Text,
    )

    location = db.Column(
        db.Text,
    )

    password = db.Column(
        db.Text,
        nullable=False,
    )

    admin = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    liked_messages = db.relationship('Message', secondary='likes')

    messages = db.relationship('Message', cascade="all, delete", passive_deletes=True, order_by='Message.timestamp.desc()')
    """
    relationship.primaryjoin argument, as well as the relationship.
    secondaryjoin argument in the case when a “secondary” table is used.
    """
    # SELECT u.username, f.user_being_followed_id, f.user_following_id FROM users AS u
    # JOIN follows AS f
    # ON f.user_following_id = 179
    # JOIN user AS u2
    # ON f.user_being_followed_id = u.id;

    followers = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_being_followed_id == id),
        secondaryjoin=(Follows.user_following_id == id)
    )

    # SELECT u.username, f.user_being_followed_id, f.user_following_id FROM users AS u
    # JOIN follows AS f
    # ON f.user_being_followed_id = 179
    # JOIN user AS u2
    # ON f.user_following_id = u.id;
    following = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_following_id == id),
        secondaryjoin=(Follows.user_being_followed_id == id)
    )



    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    def is_followed_by(self, other_user):
        """Is this user followed by `other_user`?"""

        found_user_list = [user for user in self.followers if user == other_user]
        return len(found_user_list) == 1

    def is_following(self, other_user):
        """Is this user following `other_use`?"""

        found_user_list = [user for user in self.following if user == other_user]
        return len(found_user_list) == 1

    def send_dm(self, other_user, msg):
        new_dm = DirectMessage(user_from_id=self.id, user_to_id=other_user, msg=msg)
        db.session.add(new_dm)
        return new_dm

    @classmethod
    def signup(cls, username, email, password, image_url):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Message(db.Model):
    """An individual message ("warble")."""

    __tablename__ = 'messages'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    text = db.Column(
        db.String(140),
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False,
    )

    user = db.relationship('User')

    liked_by = db.relationship('User', secondary='likes')


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)


# my message with to-user you
# dm/your_user_id
# your message (message.your_user_id) with to-user me
# automatically user.messages.filter(to_user = me)
# message with to-user none

# SELECT * FROM messages AS m
# JOIN users
# ON m.user_to_id = 301 and m.user_from_id = 302

# sent messages
# SELECT dm.text, user_to_id, user_from_id FROM direct_messages AS dm
# WHERE dm.user_from_id = aric AND dm.user_to_id = mack

# SELECT * FROM direct_message as dm
# JOIN users as u1
# ON u1.id = direct_messsage.user_from_id
# JOIN users as u2
# ON u2.id = direct_messsage.user_to_id