import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    """Init tables and seed books.csv"""
    db.execute("DROP TABLE IF EXISTS books_tmp;")
    db.execute("DROP TABLE IF EXISTS books;")
    db.execute("DROP TABLE IF EXISTS authors;")
    db.execute("DROP TABLE IF EXISTS users;")
    db.execute("DROP TABLE IF EXISTS reviews;")
    db.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    db.execute("""
        CREATE TEMP TABLE books_tmp (
            id serial PRIMARY KEY,
            isbn text NOT NULL UNIQUE CHECK (char_length(isbn) = 10),
            title text NOT NULL,
            author text NOT NULL,
            year_pub int NOT NULL
        );""")
    db.execute("""
        CREATE TABLE authors (
            id serial PRIMARY KEY,
            name text NOT NULL
        );
    """)
    db.execute("""
        CREATE TABLE books (
            id serial PRIMARY KEY,
            isbn text NOT NULL UNIQUE CHECK (char_length(isbn) = 10),
            title text NOT NULL,
            author_id int REFERENCES authors(id),
            year_pub int NOT NULL
        );
    """)
    db.execute("""
        CREATE TABLE users (
            id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            email text NOT NULL UNIQUE,
            pwhash text NOT NULL
        );
    """)
    db.execute("""
        CREATE TABLE reviews (
            id serial PRIMARY KEY,
            user_id uuid REFERENCES users(id),
            book_id int REFERENCES books(id),
            rating int NOT NULL CHECK (rating >= 1 AND rating <= 5),
            review text NOT NULL
        );
    """)
    users = [
        { "email": "thib@example.com", "password": "password123" },
        { "email": "pom@example.com", "password": "meuhmeuh" }
    ]
    for user in users:
        db.execute("""
            INSERT INTO users (email, pwhash)
                VALUES (:email, crypt(:password, gen_salt('bf', 8)));
        """, { "email": user.get("email"), "password": user.get("password") })

    with open("books.csv", "r") as f:
        reader = csv.reader(f)
        # skip header
        next(reader)

        for isbn, title, author, year in reader:
            db.execute("""
                INSERT INTO books_tmp (isbn, title, author, year_pub)
                    VALUES (:isbn, :title, :author, :year_pub);
                """,
                {"isbn": isbn, "title": title, "author": author, "year_pub": year})
        
    db.execute("INSERT INTO authors (name) SELECT DISTINCT author FROM books_tmp;")
    db.execute("""
        INSERT INTO books (isbn, title, author_id, year_pub)
            SELECT b.isbn, b.title, a.id author_id, b.year_pub
            FROM books_tmp b JOIN authors a ON b.author = a.name
            ORDER BY b.id;  
    """)

    db.commit()


if __name__ == "__main__":
    main()
