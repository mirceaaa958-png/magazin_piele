from flask import Flask, render_template


app = Flask(__name__)


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/femei")
def femei():
    return render_template("categorie.html", categorie="Femei")


@app.route("/barbati")
def barbati():
    return render_template("categorie.html", categorie="Bărbați")


@app.route("/copii")
def copii():
    return render_template("categorie.html", categorie="Copii")


@app.route("/cos")
def cos():
    return render_template("cos.html")


@app.route("/login")
def login():
    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True)