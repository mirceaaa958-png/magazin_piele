from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "lethare-secret"
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


def produse_cu_highlight(categorie):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM produse WHERE categorie = ? AND status = 1",
        (categorie,)
    ).fetchall()

    normale = [p for p in rows if p["highlight"] == 0]
    highlight = [p for p in rows if p["highlight"] == 1]

    produse = []
    i = 0
    h = 0

    while i < len(normale):
        produse.extend(normale[i:i+6])
        i += 6

        if h < len(highlight):
            produse.append(highlight[h])
            h += 1

    return produse


@app.route("/femei")
def femei():
    produse = produse_cu_highlight("Femei")
    return render_template("categorie.html", categorie="Femei", produse=produse)


@app.route("/barbati")
def barbati():
    produse = produse_cu_highlight("Bărbați")
    return render_template("categorie.html", categorie="Bărbați", produse=produse)


@app.route("/copii")
def copii():
    produse = produse_cu_highlight("Copii")
    return render_template("categorie.html", categorie="Copii", produse=produse)
@app.route("/produs/<int:id>")
def produs(id):
    db = get_db()
    produs = db.execute(
        "SELECT * FROM produse WHERE id=?",
        (id,)
    ).fetchone()

    return render_template("produs.html", produs=produs)
@app.route("/cos/adauga/<int:id>")
def cos_adauga(id):
    cos = session.get("cos", {})

    if str(id) in cos:
        cos[str(id)] += 1
    else:
        cos[str(id)] = 1

    session["cos"] = cos

    return redirect(request.referrer or "/")
@app.route("/cos/remove/<int:id>")
def cos_remove(id):
    cos = session.get("cos", {})

    if str(id) in cos:
        del cos[str(id)]

    session["cos"] = cos
    return redirect("/cos")
@app.route("/cos/update/<int:id>/<int:cant>")
def cos_update(id, cant):
    cos = session.get("cos", {})

    if cant <= 0:
        cos.pop(str(id), None)
    else:
        cos[str(id)] = cant

    session["cos"] = cos
    return redirect("/cos")
@app.route("/cos")
def cos():
    cos = session.get("cos", {})

    produse = []
    total = 0

    if cos:
        db = get_db()
        ids = [int(i) for i in cos.keys()]
        query = f"SELECT * FROM produse WHERE id IN ({','.join(['?']*len(ids))})"
        rows = db.execute(query, ids).fetchall()

        for p in rows:
            cant = cos.get(str(p["id"]), 0)
            subtotal = p["pret"] * cant
            total += subtotal

            produse.append({
                "id": p["id"],
                "nume": p["nume"],
                "pret": p["pret"],
                "imagine": p["imagine"],
                "cantitate": cant,
                "subtotal": subtotal
            })

    return render_template("cos.html", produse=produse, total=total)

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cos = session.get("cos", {})

    if not cos:
        return redirect("/cos")

    db = get_db()

    ids = [int(i) for i in cos.keys()]
    query = f"SELECT * FROM produse WHERE id IN ({','.join(['?']*len(ids))})"
    rows = db.execute(query, ids).fetchall()

    total = 0
    produse = []

    for p in rows:
        cant = cos.get(str(p["id"]), 0)
        subtotal = p["pret"] * cant
        total += subtotal
        produse.append((p["nume"], cant, subtotal))

    if request.method == "POST":
        nume = request.form["nume"]
        email = request.form["email"]
        telefon = request.form["telefon"]
        adresa = request.form["adresa"]

        db.execute(
            "INSERT INTO comenzi (nume, email, telefon, adresa, total, data) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (nume, email, telefon, adresa, total)
        )
        db.commit()

        session["cos"] = {}
        return render_template("confirmare.html", total=total)

    return render_template("checkout.html", produse=produse, total=total)

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/admin")
def admin():
    categorie = request.args.get("categorie")

    db = get_db()

    if categorie and categorie != "Toate":
        produse = db.execute(
            "SELECT * FROM produse WHERE categorie=?",
            (categorie,)
        ).fetchall()
    else:
        produse = db.execute("SELECT * FROM produse").fetchall()

    return render_template("admin.html", produse=produse, categorie=categorie)

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
        status = request.form["status"]
        highlight = request.form["highlight"]

        file = request.files.get("imagine")

        if file and file.filename != "":
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            imagine = "/" + filepath.replace("\\", "/")

            db.execute(
                "UPDATE produse SET nume=?, pret=?, imagine=?, descriere=?, categorie=?, status=?, highlight=? WHERE id=?",
                (nume, pret, imagine, descriere, categorie, status, highlight, id)
            )
        else:
            db.execute(
                "UPDATE produse SET nume=?, pret=?, descriere=?, categorie=?, status=?, highlight=? WHERE id=?",
                (nume, pret, descriere, categorie, status, highlight, id)
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
        highlight = request.form["highlight"]

        file = request.files.get("imagine")
        imagine = ""

        if file and file.filename != "":
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            imagine = "/" + filepath.replace("\\", "/")

        db = get_db()
        db.execute(
            "INSERT INTO produse (nume, pret, imagine, descriere, categorie, status, highlight) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nume, pret, imagine, descriere, categorie, status, highlight)
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
            status INTEGER DEFAULT 1,
            highlight INTEGER DEFAULT 0
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS comenzi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nume TEXT,
            email TEXT,
            telefon TEXT,
            adresa TEXT,
            total REAL,
            data TEXT
        )
    """)

    try:
        db.execute("ALTER TABLE produse ADD COLUMN status INTEGER DEFAULT 1")
    except:
        pass

    try:
        db.execute("ALTER TABLE produse ADD COLUMN highlight INTEGER DEFAULT 0")
    except:
        pass

    db.commit()


init_db()


if __name__ == "__main__":
    app.run(debug=True)