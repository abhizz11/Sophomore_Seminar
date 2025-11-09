from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
import random
import re

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret_in_production"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
# Upload configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    tag = db.Column(db.String(200), unique=True, nullable=True)
    members = db.relationship('User', secondary=members, lazy='subquery', backref=db.backref('groups', lazy=True))

    def __repr__(self):
        return f'<Group {self.name}>'


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable = False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(300), nullable=True)
    receipt_image = db.Column(db.String(300), nullable=True)

    # The user who paid the expense
    payer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Linking it to the group
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)


    def __repr__(self):
        return f'<Expense {self.description} - {self.amount}>'

class ExpenseSplit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_settled = db.Column(db.Boolean, default=False)
    receipt_image = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<ExpenseSplit for User {self.user_id} - Amount: {self.amount}>'


# This is the route to the homepage
@app.route('/')
def index():
    # If user already logged in, redirect to dashboard
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('index.html')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/users')
def user_list():
    users = db.session.execute(db.select(User).order_by(User.username)).scalars()
    groups = db.session.execute(db.select(Group).order_by(Group.name)).scalars()
    
    users_list = [{'id': user.id, 'username': user.username, 'email': user.email, 'password': user.password} for user in users]
    groups_list = [{'id': group.id, 'name': group.name, 'members': [member.username for member in group.members]} for group in groups]
    
    return jsonify({'users': users_list, 'groups': groups_list})

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
    # Log the user in by setting the session
    session['user_id'] = new_user.id
    session['username'] = new_user.username
    return redirect(url_for('dashboard'))


