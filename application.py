import os

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        q = request.form.get("q")
        books = db.execute("""
            SELECT b.isbn, b.title, a.name author, b.year_pub
            FROM books b JOIN authors a ON b.author_id = a.id
            WHERE 
                b.isbn ILIKE :q
                OR b.title ILIKE :q
                OR a.name ILIKE :q;
        """, {"q": f'%{q}%'}).fetchall()
        return render_template("search_results.html", q=q, books=books)
    
    return render_template("search_form.html")


