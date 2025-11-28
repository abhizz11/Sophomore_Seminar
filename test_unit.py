import unittest
from app import app, db, User, Group, Expense, ExpenseSplit, _settle_splits_helper, allowed_file
from flask_bcrypt import Bcrypt

class SharePayUnitTests(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory DB
        app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for easier testing
        
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.bcrypt = Bcrypt(app)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation_and_hashing(self):
        """Test that users are created and passwords are hashed correctly."""
        password = "securepassword"
        hashed = self.bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username="testuser", email="test@example.com", password=hashed)
        db.session.add(user)
        db.session.commit()

        retrieved_user = User.query.filter_by(username="testuser").first()
        self.assertIsNotNone(retrieved_user)
        self.assertNotEqual(retrieved_user.password, password) # Should be hashed
        self.assertTrue(self.bcrypt.check_password_hash(retrieved_user.password, password))

    def test_allowed_file(self):
        """Test the file extension checker."""
        self.assertTrue(allowed_file("receipt.png"))
        self.assertTrue(allowed_file("document.pdf"))
        self.assertTrue(allowed_file("image.JPG"))
        self.assertFalse(allowed_file("script.exe"))
        self.assertFalse(allowed_file("image")) # No extension

    def test_settle_splits_helper(self):
        """Test the logic for splitting expense records during settlement."""
        # Setup: User owes 50. We want to settle 20.
        # We need mock objects that act like ExpenseSplit
        class MockSplit:
            def __init__(self, amount):
                self.amount = amount
                self.is_settled = False
                self.expense_id = 1
                self.user_id = 2
                self.receipt_image = None
        
        split1 = MockSplit(50.0)
        splits_list = [split1]

        # Call the helper directly
        # Note: This function normally adds to db.session, so we need to mock db.session.add 
        # or rely on the fact that it might fail if we don't have a real DB context for the new split.
        # Since we are using an in-memory DB, we can actually create real objects.
        
        user = User(username="u1", email="e1", password="pw")
        db.session.add(user)
        db.session.commit()

        # We need a dummy expense to link to
        # (Skipping full foreign key setup for pure unit test logic if possible, 
        # but SQLAlchemy requires valid FKs usually. We will use the integration test for full DB logic,
        # here we just test the math if we can, but _settle_splits_helper interacts with DB.)
        
        # ACTUALLY, _settle_splits_helper creates a new ExpenseSplit object which requires a DB session.
        # Let's verify the logic by creating a Real split.
        group = Group(name="g1", tag="t1")
        payer = User(username="p1", email="ep1", password="pw")
        db.session.add_all([group, payer])
        db.session.commit()
        
        expense = Expense(description="test", amount=100, payer_id=payer.id, group_id=group.id)
        db.session.add(expense)
        db.session.commit()

        real_split = ExpenseSplit(expense_id=expense.id, user_id=user.id, amount=50.0, is_settled=False)
        db.session.add(real_split)
        db.session.commit()

        # Action: Settle 20.00
        _settle_splits_helper([real_split], 20.0)
        
        # Assert
        # The original split should be modified to 20.0 (settled)
        # A new split should be created for 30.0 (unsettled)
        self.assertTrue(real_split.is_settled)
        self.assertAlmostEqual(real_split.amount, 20.0)

        # Check for the new remainder split
        all_splits = ExpenseSplit.query.filter_by(user_id=user.id).all()
        self.assertEqual(len(all_splits), 2)
        
        remainder_split = [s for s in all_splits if s.id != real_split.id][0]
        self.assertFalse(remainder_split.is_settled)
        self.assertAlmostEqual(remainder_split.amount, 30.0)

if __name__ == '__main__':
    unittest.main()