from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange, Length, Regexp

class OrderForm(FlaskForm):
    order_type = SelectField('نوع سفارش', choices=[('buy', 'خرید'), ('sell', 'فروش')], validators=[DataRequired()])
    amount = IntegerField('مقدار', validators=[DataRequired(), NumberRange(min=1000, max=10000)])
    card_number = StringField('شماره کارت', validators=[DataRequired(), Length(min=16, max=16, message="شماره کارت باید ۱۶ رقم باشد"), Regexp(r'^\d{16}$', message="شماره کارت باید فقط شامل ارقام باشد")])
    lightning_wallet = StringField('آدرس کیف پول لایتنینگ', validators=[DataRequired(), Length(max=255, message="آدرس کیف پول لایتنینگ نمی‌تواند بیشتر از ۲۵۵ کاراکتر باشد")])
