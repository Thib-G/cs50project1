import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

if not os.getenv("GOODREAD_API_KEY"):
    raise RuntimeError("GOODREAD_API_KEY is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"), poolclass=NullPool)
db = scoped_session(sessionmaker(bind=engine))

# Goodread
GR_KEY = os.getenv("GOODREAD_API_KEY")
GR_URL = "https://www.goodreads.com/book/review_counts.json"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.execute("""
            SELECT id, email FROM users
            WHERE email = :email 
            AND crypt(:password, pwhash) = pwhash;
        """, {"email": email, "password": password}).fetchone()
        if user:
            session["user"] = user
        return render_template("login_result.html", user=user)

    if session.get("user"):
        return render_template("login_result.html", user=session.get("user"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        password2 = request.form.get("password2")

        if password != password2:
            return render_template("signup_result.html", user=None, error="Passwords don't match")

        if db.execute("SELECT 1 FROM users WHERE email = :email", {"email": email }).fetchone():
            return render_template("signup_result.html", user=None, error="User already exists")

        try:
            db.execute("""
                INSERT INTO users (email, pwhash)
                    VALUES (:email, crypt(:password, gen_salt('bf', 8)));
            """, { "email": email, "password": password })
            db.commit()
        except Exception as e:
            print(e)
            return render_template("signup_result.html", user=None, error=e)
        user = db.execute("""
            SELECT id, email
            FROM users
            WHERE email = :email
            AND crypt(:password, pwhash) = pwhash;
        """, {"email": email, "password": password}).fetchone()
        if user:
            session["user"] = user
            return render_template("signup_result.html", user=session.get("user"), error=None)
        else:
            return render_template("signup_result.html", user=None, error="Problem during registration")
    
    else:
        return render_template("signup.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        q = request.form.get("q")
        books = db.execute("""
            SELECT b.isbn, b.title, a.name author, b.year_pub,
                (SELECT COUNT(*) FROM reviews r WHERE r.book_id = b.id) reviews_count
            FROM books b JOIN authors a ON b.author_id = a.id
            WHERE 
                b.isbn ILIKE :q
                OR b.title ILIKE :q
                OR a.name ILIKE :q
            ORDER BY a.name, b.year_pub
            LIMIT 100;
        """, {"q": f'%{q}%'}).fetchall()
        
        return render_template("search_results.html", q=q, books=books)
    
    return render_template("search_form.html")

@app.route("/book/<string:isbn>")
def book(isbn):
    book = db.execute("""
        SELECT b.id, b.isbn, b.title, a.name author, b.year_pub
        FROM books b
        JOIN authors a ON b.author_id = a.id
        WHERE b.isbn = :isbn;
    """, { "isbn": isbn }).fetchone()

    reviews = db.execute("""
        SELECT r.id review_id, u.email, r.rating, r.review
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        JOIN books b ON r.book_id = b.id
        WHERE b.isbn = :isbn;
    """, { "isbn": isbn }).fetchall()

    res = requests.get(GR_URL, params={ "key": GR_KEY, "isbns": isbn })
    goodread = { "success": False }
    if res.status_code == 200:
        goodread = { "success": True, "result": res.json()["books"][0]}

    already_reviewed = session["user"]["email"] in [review.email for review in reviews]

    return render_template("book.html", book=book, reviews=reviews, already_reviewed=already_reviewed, goodread=goodread)

@app.route("/post-review", methods=["POST"])
def post_review():
    book_id = request.form.get("book_id")
    isbn = request.form.get("isbn")
    rating = request.form.get("rating")
    review = request.form.get("review")

    user_id = session["user"]["id"]
    
    db.execute("""
        INSERT INTO reviews (user_id, book_id, rating, review)
            VALUES (:user_id, :book_id, :rating, :review);
    """, { "user_id": user_id, "book_id": book_id, "rating": rating, "review": review })
    db.commit()

    return redirect(url_for('book', isbn=isbn))

@app.route("/delete-review", methods=["POST"])
def delete_review():
    review_id = request.form.get("review_id")
    isbn = request.form.get("isbn")
    user_id = session["user"]["id"]
    db.execute("""
        DELETE FROM reviews
        WHERE user_id = :user_id AND id = :review_id
    """, { "user_id": user_id, "review_id": review_id })
    db.commit()

    return redirect(url_for('book', isbn=isbn))

@app.route("/api/book/<string:isbn>")
def book_api(isbn):
    """Returns details about a book"""
    """
    {
        "title": "Memory",
        "author": "Doug Lloyd",
        "year": 2015,
        "isbn": "1632168146",
        "review_count": 28,
        "average_score": 5.0
    }
    """
    # Retrieve book details from database
    book = db.execute("""
        SELECT 
            b.id, b.isbn, b.title, a.name author, b.year_pub
        FROM books b
        JOIN authors a ON b.author_id = a.id
        WHERE b.isbn = :isbn;
    """, { "isbn": isbn }).fetchone()

    if not book:
        return jsonify({"error": "Book not found"}), 404

    reviews = db.execute("""
        SELECT COUNT(*) review_count, AVG(rating::double precision) average_score
        FROM reviews
        WHERE book_id = :book_id
    """, { "book_id": book.id }).fetchone()

    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year_pub,
        "isbn": book.isbn,
        "review_count": reviews.review_count,
        "average_score": reviews.average_score 
    })
    