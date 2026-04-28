"""
scripts/seed_sample_db.py
──────────────────────────
Creates a sample SQLite database that mirrors the Spider 'concert_singer'
schema so the team can run the API locally without downloading the full
Spider dataset.

Usage:
    python scripts/seed_sample_db.py
"""

import os
import sqlite3
from pathlib import Path

DB_DIR = Path("./data/databases/concert_singer")
DB_PATH = DB_DIR / "concert_singer.sqlite"


def create_and_seed():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS singer_in_concert;
        DROP TABLE IF EXISTS concert;
        DROP TABLE IF EXISTS stadium;
        DROP TABLE IF EXISTS singer;

        CREATE TABLE singer (
            singer_id   INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            country     TEXT,
            song_name   TEXT,
            song_release_year TEXT,
            age         INTEGER,
            is_male     INTEGER
        );

        CREATE TABLE stadium (
            stadium_id  INTEGER PRIMARY KEY,
            location    TEXT,
            name        TEXT,
            capacity    INTEGER,
            highest     INTEGER,
            lowest      INTEGER,
            average     INTEGER
        );

        CREATE TABLE concert (
            concert_id   INTEGER PRIMARY KEY,
            concert_name TEXT,
            theme        TEXT,
            stadium_id   INTEGER,
            year         TEXT,
            FOREIGN KEY (stadium_id) REFERENCES stadium(stadium_id)
        );

        CREATE TABLE singer_in_concert (
            concert_id INTEGER,
            singer_id  INTEGER,
            PRIMARY KEY (concert_id, singer_id),
            FOREIGN KEY (concert_id) REFERENCES concert(concert_id),
            FOREIGN KEY (singer_id)  REFERENCES singer(singer_id)
        );
    """)

    # Seed data
    cur.executemany(
        "INSERT INTO singer VALUES (?,?,?,?,?,?,?)",
        [
            (1, "Justin Brown",   "USA",       "Hey Oh",         "2012", 29, 1),
            (2, "Camila Cabello", "USA",       "Never Be Same",  "2018", 21, 0),
            (3, "Ed Sheeran",     "UK",        "Shape of You",   "2017", 27, 1),
            (4, "Adele",          "UK",        "Hello",          "2015", 30, 0),
            (5, "BTS RM",         "South Korea","Dynamite",      "2020", 26, 1),
        ],
    )

    cur.executemany(
        "INSERT INTO stadium VALUES (?,?,?,?,?,?,?)",
        [
            (1, "New York, USA",   "Madison Square Garden", 20000, 18000, 5000, 11000),
            (2, "London, UK",      "The O2 Arena",          20000, 19000, 8000, 13000),
            (3, "Seoul, S. Korea", "Olympic Stadium",       69950, 60000, 30000, 45000),
        ],
    )

    cur.executemany(
        "INSERT INTO concert VALUES (?,?,?,?,?)",
        [
            (1, "Summerfest",    "Pop",  1, "2014"),
            (2, "World Tour",    "Rock", 2, "2015"),
            (3, "K-Pop Night",   "Pop",  3, "2021"),
            (4, "Acoustic Vibes","Folk", 2, "2019"),
        ],
    )

    cur.executemany(
        "INSERT INTO singer_in_concert VALUES (?,?)",
        [
            (1, 1), (1, 2),
            (2, 3), (2, 4),
            (3, 5),
            (4, 3),
        ],
    )

    conn.commit()
    conn.close()
    print(f"Sample database created at: {DB_PATH}")


if __name__ == "__main__":
    create_and_seed()
