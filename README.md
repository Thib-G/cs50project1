# Project 1

Web Programming with Python and JavaScript

## Installation

Follow the instructions on the [project 1 page](https://docs.cs50.net/web/2018/w/projects/1/project1.html) to create a PostgreSQL database on Heroku and to install Python.

Note: I'm using Python 3.6 on Windows with Anaconda. If you are on Linux or MacOS, you may need to replace `pip` and `python` with `pip3` and `python3` to use Python 3.x.

1. Install all `pip` dependencies:

```
pip install -r requirements.txt 
```

1. Set `export DATABASE_URL=YOUR_CONNECTION_STRING FROM HEROKU` and run `import.py` to generate the tables in the database and to import the list of books.

```
python import.py
```


3. Edit `launch.sh-dist` with your credentials and rename it to `launch.sh`. I'm using Git Bash on Windows to run this script. You may need to run `chmod` to make it executable.

```
chmod +x launch.sh
```

4. Run the shell script to run the Flask server with its environnement variables. On Windows, you need a `bash` shell to be able to run it.

```
./launch.sh
```

### Website

1. Go to http://localhost:5000/ to access the site.
   
2. Log in with `thib@example.com` and `password123`. You can also sign up with a new user. You will be redirected to a search page. Enter your term. In the search results, click on the book's title to see the book's page.
   
### API
Use the api endpoint `/api/book/[isbn]` to search for a book.

#### Example:
`/api/book/1600963943` returns
```Json
{
    "author": "Agatha Christie",
    "average_score": 3.66666666666667,
    "isbn": "1600963943",
    "review_count": 3,
    "title": "The Secret Adversary",
    "year": 1922
}
```