import datetime

from werkzeug.security import generate_password_hash

from app import app, get_db, init_db  # adjust imports if needed


def seed():
    with app.app_context():
        db = get_db()



        admin_pw = generate_password_hash('cccccc')

        db.execute(
            """
            INSERT INTO users (username, password_hash, role, name, email)
            VALUES (?, ?, ?, ?, ?)
            """,
            ('admin', admin_pw, 'admin', 'League Admin', 'admin@example.com')
        )

        admin_row = db.execute(
            "SELECT id FROM users WHERE username = ?",
            ('admin',)
        ).fetchone()

        admin_id = admin_row['id']

        db.execute(
            """
            INSERT INTO leagues (league_name, sport, max_teams, admin, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ('NBA G League', 'Basketball', 32, admin_id, 'active')
        )

        league_row = db.execute(
            "SELECT id FROM leagues WHERE league_name = ?",
            ('NBA G League',)
        ).fetchone()

        league_id = league_row['id']

        g_league_teams = [
            "Agua Caliente Clippers",
            "Austin Spurs",
            "Birmingham Squadron",
            "Capital City Go-Go",
            "Cleveland Charge",
            "College Park Skyhawks",
            "Delaware Blue Coats",
            "Fort Wayne Mad Ants",
            "Greensboro Swarm",
            "G League Ignite",
            "Grand Rapids Gold",
            "Iowa Wolves",
            "Lakeland Magic",
            "Long Island Nets",
            "Maine Celtics",
            "Memphis Hustle",
            "Motor City Cruise",
            "Oklahoma City Blue",
            "Ontario Clippers",
            "Raptors 905",
            "Rio Grande Valley Vipers",
            "Santa Cruz Warriors",
            "Sioux Falls Skyforce",
            "South Bay Lakers",
            "Stockton Kings",
            "Texas Legends",
            "Westchester Knicks",
            "Windy City Bulls",
            "Wisconsin Herd",
            "Mexico City Capitanes",
        ]

        for team_name in g_league_teams:
            db.execute(
                """
                INSERT INTO teams (name, league_id, team_manager)
                VALUES (?, ?, ?)
                """,
                (team_name, league_id, admin_id)
            )

        today = datetime.date.today()

        team_rows = db.execute(
            "SELECT id FROM teams WHERE league_id = ? LIMIT 2",
            (league_id,)
        ).fetchall()

        # if len(team_rows) == 2:
        #     home_team_id = team_rows[0]['id']
        #     away_team_id = team_rows[1]['id']
        #     db.execute(
        #         """
        #         INSERT INTO games (
        #             league_id,
        #             home_team_id,
        #             away_team_id,
        #             home_score,
        #             away_score,
        #             game_date
        #         ) VALUES (?, ?, ?, ?, ?, ?)
        #         """,
        #         (league_id, home_team_id, away_team_id, 110, 102, today)
        #     )

        db.commit()
        print("Database seeded with NBA G League and teams.")


if __name__ == '__main__':
    seed()
