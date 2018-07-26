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
    db.execute("""
        CREATE TABLE books_tmp (
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
        )
    """)
    with open("books.csv", "r") as f:
        reader = csv.reader(f)
        # skip header
        next(reader)

        for isbn, title, author, year in reader:
            db.execute("INSERT INTO books_tmp (isbn, title, author, year_pub) VALUES (:isbn, :title, :author, :year_pub)",
                        {"isbn": isbn, "title": title, "author": author, "year_pub": year})
        
        db.execute("INSERT INTO authors (name) SELECT DISTINCT author FROM books_tmp;")
        db.execute("""
            INSERT INTO books (isbn, title, author_id, year_pub)
                SELECT b.isbn, b.title, a.id author_id, b.year_pub
                FROM books_tmp b JOIN authors a ON b.author = a.name;  
        """)
        db.execute("DROP TABLE books_tmp;")

    db.commit()


if __name__ == "__main__":
    main()
