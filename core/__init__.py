from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_ckeditor import CKEditor

db = SQLAlchemy()
login_manager = LoginManager()
ckeditor = CKEditor()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.static_url_path='/static'

    db.init_app(app)
    from core.models import User, Book
    with app.app_context():
        db.create_all()


    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    ckeditor.init_app(app)

    from core.routes import main
    from core.auth import auth
    app.register_blueprint(main)
    app.register_blueprint(auth)



    return app