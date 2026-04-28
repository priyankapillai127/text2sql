"""
scripts/generate_sample_examples.py
─────────────────────────────────────
Generates a small spider_train.json with hand-crafted (question, SQL) pairs
so the team can build and test the RAG index without the full Spider download.

Usage:
    python scripts/generate_sample_examples.py
"""

import json
from pathlib import Path

EXAMPLES = [
    {"question": "How many singers are there?",            "query": "SELECT count(*) FROM singer",                                         "db_id": "concert_singer"},
    {"question": "List all singer names.",                 "query": "SELECT name FROM singer",                                             "db_id": "concert_singer"},
    {"question": "What are the names of the stadiums?",    "query": "SELECT name FROM stadium",                                            "db_id": "concert_singer"},
    {"question": "How many concerts are held each year?",  "query": "SELECT year, count(*) FROM concert GROUP BY year",                    "db_id": "concert_singer"},
    {"question": "Find singers from USA.",                 "query": "SELECT name FROM singer WHERE country = 'USA'",                       "db_id": "concert_singer"},
    {"question": "What is the average age of singers?",    "query": "SELECT avg(age) FROM singer",                                        "db_id": "concert_singer"},
    {"question": "Which stadium has the highest capacity?","query": "SELECT name FROM stadium ORDER BY capacity DESC LIMIT 1",            "db_id": "concert_singer"},
    {"question": "List concerts with their stadium names.","query": "SELECT c.concert_name, s.name FROM concert c JOIN stadium s ON c.stadium_id = s.stadium_id", "db_id": "concert_singer"},
    {"question": "How many singers performed in concert 1?","query": "SELECT count(*) FROM singer_in_concert WHERE concert_id = 1",       "db_id": "concert_singer"},
    {"question": "Find all female singers.",               "query": "SELECT name FROM singer WHERE is_male = 0",                          "db_id": "concert_singer"},
    {"question": "What is the maximum stadium capacity?",  "query": "SELECT max(capacity) FROM stadium",                                  "db_id": "concert_singer"},
    {"question": "List all concert themes.",               "query": "SELECT DISTINCT theme FROM concert",                                 "db_id": "concert_singer"},
]

OUT_PATH = Path("./data/spider_train.json")


def generate():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(EXAMPLES, f, indent=2)
    print(f"Sample training file written to: {OUT_PATH} ({len(EXAMPLES)} examples)")


if __name__ == "__main__":
    generate()
