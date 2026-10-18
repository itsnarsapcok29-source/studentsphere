"""Create the SQLite database and tables.  Usage: python -m scripts.init_db"""
from app.database import engine, init_db


def main() -> None:
    init_db()
    print(f"Database ready: {engine.url.render_as_string(hide_password=True)}")


if __name__ == "__main__":
    main()
