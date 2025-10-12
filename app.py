from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

# Mail configuration (simulation)
app.config['TESTING'] = True # This will prevent emails from being sent
mail = Mail(app)



# Association table for many-to-many relationship between user and groups
members = db.Table('members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True)
)

# Define User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'
    
    def reset_password(self, new_password):
        self.password = new_password
        db.session.commit()

# Define Group Model
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    members = db.relationship('User', secondary=members, lazy='subquery', backref=db.backref('groups', lazy=True))

    def __repr__(self):
        return f'<Group {self.name}>'

# Define Expense Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable = False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # The user who paid the expense
    payer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Linking it to the group
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)


    def __repr__(self):
        return f'<Expense {self.description} - {self.amount}>'


# This is the route to the homepage
@app.route('/')
def index():
    return render_template('index.html')

# This is the route to register a new user
@app.route('/register', methods=['POST'])
def register():
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

    # Create a new database entry
    existing_user = User.query.filter_by(username=username).first()
    existing_email = User.query.filter_by(email=email).first()

    if existing_user or existing_email:
        return 'User or Email already exists!'

    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return f'Created a user with name: {username}'


# This is the route to login a user
@app.route('/login', methods=['POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return f'Logged in as: {username}'
    else:
        return 'Invalid credentials!'

@app.route('/forget_password', methods=['POST'])
def forget_password():
    if request.method == "POST":
        email = request.form.get('email')

    user = User.query.filter_by(email=email).first()
    if user:
        msg = Message(
            'Hello',
            sender = 'sharepay@no-reply.com',
            recipients = [email]
        )
        msg.body = 'Click the link to reset your password: http://example.com/reset_password'
        
        # In testing mode, the email is not sent but captured.
        # We can access it to show the content.
        with mail.record_messages() as outbox:
            mail.send(msg)
            # Return the content of the email body
            if outbox:
                return f"EMAIL: {outbox[0].body}"
            else:
                return "Failed to simulate email."

    else:
        return 'Email not found!'



if __name__ == '__main__':
    app.run(debug=True)

