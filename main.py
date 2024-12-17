from flask import Flask, render_template, request, redirect, flash
import pymysql
from dynaconf import Dynaconf

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)


app.secret_key = conf.secret_key


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

    cursor.close()
    conn.close()

    return render_template("product.html.jinja", product = result)


@app.route("/sign_up", methods =["POST", "GET"])
def sign_up_page():

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


@app.route("/sign_in")
def sign_in_page():

    return render_template("sign_in.html.jinja")