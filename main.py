from flask import Flask, render_template, request, redirect, flash, abort
import pymysql
from dynaconf import Dynaconf
import flask_login

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

 
app.secret_key = conf.secret_key

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = '/sign_in'

class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True

    def __init__(self, user_id, username, email, first_name, last_name):
        self.id = user_id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

    def get_id(self): 
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM `Customer` WHERE id ={user_id};")

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is not None:
        return User(result["id"], result["username"], result["email"], result["first_name"], result["last_name"])


def connect_db():
    conn = pymysql.connect(
        host = "10.100.34.80",
        database = "kheaven_seeds_n_shrubs",
        user = 'kheaven',
        password = conf.password,
        autocommit = True,
        cursorclass = pymysql.cursors.DictCursor
    )

    return conn

@app.route("/")
def index():
    return render_template("homepage.html.jinja")


@app.route("/browse")
def product_browse():
    query = request.args.get('query')

    conn = connect_db()

    cursor = conn.cursor()

    if query is None:
        cursor.execute(f"SELECT * FROM `Product`;")
    else:
        cursor.execute(f"SELECT * FROM `Product` WHERE `product` LIKE '%{query}%' OR `description` LIKE '%{query}%';")

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("browse.html.jinja", products = results, query = query)


@app.route("/product/<product_id>")
def product_page(product_id):

    conn = connect_db()

    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM `Product` WHERE `id` = {product_id};")

    result = cursor.fetchone()

    if result is None:
        abort(404)

    cursor.execute(f""" SELECT
                            `customer_id`,
                            `product_id`,
                            `written_review`,
                            `rating`,
                            `Review`.`timestamp`,
                            `username`
                        FROM `Review`
                        JOIN `Customer` ON `customer_id` = `Customer`.`id`
                        WHERE `product_id` = {product_id};
                    """)
    
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    total = 0
    try:

        for rating in results:
            number = rating['rating']

            total += number
        count = len(results)
        average = total/count
    except:
        average = 0
    

    return render_template("product.html.jinja", product = result, reviews = results, average = average)


@app.route("/product/<product_id>/cart", methods = ["POST"])
@flask_login.login_required
def add_to_cart(product_id):
    quantity = request.form["quantity"]
    customer_id = flask_login.current_user.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"""INSERT INTO 
                    `Cart` (`customer_id`, `product_id`, `quantity`) 
                   VALUES ('{customer_id}','{product_id}','{quantity}')
                   ON DUPLICATE KEY UPDATE 
                   `quantity` = `quantity` + {quantity}
                   """)
    
    cursor.close()
    conn.close()

    return redirect('/cart')



@app.route("/sign_up", methods =["POST", "GET"])
def sign_up_page():
    if flask_login.current_user.is_authenticated:
        return redirect("/")
    else:
        if request.method == 'POST':

            first_name = request.form["first_name"]
            last_name = request.form["last_name"]

            email = request.form["email"]
            address = request.form["address"]

            username = request.form["user_name"]
            password = request.form["password"]
            comfirm_password = request.form["verify_password"]

            conn = connect_db()

            cursor = conn.cursor()

            if comfirm_password != password:
                flash("Sorry, those passwords do not match")
            elif len(password) < 12:
                flash("Sorry, that password is too shoort")
            else:
                try:
                    cursor.execute(f""" 
                        INSERT INTO `Customer`
                            (`first_name`, `last_name`, `username`, `password`, `email`, `address` )
                        VALUES
                            ( '{first_name}', '{last_name}', '{username}', '{password}', '{email}', '{address}' );
                    """)
                except pymysql.err.IntegrityError:
                    flash("Sorry, that username/email is already in use")
                else:
                    return redirect("/sign_in") 
                finally:
                    cursor.close()
                    conn.close()


        return render_template("sign_up.html.jinja")


