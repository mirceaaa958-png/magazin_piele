from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

DATABASE = "magazin.db"
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/femei")
def femei():
    db = get_db()
    produse = db.execute(
        "SELECT * FROM produse WHERE categorie = ? AND status = 1",
        ("Femei",)
    ).fetchall()
    return render_template("categorie.html", categorie="Femei", produse=produse)

@app.route("/barbati")
def barbati():
    db = get_db()
    produse = db.execute(
        "SELECT * FROM produse WHERE categorie = ? AND status = 1",
        ("Bărbați",)
    ).fetchall()
    return render_template("categorie.html", categorie="Bărbați", produse=produse)

@app.route("/copii")
def copii():
    db = get_db()
    produse = db.execute(
        "SELECT * FROM produse WHERE categorie = ? AND status = 1",
        ("Copii",)
    ).fetchall()
    return render_template("categorie.html", categorie="Copii", produse=produse)

@app.route("/cos")
def cos():
    return render_template("cos.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/admin")
def admin():
    db = get_db()
    produse = db.execute("SELECT * FROM produse").fetchall()
    return render_template("admin.html", produse=produse)

@app.route("/admin/sterge/<int:id>")
def admin_sterge(id):
    db = get_db()
    db.execute("DELETE FROM produse WHERE id = ?", (id,))
    db.commit()
    return redirect("/admin")

@app.route("/admin/toggle/<int:id>")
def admin_toggle(id):
    db = get_db()
    produs = db.execute("SELECT status FROM produse WHERE id=?", (id,)).fetchone()

    nou_status = 0 if produs["status"] == 1 else 1

    db.execute(
        "UPDATE produse SET status=? WHERE id=?",
        (nou_status, id)
    )
    db.commit()

    return redirect("/admin")
@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def admin_edit(id):
    db = get_db()

    if request.method == "POST":
        nume = request.form["nume"]
        pret = request.form["pret"]
        descriere = request.form["descriere"]
        categorie = request.form["categorie"]

        file = request.files.get("imagine")

        if file and file.filename != "":
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            imagine = "/" + filepath.replace("\\", "/")

            db.execute(
                "UPDATE produse SET nume=?, pret=?, imagine=?, descriere=?, categorie=? WHERE id=?",
                (nume, pret, imagine, descriere, categorie, id)
            )
        else:
            db.execute(
                "UPDATE produse SET nume=?, pret=?, descriere=?, categorie=? WHERE id=?",
                (nume, pret, descriere, categorie, id)
            )

        db.commit()
        return redirect("/admin")

    produs = db.execute("SELECT * FROM produse WHERE id=?", (id,)).fetchone()
    return render_template("admin_edit.html", produs=produs)

@app.route("/admin/adauga", methods=["GET", "POST"])
def admin_adauga():
    if request.method == "POST":
        nume = request.form["nume"]
        pret = request.form["pret"]
        descriere = request.form["descriere"]
        categorie = request.form["categorie"]
        status = request.form["status"]

        file = request.files.get("imagine")
        imagine = ""

        if file and file.filename != "":
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            imagine = "/" + filepath.replace("\\", "/")

        db = get_db()
        db.execute(
            "INSERT INTO produse (nume, pret, imagine, descriere, categorie, status) VALUES (?, ?, ?, ?, ?, ?)",
             (nume, pret, imagine, descriere, categorie, status)
        )
        db.commit()

        return redirect("/admin")

    return render_template("admin.html")

def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS produse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nume TEXT NOT NULL,
            pret REAL NOT NULL,
            imagine TEXT NOT NULL,
            descriere TEXT,
            categorie TEXT,
            status INTEGER DEFAULT 1
        )
    """)

    try:
        db.execute("ALTER TABLE produse ADD COLUMN status INTEGER DEFAULT 1")
    except:
        pass

    db.commit()

init_db()


if __name__ == "__main__":
    app.run(debug=True)