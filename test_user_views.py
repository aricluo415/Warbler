"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_2 = User.signup(username="testuser2",
                                      email="test2@test.com",
                                      password="testuser",
                                      image_url=None)

        db.session.add_all([self.testuser, self.testuser_2])
        db.session.commit()

    def test_add_user(self):
        """Can you add a user?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            # with c.session_transaction() as sess:
            #     sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/signup", data={"username": "bestuser",
                                           "email": "best@email.com",
                                           "password": "password",
                                           "image_url": None})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            users = User.query.all()
            self.assertEqual(len(users), 3)

    def test_login(self):
        """Can you login a user?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/login",
                          data={
                              "username": "testuser",
                              "password": "testuser"
                          },
                          follow_redirects=True)
            html = resp.get_data(as_text=True)

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)
            self.assertIn('<li><a href="/logout">Log out</a></li>', html)

    def test_add_follower(self):
        """Can you follow a user?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            second = User.query.filter(User.id != self.testuser.id).first()

            resp = c.post(f"/users/follow/{second.id}")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(self.testuser.id, second.followers[0].id)
            self.assertNotIn(self.testuser, second.following)

    def test_remove_follow(self):
        """Can you remove a followed user?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            first = User.query.filter(User.id == self.testuser.id).first()
            second = User.query.filter(User.id != self.testuser.id).first()
            first.following.append(second)
            db.session.commit()

            resp = c.post(f"/users/stop-following/{second.id}")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(len(first.following), 0)
