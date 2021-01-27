"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()
        Likes.query.delete()

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )
        self.user = u
        db.session.add(u)
        db.session.commit()

        self.client = app.test_client()

    def test_message_model(self):
        """Does basic model work?"""

        m = Message(
            text="message_test",
            user_id=self.user.id
        )
        db.session.add(m)
        db.session.commit()
        # Message should have a user owner & no likes
        self.assertEqual(m.user_id, self.user.id)
        self.assertEqual(len(m.liked_by), 0)

    def test_message_like(self):
        """Test Message Liked_by"""
        m = Message(
            text="message_test",
            user_id=self.user.id
        )
        db.session.add(m)
        db.session.commit()

        m.liked_by.append(self.user)
        db.session.commit()
        self.assertIn(self.user_id, m.liked_by[0].id)
        self.assertIn(m, self.user.liked_messages)