@app.route("/sign_in", methods =["POST", "GET"])
def sign_in_page():
    if flask_login.current_user.is_authenticated:
        return redirect("/")
    else:
        if request.method == "POST":
            username = request.form['username'].strip()
            password = request.form['password']

            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}';")

            result = cursor.fetchone()

            if result is None:
                flash("Your username/password is incorrect")
            elif password != result["password"]:
                flash("Your username/password is incorrect")
            else:
                user = User(result["id"], result["username"], result["email"], result["first_name"], result["last_name"])
                flask_login.login_user(user)

                return redirect("/")


        return render_template("sign_in.html.jinja")


@app.route('/sign_out')
def sign_out():
    flask_login.logout_user()
    return redirect('/')


@app.route('/cart')
@flask_login.login_required
def cart():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    cursor.execute(f"""
        SELECT 
            `product`, 
            `price`, 
            `quantity`, 
            `image`, 
            `product_id`, 
            `Cart`.`id` 
        FROM `Cart` 
        JOIN `Product` ON `product_id` = `Product`.`id` 
        WHERE `customer_id` = {customer_id};""")

    results = cursor.fetchall()

    total = 0
    for products in results:
        quantity =   products["quantity"]
        price = products["price"]
        item_total = quantity * price
        total = item_total + total

    cursor.close()
    conn.close()

    return render_template("cart.html.jinja", products = results, total = total)


@app.route("/cart/<cart_id>/del", methods = ["POST"])
@flask_login.login_required
def delete(cart_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM `Cart` WHERE `id` = {cart_id};")

    cursor.close()
    conn.close()
    return redirect("/cart")


@app.route("/cart/<cart_id>/update", methods = ["POST"])
@flask_login.login_required
def update(cart_id):
    quantity = request.form["qty"]

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"UPDATE `Cart` SET `quantity` = {quantity} WHERE `id` = {cart_id};")

    cursor.close()
    conn.close()
    return redirect("/cart")


@app.route("/check_out")
@flask_login.login_required
def check_out():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    cursor.execute(f"""
        SELECT 
            `product`, 
            `price`, 
            `quantity`, 
            `image`, 
            `product_id`, 
            `Cart`.`id` 
        FROM `Cart` 
        JOIN `Product` ON `product_id` = `Product`.`id` 
        WHERE `customer_id` = {customer_id};""")

    results = cursor.fetchall()

    if len(results) > 0:

        total = 0
        for products in results:
            quantity =   products["quantity"]
            price = products["price"]
            item_total = quantity * price
            total = item_total + total

        cursor.close()
        conn.close()

        return render_template("check_out.html.jinja", products = results, total = total)
    else:
        return redirect("/cart")


@app.route("/sales", methods = ["POST"])
def sales():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    address = request.form["address"]
    payment = request.form["payment"]

    cursor.execute(f"""
                   INSERT INTO `Sale`
                      (`address`, `payment`, `customer_id`)
                   VALUES
                      ('{address}', '{payment}', '{customer_id}');
                   """)
    
    sale_id = cursor.lastrowid

    cursor.execute(f""" SELECT * FROM `Cart` WHERE `customer_id` = {customer_id};""")
    
    results = cursor.fetchall()

    for products in results:
        product_id = products["product_id"]
        quantity = products["quantity"]
        cursor.execute(f""" 
                        INSERT INTO `SaleProduct`
                            (`product_id`, `quantity`, `sale_id`)
                        VALUES
                            ('{product_id}','{quantity}', '{sale_id}');
                       """)
    cursor.execute(f"DELETE FROM `Cart` WHERE `customer_id` = '{customer_id}';")
    cursor.close()
    conn.close()
    return redirect("/thank_you")


@app.route("/thank_you")
@flask_login.login_required
def thank_you():
    return render_template("thank_you.html.jinja")

@app.route("/product/<product_id>/review", methods = ["POST"])
@flask_login.login_required
def review(product_id):
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    written_review = request.form["written_review"]
    rating = request.form["rating"]

    cursor.execute(f"""INSERT INTO `Review`
                   (`customer_id`, `product_id`, `written_review`, `rating`)
                   VALUES
                   ("{customer_id}","{product_id}","{written_review}","{rating}")
                   ON DUPLICATE KEY UPDATE 
                   `written_review` = "{written_review}",
                   `rating` = "{rating}";
                    """)

    return redirect(f"/product/{product_id}")


