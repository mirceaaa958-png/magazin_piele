from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "lethare-secret"
DATABASE = "magazin.db"
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.context_processor
def inject_client():
    return dict(
        client_logat="client_id" in session,
        client_nume=session.get("client_nume"),
        client_email=session.get("client_email")
    )

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
    session["last_shop"] = request.path
    produse = produse_cu_highlight("Femei")
    return render_template("categorie.html", categorie="Femei", produse=produse)


@app.route("/barbati")
def barbati():
    session["last_shop"] = request.path
    produse = produse_cu_highlight("Bărbați")
    return render_template("categorie.html", categorie="Bărbați", produse=produse)


@app.route("/copii")
def copii():
    session["last_shop"] = request.path
    produse = produse_cu_highlight("Copii")
    return render_template("categorie.html", categorie="Copii", produse=produse)
@app.route("/accesorii")
def accesorii():
    session["last_shop"] = "/accesorii"

    conn = sqlite3.connect("magazin.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM produse WHERE LOWER(categorie)='accesorii'")
    produse = c.fetchall()

    conn.close()

    return render_template("categorie.html", produse=produse, titlu="Accesorii")
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
        email = session.get("client_email") or request.form["email"]
        telefon = request.form["telefon"]
        adresa = request.form["adresa"]
        produse_cmd = str(cos)
        db.execute(
            "INSERT INTO comenzi (nume, email, telefon, adresa, total, data, produse) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)",
            (request.form["nume"], email, telefon, adresa, total, produse_cmd)
       )
        db.commit()

        session["cos"] = {}
        return render_template("confirmare.html", total=total)
        
    return render_template("checkout.html", produse=produse, total=total)

