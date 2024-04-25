from flask import Flask, render_template, url_for, request, flash, session, redirect, abort, g, send_from_directory
import pymysql.cursors
import os


def connect_db():
    connection = pymysql.connect(host='localhost',
                                 user='Paskera',
                                 password='912t2414',
                                 database='sport',
                                 cursorclass=pymysql.cursors.DictCursor)
    return connection


def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


app = Flask(__name__)
app.config['SECRET_KEY'] = '12304560'
app.config['UPLOAD_FOLDER'] = "static/pictures/"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


@app.route("/index")
@app.route("/")
def index():
    if 'login' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', title='Main', role=session['role'], login=session['login'])


@app.route("/login", methods=['POST', 'GET'])
def login():
    if 'login' in session:
        return redirect(url_for('index'))
    elif request.method == 'POST':
        connection = get_db()
        with connection.cursor() as cursor:
            cursor.execute("select login, role, password from users;")
            for row in cursor.fetchall():
                count = 0
                for key, value in row.items():
                    if count == 0:
                        login_enter = value
                    elif count == 1:
                        role_enter = value
                    elif count == 2:
                        password_enter = value
                        if request.form['login'] == login_enter and request.form['psw'] == password_enter:
                            session['login'] = request.form['login']
                            session['role'] = role_enter
                            return redirect(url_for('index'))
                        elif request.form['login'] == login_enter and request.form['psw'] != password_enter:
                            flash('Incorrect password')

                        count = -1
                    count += 1
        flash('Login is not registered')
    return render_template('login.html', title='Login')


@app.route("/registration", methods=['POST', 'GET'])
def registration():
    if 'login' in session:
        return redirect(url_for('index'))

    elif request.method == 'POST':
        connection = get_db()
        with connection.cursor() as cursor:
            cursor.execute("select login from users;")

            # Check for used login
            for row in cursor.fetchall():
                if request.form['login'] in row.values():
                    flash("Login is used")
                    return redirect(url_for('registration'))

            # Add information into database
            cursor.execute("insert into `users`(`login`, `password`, `email`, `role`)"
                           "values(%s, %s, %s, %s) ON DUPLICATE KEY update `login` = `login`",
                           (request.form['login'], request.form['psw'],
                            request.form['email'], request.form['role']))
            connection.commit()
            return redirect(url_for('login'))
    return render_template('registration.html', title='Registration')


@app.route("/store", methods=["POST", "GET"])
def store():
    if 'login' not in session:
        return redirect(url_for('login'))
    connection = get_db()

    with connection.cursor() as cursor:
        cursor.execute("select * from product;")
        info = cursor.fetchall()
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("insert into `cart`(`users_login`, `product_id`, `value`)"
                           "values(%s, %s, %s) ON DUPLICATE KEY update `value` = `value` + 1",
                           (session['login'], request.form['id'], 1))
            connection.commit()
            return redirect(url_for('profile', login=session['login']))
    return render_template('store.html', title='Store', cursor=info, role=session['role'],
                           login=session['login'])


@app.route("/products", methods=['POST', 'GET'])
def products():
    if 'login' not in session:
        return redirect(url_for('login'))
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute("select * from product;")
        list_products = cursor.fetchall()
    if request.method == 'POST':
        file = request.files['file']
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], request.form['name'] + '.jpg'))
        with connection.cursor() as cursor:
            cursor.execute("insert into product(name, price, description, value, photo) "
                           "values(%s, %s, %s, %s, %s)",
                           (request.form['name'], request.form['price'],
                            request.form['description'], request.form['value'],
                            os.path.join(app.config['UPLOAD_FOLDER'], request.form['name'] + '.jpg')))
            connection.commit()

        return redirect(url_for('products'))

    # if request.method == 'POST':
    #     with connection.cursor() as cursor:
    #         cursor.execute(f"insert into product(name, price) values ({request.form['name']}, {request.form['price']})")
    #         connection.commit()
    #
    #     return render_template('products.html', title='Products', menu=get_menu(), cursor=list_products)
    return render_template('products.html', title='Products', list_products=list_products,
                           role=session['role'], login=session['login'])


@app.route("/product/<int:id_product>")
def product(id_product):
    if 'login' not in session:
        return redirect(url_for('login'))
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute(f"select * from product where id = {id_product}")
        info = cursor.fetchone()
    if info is None:
        abort(404)
    return render_template('product.html', title=f"Product {info['name']}",
                           row=info, role=session['role'], login=session['login'])


@app.route("/profile/<login>", methods=['POST', 'GET'])
def profile(login):
    if 'login' not in session:
        return redirect(url_for('login'))
    if session['login'] != login:
        abort(401)
    connection = get_db()
    with connection.cursor() as cursor:
        cursor.execute("select * from `product` " 
                       "where `id` in "
                       "(select `product_id` from `cart` where `users_login` = %s)", login)
        cart = cursor.fetchall()

        # For ordered values products
        cursor.execute("select `product_id`, `value` from `cart`"
                       "where `users_login` = %s", login)
        value_product = cursor.fetchall()
    if request.method == 'POST':
        with connection.cursor() as cursor:
            # Out cart 1 product
            cursor.execute("update `cart` "
                           "set value = value - 1 "
                           "where product_id = %s and if(value<>0, 'yes', 'no') = 'yes'", request.form['id'])

            # if value product = 0 => delete product from cart
            cursor.execute("delete "
                           "from cart "
                           "where product_id = %s and if(value=0, 'yes', 'no') = 'yes'", request.form['id'])
            connection.commit()
            return redirect(url_for('profile', login=session['login']))
    return render_template('profile.html', title=f"Profile {login}", cart=cart,
                           role=session['role'], login=session['login'], value_product=value_product)


@app.errorhandler(404)
def page_not_found(error):
    if 'login' not in session:
        return redirect(url_for('login'))
    return render_template('page404.html', title='Page not found', role=session['role'],
                           login=session['login']), 404


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
