from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
import psycopg2.extras
import hashlib
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cs480secret")

DB = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "database": os.environ.get("DB_NAME", "movie_ticketing"),
    "user":     os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASS", "postgres"),
    "port":     os.environ.get("DB_PORT", "5432"),
}

def db(): # kept for compatibility
    return get_conn()

def get_conn():
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    return conn

def hashpw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a, **kw):
        if "uid" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap

def client_only(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a, **kw):
        if session.get("utype") != "client":
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def wrap(*a, **kw):
        if session.get("utype") != "admin":
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap

@app.route("/")
def index():
    if "uid" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("admin_home") if session["utype"] == "admin" else url_for("client_home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM "user" WHERE email=%s AND password_hash=%s',
                    (request.form["email"], hashpw(request.form["password"])))
        u = cur.fetchone()
        conn.close()
        if u:
            session["uid"]   = u["user_id"]
            session["utype"] = u["user_type"]
            session["email"] = u["email"]
            return redirect(url_for("admin_home") if u["user_type"] == "admin" else url_for("client_home"))
        flash("Wrong email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/register/client", methods=["GET", "POST"])
def register_client():
    if request.method == "POST":
        conn = db()
        cur  = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO "user" (email, password_hash, user_type) VALUES (%s,%s,%s) RETURNING user_id',
                (request.form["email"], hashpw(request.form["password"]), "client")
            )
            uid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO client (client_id, full_name, address, movie_interests, reward_signup) VALUES (%s,%s,%s,%s,%s)",
                (uid, request.form["full_name"], request.form["address"],
                 request.form.get("movie_interests", ""), "reward_signup" in request.form)
            )
            conn.commit()
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash(str(e))
        finally:
            conn.close()
    return render_template("register_client.html")

@app.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        conn = db()
        cur  = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO "user" (email, password_hash, user_type) VALUES (%s,%s,%s) RETURNING user_id',
                (request.form["email"], hashpw(request.form["password"]), "admin")
            )
            uid = cur.fetchone()[0]
            cur.execute("INSERT INTO admin (admin_id, admin_role) VALUES (%s,%s)",
                        (uid, request.form["admin_role"]))
            conn.commit()
            flash("Admin account created! Please log in.")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash(str(e))
        finally:
            conn.close()
    return render_template("register_admin.html")

@app.route("/client")
@login_required
@client_only
def client_home():
    return render_template("client_home.html")

@app.route("/client/search")
@login_required
@client_only
def search():
    conn   = db()
    cur    = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    title  = request.args.get("title", "")
    date   = request.args.get("date", "")
    after  = request.args.get("after_time", "")
    is_3d  = request.args.get("is_3d", "")
    fancy  = request.args.get("fancy", "")

    q = """
        SELECT s.screening_id, m.title, m.original_language, m.length_min, m.major_studio,
               t.theater_name, t.is_3d, t.has_fancy_sound,
               t.max_occupancy, s.screening_date, s.start_time, s.end_time,
               calculate_ticket_price(s.screening_id) AS price,
               t.max_occupancy - COALESCE(
                   (SELECT SUM(ticket_quantity) FROM ticket_sale WHERE screening_id = s.screening_id), 0
               ) AS seats_left,
               (SELECT STRING_AGG(p.full_name, ', ') FROM movie_actor ma JOIN person p ON p.person_id = ma.person_id WHERE ma.movie_id = m.movie_id) AS actors,
               (SELECT STRING_AGG(p.full_name, ', ') FROM movie_director md JOIN person p ON p.person_id = md.person_id WHERE md.movie_id = m.movie_id) AS directors
        FROM screening s
        JOIN movie   m ON m.movie_id   = s.movie_id
        JOIN theater t ON t.theater_id = s.theater_id
        WHERE 1=1
    """
    params = []
    if title: q += " AND LOWER(m.title) LIKE LOWER(%s)"; params.append(f"%{title}%")
    if date:  q += " AND s.screening_date = %s";          params.append(date)
    if after: q += " AND s.start_time >= %s";             params.append(after)
    if is_3d == "1": q += " AND t.is_3d = TRUE"
    if fancy == "1": q += " AND t.has_fancy_sound = TRUE"
    q += " ORDER BY s.screening_date, s.start_time"

    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    return render_template("search.html", rows=rows,
                           title=title, date=date, after=after, is_3d=is_3d, fancy=fancy)