@app.route("/login", methods=["GET", "POST"])
def login():
    # dacă deja logat → cont
    if "client_id" in session:
        return redirect("/cont")

    if request.method == "POST":
        email = request.form["email"]
        parola = request.form["parola"]

        db = get_db()
        client = db.execute(
            "SELECT * FROM clienti WHERE email=? AND parola=?",
            (email, parola)
        ).fetchone()

        if client:
            session["client_id"] = client["id"]
            session["client_nume"] = client["nume"]
            session["client_email"] = client["email"]

            # revine unde era sau cont
            next_page = request.args.get("next")
            return redirect(next_page or "/cont")

        else:
            return "Date incorecte"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nume = request.form.get("nume")
        email = request.form.get("email")
        parola = request.form.get("parola")
        telefon = request.form.get("telefon")
        adresa = request.form.get("adresa")

        db = get_db()

        try:
            db.execute(
                """
                INSERT INTO clienti (nume, email, parola, telefon, adresa)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nume, email, parola, telefon, adresa)
            )
            db.commit()
            return redirect("/login")

        except Exception:
            return "Email deja existent"

    return render_template("register.html")


@app.route("/cont")
def cont():
    if "client_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("magazin.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM clienti WHERE id=?", (session["client_id"],))
    client = c.fetchone()

    conn.close()

    return render_template("cont.html", client=client)

@app.route("/logout")
def logout():
    session.pop("client_id", None)
    session.pop("client_nume", None)
    session.pop("client_email", None)
    return redirect("/")

@app.route("/cont/comenzi")
def cont_comenzi():
    if "client_id" not in session:
        return redirect("/login")

    db = get_db()
    comenzi = db.execute(
        "SELECT * FROM comenzi WHERE email=? ORDER BY data DESC",
        (session.get("client_email"),)
    ).fetchall()

    return render_template("cont_comenzi.html", comenzi=comenzi)
@app.route("/cont/comanda/<int:id>")
def cont_comanda(id):
    if "client_id" not in session:
        return redirect("/login")

    db = get_db()

    c = db.execute(
        "SELECT * FROM comenzi WHERE id=? AND email=?",
        (id, session.get("client_email"))
    ).fetchone()

    if not c:
        return redirect("/cont/comenzi")

    produse_list = []

    if c["produse"]:
        cos = eval(c["produse"])

        ids = [int(i) for i in cos.keys()]
        if ids:
            query = f"SELECT id, nume, pret, imagine FROM produse WHERE id IN ({','.join(['?']*len(ids))})"
            produse_db = db.execute(query, ids).fetchall()

            prod_map = {p["id"]: p for p in produse_db}

            for pid, cant in cos.items():
                p = prod_map.get(int(pid))
                if p:
                    produse_list.append({
                        "nume": p["nume"],
                        "pret": p["pret"],
                        "cant": cant,
                        "subtotal": p["pret"] * cant,
                        "imagine": p["imagine"]
                    })

    comanda = {
        "id": c["id"],
        "data": c["data"],
        "status": c["status"],
        "total": c["total"],
        "produse": produse_list
    }

    return render_template("cont_comanda.html", c=comanda)
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
@app.route("/admin/comenzi")
def admin_comenzi():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM comenzi ORDER BY data DESC"
    ).fetchall()

    comenzi = []

    for c in rows:
        produse_list = []

        if c["produse"]:
            cos = eval(c["produse"])

            ids = [int(i) for i in cos.keys()]
            if ids:
                query = f"SELECT id, nume FROM produse WHERE id IN ({','.join(['?']*len(ids))})"
                produse_db = db.execute(query, ids).fetchall()

                nume_map = {p["id"]: p["nume"] for p in produse_db}

                for pid, cant in cos.items():
                    nume = nume_map.get(int(pid), "Produs șters")
                    produse_list.append(f"{nume} — x{cant}")

        comenzi.append({
            "id": c["id"],
            "nume": c["nume"],
            "email": c["email"],
            "telefon": c["telefon"],
            "total": c["total"],
            "data": c["data"],
            "status": c["status"],
            "produse": produse_list
      })

    return render_template("admin_comenzi.html", comenzi=comenzi)
@app.route("/admin/comanda/<int:id>")
def admin_comanda(id):
    db = get_db()

    c = db.execute(
        "SELECT * FROM comenzi WHERE id=?",
        (id,)
    ).fetchone()

    produse_list = []

    if c["produse"]:
        cos = eval(c["produse"])

        ids = [int(i) for i in cos.keys()]
        if ids:
            query = f"SELECT id, nume, pret FROM produse WHERE id IN ({','.join(['?']*len(ids))})"
            produse_db = db.execute(query, ids).fetchall()

            prod_map = {p["id"]: p for p in produse_db}

            for pid, cant in cos.items():
                p = prod_map.get(int(pid))
                if p:
                    produse_list.append({
                        "nume": p["nume"],
                        "pret": p["pret"],
                        "cant": cant,
                        "subtotal": p["pret"] * cant
                    })

    comanda = {
        "id": c["id"],
        "nume": c["nume"],
        "email": c["email"],
        "telefon": c["telefon"],
        "adresa": c["adresa"],
        "total": c["total"],
        "data": c["data"],
        "produse": produse_list
    }

    return render_template("admin_comanda.html", c=comanda)
@app.route("/admin/comanda/status/<int:id>", methods=["POST"])
def admin_comanda_status(id):
    status = request.form["status"]

    db = get_db()
    db.execute(
        "UPDATE comenzi SET status=? WHERE id=?",
        (status, id)
    )
    db.commit()

    return redirect("/admin/comenzi")
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
    db.execute("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nume TEXT,
            email TEXT UNIQUE,
            parola TEXT,
            telefon TEXT,
            data_creare TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    try:
        db.execute("ALTER TABLE comenzi ADD COLUMN produse TEXT")
    except:
        pass
    try:
        db.execute("ALTER TABLE comenzi ADD COLUMN status TEXT DEFAULT 'Noua'")
    except:
        pass
    db.commit()


init_db()


if __name__ == "__main__":
    app.run(debug=True)