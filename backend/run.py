import os
import datetime
from flask import Flask, json, request
from flask_jwt import JWT, jwt_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import safe_str_cmp
from geopy.geocoders import Nominatim
from flask_cors import CORS

geolocator = Nominatim()

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "queuedatabase.db"))

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'super-secret'

# setting up the database
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(80), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    storespace = db.Column(db.Integer, nullable=False)
    maxcapacity = db.Column(db.Integer, nullable=False)
    userid = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "<ID: {}>".format(self.id)


class People(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shopid = db.Column(db.Integer, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Float, nullable=False)
    waitingtime = db.Column(db.Integer, nullable=False)
    lastupdate = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return "<ID: {}>".format(id)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    shopaddress = db.Column(db.String(80), nullable=False)
    login = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return "<ID: {}>".format(self.id)


class CurrentUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(80), nullable=False)
    login = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return "<ID: {}>".format(self.id)


def get_all_users():
    users = [12]  # load all users
    username_table = {u.username: u for u in users}
    userid_table = {u.id: u for u in users}
    return username_table, userid_table


def authenticate(username, password):
    username_table, _ = get_all_users()
    user = username_table.get(username, None)
    if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
        return user


def identity(payload):
    _, userid_table = get_all_users()
    user_id = payload['identity']
    return userid_table.get(user_id, None)


def update_database(id_, peoplechange):
    lastup = People.query.filter_by(shopid=id_).order_by(People.id.desc()).first()
    if lastup is None:
        num = peoplechange
    else:
        num = lastup.number + peoplechange
    shopinf = Shop.query.filter_by(id=id_).first()
    if lastup is None:
        maxcap = 100
    else:
        maxcap = shopinf.maxcapacity

    cap = num / maxcap
    if cap < 1:
        wait = 0
    else:
        wait = num - maxcap

    people = People(
        shopid=id_,
        number=num,
        capacity=cap,
        waitingtime=wait,
        lastupdate=datetime.datetime.now()
    )
    db.session.add(people)
    db.session.commit()
    return num


def register(signin_data):
    # check whether it is the correct format for signin_data
    user = User(
        name=signin_data["name"],
        shopaddress="DUMMY",
        login=signin_data["login"],
        password=signin_data["password"]
    )
    db.session.add(user)
    db.session.commit()


def login(username, password):
    # pw = User.query.filter(login = username).last()
    pw = User.query.filter_by(login=username).first()
    if (pw.password == password):
        curUsr = CurrentUser(
            userid=pw.id,
            login=pw.login,
            password=pw.password
        )
        db.session.add(curUsr)
        db.session.commit()
        return pw.id
    else:
        return False


def get_shops(all=True, id_=""):
    if all:
        shops = Shop.query.all()
    else:
        shops = Shop.query.filter_by(userid=id_).all()
    shoplist = []
    for shop in shops:
        peop = People.query.filter_by(shopid=shop.id).order_by(People.id.desc()).first()
        shoplist.append({
            "id": shop.id,
            "name": shop.name,
            "category": shop.category,
            'latitude': shop.latitude,
            'longitude': shop.longitude,
            'waitingtime': peop.waitingtime,
            'capacity': peop.capacity
        })
    return shoplist


def get_shopinfo(id_):
    # peop = People.query.filter(People.lastupdate<time).order_by(People.id.desc()).first()
    p = People.query.filter_by(shopid=id_).order_by(People.id.desc()).first()
    shopinf = Shop.query.filter_by(id=p.shopid).first()
    peop = People.query.filter_by(shopid=id_).order_by(People.id.desc())
    peoplist = []
    for pep in peop:
        peoplist.append({
            'id': shopinf.id,
            'name': shopinf.name,
            'category': shopinf.category,
            'address': shopinf.address,
            'latitude': shopinf.latitude,
            'longitude': shopinf.longitude,
            'storespace': shopinf.storespace,
            'maxcapacity': shopinf.maxcapacity,
            'capacity': pep.capacity,
            'waitingtime': pep.waitingtime,
            'lastupdate': pep.lastupdate
        })
    return peoplist


