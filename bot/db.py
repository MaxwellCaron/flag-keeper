import os
import csv
import sqlite3
from loguru import logger


DATABASE_PATH = os.environ.get('DATABASE_PATH')


def db_to_dict(cursor, row) -> dict | None:
    return {column[0]: row[i] for i, column in enumerate(cursor.description)} if row else None


class FlagAlreadySubmitted(Exception):
    def __init__(self, message: str = 'This flag has already been submitted by this team.'):
        self.message = message
        super().__init__(self.message)


class FlagsDatabase:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path

    def initialize_database(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS flags (
            flag TEXT PRIMARY KEY,
            team INTEGER,
            channel_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS found (
            flag TEXT,
            team INTEGER,
            UNIQUE(flag, team)
        );
        """)
        conn.commit()
        conn.close()

    def import_flags(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        with open('flags.csv', 'r') as file:
            csv_reader = csv.reader(file)

            for row in csv_reader:
                flag, team, channel_id = row
                try:
                    cursor.execute(
                        'INSERT OR IGNORE INTO flags (flag, team, channel_id) VALUES (?, ?, ?)',
                        (flag, team, channel_id)
                    )
                except sqlite3.Error as e:
                    logger.error(f"Error importing flag: {str(e)}")

        conn.commit()
        conn.close()

    def get_team(self, flag: str) -> dict | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM flags WHERE flag = ?',
            (flag,)
        )
        team = cursor.fetchone()
        conn.close()

        return db_to_dict(cursor, team) if team else None

    def submit_flag(self, flag: str, team: int) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM found WHERE flag = ? AND team = ?',
            (flag, team)
        )

        found = cursor.fetchone()
        if found:
            raise FlagAlreadySubmitted

        cursor.execute(
            'INSERT INTO found (flag, team) VALUES (?, ?)',
            (flag, team)
        )
        conn.commit()
        conn.close()

    def get_submitted_flags(self) -> dict | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT flags.team, COUNT(DISTINCT found.flag) as flags
        FROM flags
        LEFT JOIN found ON flags.team = found.team
        GROUP BY flags.team
        ORDER BY flags.team;
        """)
        teams = cursor.fetchall()
        conn.close()

        return teams if teams else None

    def get_found_flags(self) -> dict | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT flags.team, COUNT(*) as flags
        FROM found
        JOIN flags ON found.flag = flags.flag
        WHERE found.team != flags.team
        GROUP BY flags.team;
        """)
        teams = cursor.fetchall()
        conn.close()

        return teams if teams else None


if __name__ == '__main__':
    pass
