from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import current_user, login_user, logout_user, login_manager
from core.forms import Register, Login
from core.routes import main
from core.models import User, db, Bookshelf, Author, Book

auth = Blueprint('auth', __name__)
login_manager.login_view = 'auth.login'

@auth.route('/register', methods=['GET', 'POST'])
def register():
    register_form = Register()

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST' and register_form.validate_on_submit():

        print(register_form.password.data)


        username = register_form.username.data
        email = register_form.email.data
        password = register_form.password.data
        confirmed_password = register_form.confirm_password.data

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')

        elif User.query.filter_by(email=email).first():
            flash('Email address already exists.')
        # elif register_form.password.errors:
        elif password != confirmed_password :
            flash('Passwords must match.')
        else:

            user = User(username=username, email=email if email else None)
            user.set_password(password)
            db.session.add(user)

            db.session.commit()

            login_user(user)
            user.add_default_bookshelves()




            return redirect(url_for('main.index'))

    return render_template('register.html', form=register_form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    login_form = Login()

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST' and login_form.validate_on_submit():
        username = login_form.username.data
        password = login_form.password.data

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Username not found.')

        elif not user.check_password(password):
            flash('Incorrect password.')
        else:
            login_user(user)
            return redirect(url_for('main.index'))
    return render_template('login.html', form=login_form)


@auth.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('main.index'))
