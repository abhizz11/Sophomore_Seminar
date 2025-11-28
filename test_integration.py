import unittest
from app import app, db, User, Group, Expense, ExpenseSplit
from flask_bcrypt import Bcrypt

class SharePayIntegrationTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False 
        
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        self.bcrypt = Bcrypt(app)
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_user(self, username, email, password):
        hashed = self.bcrypt.generate_password_hash(password).decode('utf-8')
        u = User(username=username, email=email, password=hashed)
        db.session.add(u)
        db.session.commit()
        return u

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def test_full_user_flow(self):
        """Test Register -> Create Group -> Add Expense"""
        
        # 1. Register
        resp = self.client.post('/register', data=dict(
            username='alice',
            email='alice@example.com',
            password='password123'
        ), follow_redirects=True)
        self.assertIn(b'Your Dashboard', resp.data)

        # 2. Create Group
        resp = self.client.post('/create_group', data=dict(
            group_name='Trip to Vegas',
            members=''
        ), follow_redirects=True)
        self.assertIn(b'Trip to Vegas', resp.data)
        
        # Get Group ID
        group = Group.query.filter_by(name='Trip to Vegas').first()
        self.assertIsNotNone(group)

        # 3. Add Expense
        # Alice pays 100, split equally (defaults to just her if no other members, 
        # but let's add a member first to make it interesting)
        
        # Create Bob and add to group
        bob = self.create_user('bob', 'bob@example.com', 'password123')
        group.members.append(bob)
        db.session.commit()
        
        alice = User.query.filter_by(username='alice').first()

        resp = self.client.post('/add_expense', data=dict(
            group_id=group.id,
            description='Dinner',
            amount='100',
            paid_by=alice.id,
            split_type='equal',
            participants=[alice.id, bob.id] # Both participate
        ), follow_redirects=True)
        
        self.assertIn(b'Dinner', resp.data)
        self.assertIn(b'100.00', resp.data)

        # Check Splits in DB
        # Alice paid 100. Split equal. Alice owes 50 (to herself, ignored). Bob owes 50.
        split = ExpenseSplit.query.filter_by(user_id=bob.id).first()
        self.assertIsNotNone(split)
        self.assertEqual(split.amount, 50.0)

    def test_security_check_reset_flow(self):
        """Test the Identify User and Verify Identity routes."""
        
        # Setup Data
        # User: John
        # Group: Hiking
        # Friend: Jane (in Hiking group)
        # Transaction: John paid 50.0
        
        john = self.create_user('john', 'john@example.com', 'oldpass')
        jane = self.create_user('jane', 'jane@example.com', 'janepass')
        
        group = Group(name='Hiking', tag='hike-1')
        group.members.append(john)
        group.members.append(jane)
        db.session.add(group)
        db.session.commit()
        
        # Add a transaction for John (he paid 50)
        exp = Expense(description='Snacks', amount=50.0, payer_id=john.id, group_id=group.id)
        db.session.add(exp)
        db.session.commit()

        # Step 1: Identify User
        resp = self.client.post('/identify_user', data={'username': 'john'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Security Check', resp.data)
        self.assertIn(b'To verify your identity', resp.data)

        # Step 2: Verify Reset (Success Case)
        resp = self.client.post('/verify_reset', data=dict(
            username='john',
            email='john@example.com',
            group_name='Hiking',
            friend_name='jane',
            amount_1='50.0', # Matches the expense he paid
            amount_2='',
            amount_3='',
            password='newsecurepassword'
        ), follow_redirects=True)
        
        self.assertIn(b'Identity Verified!', resp.data)
        
        # Verify password changed
        john = User.query.filter_by(username='john').first()
        self.assertTrue(self.bcrypt.check_password_hash(john.password, 'newsecurepassword'))

    def test_security_check_failure(self):
        """Test failure when wrong amount is entered."""
        john = self.create_user('john', 'john@example.com', 'oldpass')
        group = Group(name='Hiking', tag='hike-1')
        group.members.append(john)
        
        # Add a friend so that part passes
        jane = self.create_user('jane', 'jane@example.com', 'janepass')
        group.members.append(jane)
        db.session.add(group)
        db.session.commit()

        # No transactions exist for John

        resp = self.client.post('/verify_reset', data=dict(
            username='john',
            email='john@example.com',
            group_name='Hiking',
            friend_name='jane',
            amount_1='9999.00', # Wrong amount
            password='newpass'
        ), follow_redirects=True)

        self.assertIn(b'Security check failed', resp.data)
        
        # Password should NOT change
        john = User.query.filter_by(username='john').first()
        self.assertTrue(self.bcrypt.check_password_hash(john.password, 'oldpass'))

if __name__ == '__main__':
    unittest.main()