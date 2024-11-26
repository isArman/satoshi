from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# تعریف login_required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ابتدا وارد حساب کاربری خود شوید', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_type = db.Column(db.String(10), nullable=False)  # 'buy' یا 'sell'
    amount = db.Column(db.Integer, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)  # وضعیت تأیید سفارش
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # کاربری که سفارش را تأیید کرده است
    user = db.relationship('User', backref='orders', foreign_keys=[user_id])
    approver = db.relationship('User', backref='approved_orders', foreign_keys=[approved_by])

# Database model for users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=True)
    card_number = db.Column(db.String(20), nullable=True)
    lightning_wallet = db.Column(db.String(255), nullable=True)
    telegram_id = db.Column(db.String(150), nullable=True)

    def is_profile_complete(self):
        # بررسی اینکه آیا تمام فیلدهای پروفایل پر شده‌اند
        return all([self.name, self.card_number, self.lightning_wallet, self.telegram_id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user = db.relationship('User', backref='notifications', lazy=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # ذخیره شناسه کاربر در session
            flash('با موفقیت وارد شدید', 'success')
            return redirect(url_for('home', user_id=user.id))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('این نام کاربری قبلاً استفاده شده است', 'warning')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('حساب کاربری با موفقیت ایجاد شد', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form['name']
        user.card_number = request.form['card_number']
        user.lightning_wallet = request.form['lightning_wallet']
        user.telegram_id = request.form['telegram_id']
        db.session.commit()
        flash('پروفایل با موفقیت به‌روزرسانی شد', 'success')
    
    return render_template('profile.html', user=user)


@app.route('/home')
@login_required
def home():
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    orders = Order.query.all()
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.timestamp.desc()).all()
    return render_template('home.html', user=user, orders=orders, notifications=notifications)


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # حذف user_id از session
    flash('با موفقیت از حساب خارج شدید', 'success')
    return redirect(url_for('login'))

@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    # بررسی کامل بودن پروفایل
    if not user.is_profile_complete():
        flash('لطفاً ابتدا پروفایل خود را تکمیل کنید.', 'warning')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        order_type = request.form['order_type']
        amount = int(request.form['amount'])

        # بررسی محدودیت تعداد ساتوشی
        if amount < 1000 or amount > 10000:
            flash('تعداد ساتوشی باید بین ۱۰۰۰ تا ۱۰۰۰۰ باشد.', 'danger')
            return redirect(url_for('order'))

        # ایجاد سفارش
        new_order = Order(user_id=user_id, order_type=order_type, amount=amount)
        db.session.add(new_order)
        db.session.commit()

        # ایجاد گزارش
        notification = Notification(user_id=user_id, message=f"سفارش {order_type} به مقدار {amount} ساتوشی ثبت شد.")
        db.session.add(notification)
        db.session.commit()

        flash(f'سفارش شما با موفقیت ثبت شد: نوع {order_type}، تعداد {amount} ساتوشی', 'success')
        return redirect(url_for('home'))
    return render_template('order.html')


@app.route('/delete_order/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    user_id = session['user_id']
    order = Order.query.get_or_404(order_id)

    # بررسی اینکه آیا سفارش متعلق به کاربر فعلی است
    if order.user_id != user_id:
        flash('شما اجازه حذف این سفارش را ندارید.', 'danger')
        return redirect(url_for('home'))

    # ایجاد گزارش حذف سفارش
    notification = Notification(user_id=user_id, message=f"سفارش {order.order_type} به مقدار {order.amount} ساتوشی حذف شد.")
    db.session.add(notification)
    db.session.commit()

    # حذف سفارش
    db.session.delete(order)
    db.session.commit()
    flash('سفارش با موفقیت حذف شد.', 'success')
    return redirect(url_for('home'))

@app.route('/approve_order/<int:order_id>', methods=['POST'])
@login_required
def approve_order(order_id):
    user_id = session['user_id']
    order = Order.query.get_or_404(order_id)
    user = User.query.get_or_404(user_id)

    # بررسی کامل بودن پروفایل
    if not user.is_profile_complete():
        flash('لطفاً ابتدا پروفایل خود را تکمیل کنید.', 'warning')
        return redirect(url_for('profile'))

    # بررسی اینکه کاربر نمی‌تواند سفارش خود را تأیید کند
    if order.user_id == user_id:
        flash('شما نمی‌توانید سفارش خود را تأیید کنید.', 'danger')
        return redirect(url_for('home'))

    # بررسی اینکه سفارش قبلاً تأیید نشده باشد
    if order.is_approved:
        flash('این سفارش قبلاً تأیید شده است.', 'warning')
        return redirect(url_for('home'))

    # تأیید سفارش
    order.is_approved = True
    order.approved_by = user_id
    db.session.commit()

    # ارسال اعلان به هر دو کاربر
    approver_notification = Notification(
        user_id=user_id,
        message=f"شما سفارش کاربر {order.user.username} را با مقدار {order.amount} ساتوشی تأیید کردید."
    )
    owner_notification = Notification(
        user_id=order.user_id,
        message=f"کاربر {user.username} سفارش شما را با مقدار {order.amount} ساتوشی تأیید کرد."
    )

    db.session.add(approver_notification)
    db.session.add(owner_notification)
    db.session.commit()

    flash('سفارش با موفقیت تأیید شد. اکنون می‌توانید پروفایل یکدیگر را مشاهده کنید.', 'success')
    return redirect(url_for('home'))



@app.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    current_user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    # بررسی ارتباط از طریق سفارش تأییدشده
    approved_orders = Order.query.filter(
        ((Order.user_id == current_user_id) & (Order.approved_by == user_id) & (Order.is_approved == True)) |
        ((Order.user_id == user_id) & (Order.approved_by == current_user_id) & (Order.is_approved == True))
    ).all()

    if not approved_orders:
        flash('فقط طرفین معامله قادر به دیدن پروفایل یکدیگر هستند.', 'danger')
        return redirect(url_for('home'))

    return render_template('profile.html', user=user)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # ایجاد جداول دیتابیس
    app.run(debug=True)