@app.route("/client/book", methods=["GET", "POST"])
@login_required
@client_only
def book():
    sid  = request.args.get("sid") or request.form.get("sid")
    conn = db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT s.screening_id, m.title, t.theater_name, t.is_3d, t.has_fancy_sound,
               t.max_occupancy, s.screening_date, s.start_time,
               calculate_ticket_price(s.screening_id) AS price,
               t.max_occupancy - COALESCE(
                   (SELECT SUM(ticket_quantity) FROM ticket_sale WHERE screening_id = s.screening_id), 0
               ) AS seats_left
        FROM screening s
        JOIN movie m ON m.movie_id = s.movie_id
        JOIN theater t ON t.theater_id = s.theater_id
        WHERE s.screening_id = %s
    """, (sid,))
    screening = cur.fetchone()

    cur.execute("SELECT * FROM payment_method WHERE client_id = %s", (session["uid"],))
    cards = cur.fetchall()

    if request.method == "POST":
        qty  = int(request.form["qty"])
        pmid = request.form.get("pmid") or None
        try:
            if pmid:
                cur.execute("INSERT INTO ticket_sale (screening_id, client_id, payment_method_id, ticket_quantity) VALUES (%s,%s,%s,%s)",
                            (sid, session["uid"], pmid, qty))
                cur.execute("UPDATE client SET movies_watched = movies_watched + %s WHERE client_id = %s",
                            (qty, session["uid"]))
            else:
                cur.execute("INSERT INTO ticket_sale (screening_id, ticket_quantity) VALUES (%s,%s)", (sid, qty))
            conn.commit()
            flash(f"Booked {qty} ticket(s)!")
            return redirect(url_for("search"))
        except Exception as e:
            conn.rollback()
            flash(str(e))
        finally:
            conn.close()
        return redirect(url_for("book", sid=sid))

    conn.close()
    return render_template("book.html", s=screening, cards=cards)

@app.route("/client/payments")
@login_required
@client_only
def payments():
    conn = db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM payment_method WHERE client_id = %s", (session["uid"],))
    cards = cur.fetchall()
    conn.close()
    return render_template("payments.html", cards=cards)

@app.route("/client/payments/add", methods=["POST"])
@login_required
@client_only
def add_payment():
    conn = db()
    cur  = conn.cursor()
    try:
        ptype   = request.form["payment_type"]
        billing = request.form.get("billing_address") if ptype == "credit" else None
        cur.execute("""
            INSERT INTO payment_method
            (client_id, payment_type, card_number, billing_address, cardholder_name, expiration_month, expiration_year)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (session["uid"], ptype, request.form["card_number"], billing,
              request.form["cardholder_name"], request.form["exp_month"], request.form["exp_year"]))
        conn.commit()
        flash("Card added.")
    except Exception as e:
        conn.rollback()
        flash(str(e))
    finally:
        conn.close()
    return redirect(url_for("payments"))

@app.route("/client/payments/update", methods=["POST"])
@login_required
@client_only
def update_payment():
    conn = db()
    cur  = conn.cursor()
    try:
        ptype   = request.form["payment_type"]
        billing = request.form.get("billing_address") if ptype == "credit" else None
        cur.execute("""
            UPDATE payment_method
            SET payment_type=%s, card_number=%s, billing_address=%s,
                cardholder_name=%s, expiration_month=%s, expiration_year=%s
            WHERE payment_method_id=%s AND client_id=%s
        """, (ptype, request.form["card_number"], billing,
              request.form["cardholder_name"], request.form["exp_month"],
              request.form["exp_year"], request.form["pmid"], session["uid"]))
        conn.commit()
        flash("Card updated.")
    except Exception as e:
        conn.rollback()
        flash(str(e))
    finally:
        conn.close()
    return redirect(url_for("payments"))

@app.route("/client/payments/delete", methods=["POST"])
@login_required
@client_only
def delete_payment():
    conn = db()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM payment_method WHERE payment_method_id=%s AND client_id=%s",
                    (request.form["pmid"], session["uid"]))
        conn.commit()
        flash("Card deleted.")
    except Exception as e:
        conn.rollback()
        flash(str(e))
    finally:
        conn.close()
    return redirect(url_for("payments"))

