import flask
from flask import Flask
from flask import request
from flask.views import MethodView
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from models import Advertisement, User, Session, db, HttpError
import os
from dotenv import load_dotenv


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from UserLogin import UserLogin

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv('SECRET_KEY')

login_manager = LoginManager(app)
login_manager.login_view = 'login'

db_app = db()

@app.route('/login')
def login():
    return flask.jsonify({'status': 'Вы не авторизованы'})


@login_manager.user_loader
def load_user(user_id):
    with Session() as session:
        return UserLogin().fromDB(db_app, session, user_id)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return flask.jsonify({'status': 'logout'})


@app.errorhandler(HttpError)
def http_error_handler(er: HttpError):
    response = flask.jsonify({'status': 'error', 'message': er.message})
    response.status_code = er.status_code
    return response


class AdvertisementView(MethodView):

    def get(self, adv_id):
        with Session() as session:
            adv = db_app.get_adv(session, adv_id)
            return flask.jsonify({
                'heading': adv.heading,
                'description': adv.description,
                'creation_date': adv.creation_date,
                'user_id': adv.user_id
            })

    def post(self):
        adv_data = request.json
        with Session() as session:
            user_id = current_user.get_id()
            new_adv = Advertisement(
                heading=adv_data['heading'],
                description=adv_data['description'],
                user_id=user_id
            )
            session.add(new_adv)
            session.commit()
            return flask.jsonify({'status': 'ok', 'id': new_adv.id})

    def patch(self, adv_id):
        adv_data = request.json
        with Session() as session:
            adv = db_app.get_adv(session, adv_id)
            if self.access_ver(adv.user_id):
                for key, value in adv_data.items():
                    setattr(adv, key, value)
                session.commit()
                return flask.jsonify({'status': 'ok'})

            return flask.jsonify({'status': 'доступ к данному объявлению запрещен'})

    def delete(self, adv_id):
        with Session() as session:
            adv = db_app.get_adv(session, adv_id)
            if self.access_ver(adv.user_id):
                session.delete(adv)
                session.commit()
                return flask.jsonify({'status': 'ok'})
            return flask.jsonify({'status': 'доступ к данному объявлению запрещен'})

    def access_ver(self, adv_user_id):
        user_id = current_user.get_id()
        if user_id == str(adv_user_id):
            return True

        return False



app.add_url_rule('/advs/<int:adv_id>', view_func=AdvertisementView.as_view('advs_get'), methods=['GET'])
app.add_url_rule('/advs', view_func=login_required(AdvertisementView.as_view('advs')), methods=['POST'])
app.add_url_rule('/advs/<int:adv_id>', view_func=login_required(AdvertisementView.as_view('advs_pd')),
                 methods=['PATCH', 'DELETE'])


class UserView(MethodView):

    def get(self):
        user_data = request.args
        with Session() as session:
            user = db_app.get_user_by_mail(session, user_data['email'])
            if check_password_hash(user.psw, user_data['psw']):
                userlogin = UserLogin().create(user)
                login_user(userlogin)
                return flask.jsonify({'status': 'ok', 'id': user.id})

            raise HttpError(404, 'Пользователя с такой парой логин/пароль не существует!')

    def post(self):
        user_data = request.json
        hash_psw = self._register_user(user_data)
        with Session() as session:
            db_app.check_user_by_mail(session, user_data['email'])
            new_user = User(email=user_data['email'], psw=hash_psw)
            session.add(new_user)
            session.commit()
            return flask.jsonify({'status': 'ok', 'id': new_user.id})

    def _register_user(self, user_data):
        if len(user_data['email']) in range(4, 100) and len(user_data['psw']) > 4:
            hash_psw = generate_password_hash(user_data['psw'])
            return hash_psw
        else:
            raise HttpError(409, 'Ошибка заполнения формы!')


app.add_url_rule('/users/', view_func=UserView.as_view('users'), methods=['GET'])
app.add_url_rule('/users/', view_func=UserView.as_view('users_post'), methods=['POST'])


if __name__ == '__main__':
    app.run(debug=True)


