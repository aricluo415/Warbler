"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


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


class MessageViewTestCase(TestCase):
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

        self.msg = Message(
                text="message",
                user_id=self.testuser.id
            )

        db.session.add(self.msg)
        db.session.commit()

    def test_add_message(self):
        """Can you add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_2.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msgs = Message.query.all()
            self.assertEqual(len(msgs), 2)

    def test_add_message_no_login(self):
        """Can you add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new",
                          data={"text": "Hello"},
                          follow_redirects=True)
            html = resp.get_data(as_text=True)

            msg = Message.query.all()
            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(1, len(msg))
            self.assertIn('<li><a href="/login">Log in</a></li>', html)

    def test_delete_message(self):
        """Can you delete a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            msg = Message.query.first()

            c.post(f"/messages/{msg.id}/delete")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msgs = Message.query.all()
            self.assertEqual(1, len(msgs))

    def test_get_message(self):
        """Can you get a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            msg = Message.query.one()

            resp = c.get(f"/messages/{msg.id}")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 200)

            self.assertEqual("message", msg.text)

    def test_like_message(self):
        """Can you like a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_2.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            msg = Message.query.one()
            resp = c.post(f"/messages/{msg.id}/like")

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            self.assertEqual(len(msg.liked_by), 1)
            self.assertEqual(self.testuser_2.id, msg.liked_by[0].id)