def add_shop(shopinfo):
    location = geolocator.geocode(shopinfo["address"])
    lat, long = location.latitude, location.longitude

    newshop = Shop(
        name=shopinfo["name"],
        category=shopinfo["category"],
        address=shopinfo["address"],
        latitude=lat,
        longitude=long,
        storespace=shopinfo["storespace"],
        maxcapacity=shopinfo["maxcapacity"],
        userid=shopinfo["userid"]
    )
    db.session.add(newshop)
    db.session.commit()

    ###

    newpeop = People(
        shopid=newshop.id,
        number=0,
        capacity=0,
        waitingtime=0,
        lastupdate=datetime.datetime.now()
    )
    db.session.add(newpeop)
    db.session.commit()


# jwt = JWT(app, authenticate, identity)

@app.route('/usershops', methods=['GET', 'POST'])
def list_all_user_shops():
    try:
        if request.method == "GET":
            id_ = request.args.get("id")
            shops = get_shops(False, id_)
            return app.response_class(response=json.dumps(shops), status=200, mimetype='application/json')
    except:
        return app.response_class(response=json.dumps("Service unavailable"), status=503, mimetype='application/json')


@app.route('/register', methods=['GET', 'POST'])
# @jwt_required()
def register_user():
    try:
        if request.method == "POST":
            signin_data = request.json
            register(signin_data)

            return app.response_class(response=json.dumps("User was added"), status=200, mimetype='application/json')
    except:
        return app.response_class(response=json.dumps("Service unavailable"), status=503, mimetype='application/json')


@app.route('/signin', methods=['GET', 'POST'])
# @jwt_required()
def login_user():
    try:
        if request.method == "POST":
            username, password = request.json["login"], request.json["password"]
            id_ = login(username, password)

            if id_ != False:
                return app.response_class(response=json.dumps(id_), status=200, mimetype='application/json')
            return app.response_class(response=json.dumps("Access denied"), status=401, mimetype='application/json')
    except:
        return app.response_class(response=json.dumps("Service unavailable"), status=503, mimetype='application/json')


@app.route('/update', methods=['GET', 'POST'])
# @jwt_required()
def update():
    try:
        if request.method == "POST":
            id_, peoplechange, userid = request.json["id"], request.json["peoplechange"], request.json["userid"]
            if CurrentUser.query.filter_by(userid=userid) != None:
                update_database(id_, peoplechange)
                return app.response_class(response=json.dumps(f"Updated {id_}\'s number of people"), status=200,
                                          mimetype='application/json')
            else:
                return app.response_class(response=json.dumps("Access denied"), status=401, mimetype='application/json')
    except:
        return app.response_class(response=json.dumps("Service unavailable"), status=503, mimetype='application/json')


@app.route('/shopinfo', methods=['GET', 'POST'])
def shopinfo():
    try:
        if request.method == "GET":
            id_ = request.args.get('id')
            shopinfo = get_shopinfo(id_)
            return app.response_class(response=json.dumps(shopinfo), status=200, mimetype='application/json')
        elif request.method == "POST":
            shopinfo = request.json
            if CurrentUser.query.filter_by(userid=shopinfo["userid"]) != None:
                add_shop(shopinfo)
                return app.response_class(response=json.dumps(f"{shopinfo['name']}\'s data was added in database"),
                                        status=200, mimetype='application/json')
            else:
                return app.response_class(response=json.dumps("Access denied"), status=401, mimetype='application/json')
    except:
        return app.response_class(response=json.dumps("Service unavailable"),status=503,mimetype='application/json')

@app.route('/shops', methods=['GET', 'POST'])
def list_all_shops():
    try:
        if request.method == "GET":
            shops = get_shops()
            return app.response_class(response=json.dumps(shops), status=200, mimetype='application/json')
    except:
        return app.response_class(response=json.dumps("Service unavailable"), status=503, mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
