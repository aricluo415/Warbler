import os

from flask import Flask, render_template, request
from flask import flash, redirect, session, g, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from functools import wraps

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Likes, DirectMessage
from sqlalchemy import or_, and_

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

db.create_all()


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash("unauthorized access", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect(url_for('homepage'))

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Handle logout of user."""
    user_id = session[CURR_USER_KEY]
    user = User.query.get(user_id)
    do_logout()
    flash(f"Successful Logout! Goodbye {user.username}!", "success")

    return redirect(url_for("homepage"))

##############################################################################
# General user routes:


@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)


@app.route('/users/<int:user_id>/likes')
@login_required
def show_likes(user_id):
    """Show list of people this user is following."""

    user = User.query.get_or_404(user_id)
    messages = user.liked_messages
    return render_template('users/show_liked.html',
                           user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
@login_required
def show_following(user_id):
    """Show list of people this user is following."""

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
@login_required
def users_followers(user_id):
    """Show list of followers of this user."""

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
@login_required
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(url_for('show_following', user_id=g.user.id))


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
@login_required
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(url_for('show_following', user_id=g.user.id))


@app.route('/users/profile', methods=["GET", "POST"])
@login_required
def profile():
    """Update profile for current user."""

    form = UserEditForm(obj=g.user)

    if form.validate_on_submit():
        user = User.authenticate(g.user.username,
                                 form.password.data)
        if not user:
            flash('Invalid Password', 'danger')
            return redirect(url_for('profile'))

        user.username = form.username.data
        user.email = form.email.data
        user.image_url = form.image_url.data
        user.header_image_url = form.header_image_url.data
        user.bio = form.bio.data

        db.session.commit()
        return redirect(url_for('users_show', user_id=g.user.id))

    return render_template("users/edit.html", form=form)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    do_logout()

    db.session.delete(g.user)
    db.session.commit()
    flash("Account Successfully Deleted", "success")

    return redirect(url_for('homepage'))


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
@login_required
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(url_for('users_show', user_id=g.user.id))

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
@login_required
def messages_destroy(message_id):
    """Delete a message."""

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(url_for('users_show', user_id=g.user.id))


@app.route('/messages/<int:message_id>/like', methods=["POST"])
@login_required
def messages_like(message_id):
    """Likes a message."""

    msg = Message.query.get_or_404(message_id)
    if msg.user_id != g.user.id:
        g.user.liked_messages.append(msg)

        db.session.commit()

    route = request.referrer

    return redirect(f'{route}')


@app.route('/messages/<int:message_id>/unlike', methods=["POST"])
@login_required
def messages_unlike(message_id):
    """Likes a message."""

    msg = Message.query.get_or_404(message_id)
    if msg.user_id != g.user.id:
        g.user.liked_messages.remove(msg)

        db.session.commit()

    route = request.referrer

    return redirect(f'{route}')


@app.route('/direct_messages', methods=["GET"])
@login_required
def direct_message():

    msgs = DirectMessage.query.filter(
        or_(
        DirectMessage.user_to_id == g.user.id,
        DirectMessage.user_from_id == g.user.id)).all()

    dm_list = []
    for msg in msgs:
        if msg.user_to_id == g.user.id:
            dm_list.append(msg.user_from_id)
        else:
            dm_list.append(msg.user_to_id)

    users = User.query.filter(User.id.in_(dm_list)).all()

    return render_template("direct_messages/all_dms.html", dm_list=users, user=g.user)


@app.route('/direct_messages/<int:other_user_id>', methods=["GET", "POST"])
@login_required
def direct_messages(other_user_id):
    """ Shows conversation with other user """

    form = MessageForm()

    msgs = DirectMessage.query.filter(
        or_(
        (and_(
           DirectMessage.user_to_id == g.user.id,
           DirectMessage.user_from_id == other_user_id)),
        (and_(
           DirectMessage.user_to_id == other_user_id,
           DirectMessage.user_from_id == g.user.id))
    )).order_by(DirectMessage.timestamp.desc()).all()

    if form.validate_on_submit():
        new_dm = g.user.send_dm(other_user=other_user_id, msg=form.text.data)
        db.session.commit()

        route = request.referrer

        return redirect(f'{route}')


    return render_template(
        "direct_messages/show_dm.html",
        messages=msgs,
        form=form,
        user=g.user
    )
##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        following = [user_being_followed.id for user_being_followed in g.user.following]
        following.append(g.user.id)
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')
##############################################################################
# Admin Pages


@app.route('/admin')
def admin():
    """ show all users with delete and edit button"""
    if not g.user.admin:
        flash("You're not an admin!", "danger")
        return redirect('/')

    users = User.query.all()

    return render_template('admin/all_users.html', users=users)


@app.route('/admin/users/<int:user_id>')
def admin_show_user(user_id):
    """ show all messages related by user_id"""
    if not g.user.admin:
        flash("You're not an admin!", "danger")
        return redirect('/')

    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)


@app.route('/admin/users/<int:user_id>/messages/<int:message_id>')
def admin_show_message(user_id, message_id):
    """ show all messages related by user_id"""
    if not g.user.admin:
        flash("You're not an admin!", "danger")
        return redirect('/')

    message = Message.query.get_or_404(message_id)
    return render_template('admin/message.html', message=message)


@app.route('/admin/edit/users/<int:user_id>', methods=["GET","POST"])
def admin_edit_user(user_id):
    """ edit user profile, allow making user admin """
    if not g.user.admin:
        flash("You're not an admin!", "danger")
        return redirect('/')

    user_to_edit = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user_to_edit)

    if form.validate_on_submit():
        form.populate_obj(user_to_edit)
        db.session.commit()
        return redirect(url_for('admin_show_user', user_id=user_to_edit.id))

    return render_template('admin/edit_user.html', user=user_to_edit, form=form)


@app.route('/admin/delete/users/<int:user_id>', methods=["POST"])
def admin_delete_user(user_id):
    """ Admin delete user profile """
    if not g.user.admin:
        return redirect('/')

    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/delete/messages/<int:message_id>', methods=["POST"])
def admin_delete_message(message_id):
    """ Admin delete user message """
    if not g.user.admin:
        return redirect('/')

    message_to_delete = Message.query.get_or_404(message_id)
    db.session.delete(message_to_delete)
    db.session.commit()
    return redirect(url_for('admin_show_user', user_id=message_to_delete.user_id))

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