# This is the route to login a user
@app.route('/login', methods=['POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

    user = User.query.filter_by(username=username, password=password).first()
    if user:
        # Set session and redirect to dashboard
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    else:
        return 'Invalid credentials!'


# This forget password route is not currently working
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

# This reset password will help us reset the password later
@app.route('/reset_password', methods=['POST'])
def reset_token():
    #This is a placeholder for reset token 
    return 'Not implemented yet', 501


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Show groups the user belongs to and outstanding expense splits
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    # Groups the user belongs to
    groups = user.groups if user else []

    # Outstanding splits for the user (is_settled = False)
    splits = db.session.execute(
        db.select(ExpenseSplit).where(ExpenseSplit.user_id == user_id, ExpenseSplit.is_settled == False)
    ).scalars()

    # Build a structure for template
    groups_list = []
    for g in groups:
        groups_list.append({
            'id': g.id,
            'name': g.name,
            'tag': g.tag,
            'members': [{'id': m.id, 'username': m.username, 'email': m.email} for m in g.members]
        })

    splits_list = []
    for s in splits:
        expense = Expense.query.get(s.expense_id)
        payer = User.query.get(expense.payer_id) if expense else None
        splits_list.append({
            'split_id': s.id,
            'expense_description': expense.description if expense else '',
            'amount': s.amount,
            'group_id': expense.group_id if expense else None,
            'payer': payer.username if payer else None,
            'is_settled': s.is_settled
        })

    # Settled splits (these will be hidden by default in the UI and revealed by a button)
    settled_splits_list = []
    settled_splits = db.session.execute(
        db.select(ExpenseSplit).where(ExpenseSplit.user_id == user_id, ExpenseSplit.is_settled == True)
    ).scalars()
    for s in settled_splits:
        expense = Expense.query.get(s.expense_id)
        payer = User.query.get(expense.payer_id) if expense else None
        settled_splits_list.append({
            'split_id': s.id,
            'expense_description': expense.description if expense else '',
            'amount': s.amount,
            'group_id': expense.group_id if expense else None,
            'payer': payer.username if payer else None,
            'date': expense.date if expense else None
        })

    # Also fetch recent expenses for the groups the user belongs to
    group_ids = [g['id'] for g in groups_list]
    expenses_list = []
    if group_ids:
        expenses = db.session.execute(
            db.select(Expense).where(Expense.group_id.in_(group_ids)).order_by(Expense.date.desc())
        ).scalars()
        for e in expenses:
            payer = User.query.get(e.payer_id)
            expenses_list.append({
                'id': e.id,
                'description': e.description,
                'location': e.location if hasattr(e, 'location') else None,
                'amount': e.amount,
                'date': e.date,
                'group_id': e.group_id,
                'payer_id': e.payer_id,
                'payer': payer.username if payer else None,
                'can_edit': (e.payer_id == user_id)
            })

    return render_template('dashboard.html', username=session.get('username'), groups=groups_list, splits=splits_list, expenses=expenses_list, settled_splits=settled_splits_list)


@app.route('/edit_expense', methods=['POST'])
@login_required
def edit_expense():
    expense_id = request.form.get('expense_id')
    if not expense_id:
        return 'expense_id required', 400
    expense = Expense.query.get(expense_id)
    if not expense:
        return 'Expense not found', 404
    # Only payer can edit
    if expense.payer_id != session.get('user_id'):
        return 'Not authorized to edit this expense', 403

    # Prevent editing if any split is already settled
    settled_any = ExpenseSplit.query.filter_by(expense_id=expense.id, is_settled=True).first()
    if settled_any:
        flash('Cannot edit this expense because one or more splits are already settled.')
        return redirect(url_for('dashboard'))

    description = request.form.get('description')
    amount = request.form.get('amount')
    date = request.form.get('date')
    location = request.form.get('location')

    amount_changed = False
    if description is not None:
        expense.description = description
    if amount:
        try:
            new_amount = float(amount)
        except ValueError:
            return 'Invalid amount', 400
        if abs(new_amount - expense.amount) > 1e-9:
            amount_changed = True
            expense.amount = new_amount
    if date:
        try:
            expense.date = datetime.fromisoformat(date)
        except Exception:
            # ignore invalid date formatting and leave unchanged
            pass
    # handle optional receipt replacement
    file = request.files.get('receipt')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{session.get('user_id')}_{int(datetime.utcnow().timestamp())}_{file.filename}")
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        expense.receipt_image = filename
    if location is not None:
        # set or clear location
        expense.location = location or None

    # If amount changed, recompute splits for this expense equally across group members
    if amount_changed:
        group = Group.query.get(expense.group_id)
        members = group.members if group else []
        if members:
            per_person_share = float(expense.amount) / len(members)
            splits = ExpenseSplit.query.filter_by(expense_id=expense.id).all()
            for s in splits:
                s.amount = per_person_share

    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/join_group', methods=['POST'])
@login_required
def join_group():
    tag = request.form.get('group_tag')
    if not tag:
        return 'group_tag required', 400
    group = Group.query.filter_by(tag=tag.strip()).first()
    if not group:
        return 'Group not found', 404
    user = User.query.get(session.get('user_id'))
    if user in group.members:
        flash('You are already a member of this group.')
        return redirect(url_for('dashboard'))
    group.members.append(user)
    db.session.commit()
    flash(f'Joined group {group.name}')
    return redirect(url_for('dashboard'))


@app.route('/leave_group', methods=['POST'])
@login_required
def leave_group():
    group_id = request.form.get('group_id')
    if not group_id:
        return 'group_id required', 400
    group = Group.query.get(group_id)
    if not group:
        return 'Group not found', 404
    user = User.query.get(session.get('user_id'))
    if user not in group.members:
        flash('You are not a member of this group.')
        return redirect(url_for('dashboard'))
    group.members.remove(user)
    db.session.commit()
    flash(f'Left group {group.name}')
    return redirect(url_for('dashboard'))


@app.route('/delete_expense', methods=['POST'])
@login_required
def delete_expense():
    expense_id = request.form.get('expense_id')
    if not expense_id:
        return 'expense_id required', 400
    expense = Expense.query.get(expense_id)
    if not expense:
        return 'Expense not found', 404
    # Only payer can delete
    if expense.payer_id != session.get('user_id'):
        return 'Not authorized to delete this expense', 403

    # delete splits first
    ExpenseSplit.query.filter_by(expense_id=expense.id).delete()
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/settle_split', methods=['POST'])
@login_required
def settle_split():
    split_id = request.form.get('split_id')
    if not split_id:
        return 'split_id required', 400
    split = ExpenseSplit.query.get(split_id)
    if not split:
        return 'Split not found', 404
    if split.user_id != session.get('user_id'):
        return 'Not authorized', 403
    # Optional receipt upload when settling
    file = request.files.get('receipt')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{session.get('user_id')}_{int(datetime.utcnow().timestamp())}_{file.filename}")
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        split.receipt_image = filename
    split.is_settled = True
    db.session.commit()
    return redirect(url_for('dashboard'))

# This route will help us to create a group we need groups to split expenses
@app.route('/create_group', methods=['POST'])
def create_group():
    if request.method == "POST":
        group_name = request.form.get('group_name')
        members_emails_str = request.form.get('members')

    if not group_name:
        return 'Group name is required!', 400

    existing_group = Group.query.filter_by(name=group_name).first()
    if existing_group:
        return 'Group name already exists!', 409

    # Generate a simple unique tag: slug + random 4-digit number
    def slugify(s):
        return re.sub(r"[^a-z0-9]+", '-', s.lower()).strip('-')

    base = slugify(group_name)
    tag = f"{base}-{random.randint(1000,9999)}"
    # ensure unique
    while Group.query.filter_by(tag=tag).first():
        tag = f"{base}-{random.randint(1000,9999)}"

    new_group = Group(name=group_name, tag=tag)
    
    if members_emails_str:
        members_emails = members_emails_str.split(',')
        for email in members_emails:
            user = User.query.filter_by(email=email.strip()).first()
            if user:
                new_group.members.append(user)
    
    db.session.add(new_group)
    db.session.commit()
    return redirect(url_for('dashboard'))



@app.route('/add_expense', methods=['POST'])
def add_expense():
    if request.method == "POST":
        group_name = request.form.get('group_name_expense')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        paid_by = request.form.get('paid_by')
        date = request.form.get('date') #Optional
        location = request.form.get('location')
        # Find the group by name
        group = Group.query.filter_by(name=group_name).first()
        if not group:
            return 'Group not found!', 404

        # Get list of user objects in the group
        members = group.members  # list of User objects
        if not members or len(members) == 0:
            return 'Group has no members to split the expense!', 400

        # Validate and find payer (expecting an email)
        payer = User.query.filter_by(email=paid_by).first()
        if not payer:
            return 'Payer (email) not found!', 400

        try:
            per_person_share = float(amount) / len(members)
        except (ValueError, ZeroDivisionError):
            return 'Invalid amount or division by zero.', 400

        # Create expense and persist to get an id
        expense_date = None
        if date:
            try:
                expense_date = datetime.fromisoformat(date)
            except Exception:
                expense_date = datetime.utcnow()
        else:
            expense_date = datetime.utcnow()

        expense = Expense(
            group_id=group.id,
            description=description,
            amount=amount,
            location=location,
            payer_id=payer.id,
            date=expense_date
        )

        db.session.add(expense)
        # flush so expense.id is available for splits before commit
        db.session.flush()

        # Handle optional receipt upload for the expense
        file = request.files.get('receipt')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{payer.id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            # Store relative path under uploads folder
            expense.receipt_image = filename

        # Create splits for each group member
        for member in members:
            if member.id == payer.id:
                # Payer does not owe to themselves
                continue
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=member.id,
                amount=per_person_share,
            )
            db.session.add(split)

        db.session.commit()
        return redirect(url_for('dashboard'))


if __name__ == '__main__':
    # Ensure database tables are created inside the application context
    with app.app_context():
        db.create_all()
    app.run(debug=True)