@app.route("/admin")
@login_required
@admin_only
def admin_home():
    return render_template("admin_home.html")

@app.route("/admin/screenings")
@login_required
@admin_only
def admin_screenings():
    conn = db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT s.screening_id, m.title, t.theater_name, t.max_occupancy,
               s.screening_date, s.start_time, s.end_time,
               COALESCE((SELECT SUM(ticket_quantity) FROM ticket_sale WHERE screening_id=s.screening_id),0) AS sold,
               t.max_occupancy - COALESCE((SELECT SUM(ticket_quantity) FROM ticket_sale WHERE screening_id=s.screening_id),0) AS remaining
        FROM screening s
        JOIN movie m ON m.movie_id = s.movie_id
        JOIN theater t ON t.theater_id = s.theater_id
        ORDER BY s.screening_date, s.start_time
    """)
    screenings = cur.fetchall()
    cur.execute("SELECT movie_id, title FROM movie ORDER BY title")
    movies = cur.fetchall()
    cur.execute("SELECT theater_id, theater_name FROM theater ORDER BY theater_name")
    theaters = cur.fetchall()
    conn.close()
    return render_template("admin_screenings.html", screenings=screenings, movies=movies, theaters=theaters)

@app.route("/admin/screenings/add", methods=["POST"])
@login_required
@admin_only
def admin_add_screening():
    conn = db()
    cur  = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO screening (movie_id, theater_id, screening_date, start_time, end_time, created_by_admin_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (request.form["movie_id"], request.form["theater_id"], request.form["date"],
              request.form["start_time"], request.form["end_time"], session["uid"]))
        conn.commit()
        flash("Screening added.")
    except Exception as e:
        conn.rollback()
        flash(str(e))
    finally:
        conn.close()
    return redirect(url_for("admin_screenings"))

@app.route("/admin/screenings/delete", methods=["POST"])
@login_required
@admin_only
def admin_delete_screening():
    conn = db()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM screening WHERE screening_id=%s", (request.form["sid"],))
        conn.commit()
        flash("Screening deleted.")
    except Exception as e:
        conn.rollback()
        flash(str(e))
    finally:
        conn.close()
    return redirect(url_for("admin_screenings"))

@app.route("/admin/analytics")
@login_required
@admin_only
def admin_analytics():
    conn = db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT m.title, SUM(ts.total_price) AS revenue, SUM(ts.ticket_quantity) AS tickets
        FROM ticket_sale ts
        JOIN screening s ON s.screening_id = ts.screening_id
        JOIN movie m ON m.movie_id = s.movie_id
        GROUP BY m.title ORDER BY revenue DESC
    """)
    by_movie = cur.fetchall()

    cur.execute("""
        SELECT t.theater_name, SUM(ts.total_price) AS revenue,
               ROUND(AVG(ts.ticket_quantity::numeric / t.max_occupancy * 100), 1) AS avg_occ
        FROM ticket_sale ts
        JOIN screening s ON s.screening_id = ts.screening_id
        JOIN theater t ON t.theater_id = s.theater_id
        GROUP BY t.theater_name, t.max_occupancy ORDER BY revenue DESC
    """)
    by_theater = cur.fetchall()

    cur.execute("""
        SELECT s.screening_date AS date, SUM(ts.total_price) AS revenue, SUM(ts.ticket_quantity) AS tickets
        FROM ticket_sale ts
        JOIN screening s ON s.screening_id = ts.screening_id
        GROUP BY s.screening_date ORDER BY s.screening_date
    """)
    by_date = cur.fetchall()

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE client_id IS NOT NULL) AS registered,
            COUNT(*) FILTER (WHERE client_id IS NULL)     AS anonymous
        FROM ticket_sale
    """)
    totals = cur.fetchone()
    cur.execute("""
        SELECT
            ROUND(MIN(occ.pct), 1) AS min_occ,
            ROUND(AVG(occ.pct), 1) AS avg_occ,
            ROUND(MAX(occ.pct), 1) AS max_occ
        FROM (
            SELECT COALESCE(SUM(ts.ticket_quantity),0)::numeric / t.max_occupancy * 100 AS pct
            FROM screening s
            JOIN theater t ON t.theater_id = s.theater_id
            LEFT JOIN ticket_sale ts ON ts.screening_id = s.screening_id
            GROUP BY s.screening_id, t.max_occupancy
        ) occ
    """)
    occupancy = cur.fetchone()
    conn.close()
    return render_template("admin_analytics.html",
                           by_movie=by_movie, by_theater=by_theater,
                           by_date=by_date, totals=totals, occupancy=occupancy)

if __name__ == "__main__":
    app.run(debug=True)


def calculate_price_manual(is_3d, has_fancy_sound, major_studio, release_date, screening_date):
    import datetime
    price = 15.00
    if is_3d: price += 5.00
    if has_fancy_sound: price += 3.00
    if major_studio: price += 3.00
    if isinstance(release_date, str):
        release_date = datetime.date.fromisoformat(str(release_date))
    if isinstance(screening_date, str):
        screening_date = datetime.date.fromisoformat(str(screening_date))
    import datetime as dt
    two_years_ago = screening_date - dt.timedelta(days=730)
    two_months_ago = screening_date - dt.timedelta(days=60)
    if release_date <= two_years_ago:
        price = round(price * 0.60, 2)
    elif release_date <= two_months_ago:
        price = round(price * 0.80, 2)
    return price


PGVECTOR_AVAILABLE = False
try:
    conn_test = db()
    cur_test = conn_test.cursor()
    cur_test.execute("SELECT 1 FROM pg_extension WHERE extname='vector'")
    if cur_test.fetchone():
        PGVECTOR_AVAILABLE = True
    conn_test.close()
except:
    pass


@app.route("/client/recommendations")
@login_required
@client_only
def recommendations():
    if not PGVECTOR_AVAILABLE:
        flash("Recommendations require the pgvector extension. Ask your admin to run sql/04_bonus_pgvector.sql.")
        return redirect(url_for("client_home"))
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT movie_interests FROM client WHERE client_id = %s", (session["uid"],))
    client = cur.fetchone()
    recs = []
    has_interests = client and client["movie_interests"]
    if has_interests:
        try:
            from embeddings import get_recommendations
            recs = get_recommendations(conn, session["uid"])
        except Exception as e:
            flash(f"Could not load recommendations: {e}")
    conn.close()
    return render_template("recommendations.html", recs=recs, has_interests=has_interests)


@app.route("/client/recommendations/update", methods=["POST"])
@login_required
@client_only
def update_interests():
    if not PGVECTOR_AVAILABLE:
        return redirect(url_for("client_home"))
    interests = request.form.get("interests", "").strip()
    if not interests:
        flash("Please enter your movie interests.")
        return redirect(url_for("recommendations"))
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE client SET movie_interests=%s WHERE client_id=%s", (interests, session["uid"]))
        conn.commit()
        from embeddings import embed_client_interests
        embed_client_interests(conn, session["uid"], interests)
        flash("Interests updated! Your recommendations are ready.")
    except Exception as e:
        conn.rollback()
        flash(str(e))
    finally:
        conn.close()
    return redirect(url_for("recommendations"))


@app.route("/admin/schedule-optimizer")
@login_required
@admin_only
def schedule_optimizer():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT COUNT(*) AS cnt FROM ticket_sale")
    sale_count = cur.fetchone()["cnt"]
    schedule = []
    model_trained = False
    if sale_count >= 3:
        try:
            from ml_model import train_model, generate_optimal_schedule
            train_model(conn)
            schedule = generate_optimal_schedule(conn)
            model_trained = True
        except Exception as e:
            flash(f"ML model error: {e}")
    conn.close()
    return render_template("schedule_optimizer.html",
                           schedule=schedule,
                           model_trained=model_trained,
                           sale_count=sale_count)


@app.route("/admin/embed-movies", methods=["POST"])
@login_required
@admin_only
def embed_movies():
    if not PGVECTOR_AVAILABLE:
        flash("pgvector extension not installed. Run sql/04_bonus_pgvector.sql first.")
        return redirect(url_for("admin_home"))
    conn = get_conn()
    try:
        from embeddings import embed_all_movies
        embed_all_movies(conn)
        flash("All movies embedded successfully!")
    except Exception as e:
        flash(f"Embedding error: {e}")
    finally:
        conn.close()
    return redirect(url_for("admin_home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)