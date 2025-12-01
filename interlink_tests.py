import os
import unittest
import tempfile
import app as interlink
from werkzeug.security import generate_password_hash


class InterlinkTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, interlink.app.config['DATABASE'] = tempfile.mkstemp()
        interlink.app.testing = True
        self.app = interlink.app.test_client()
        with interlink.app.app_context():
            interlink.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(interlink.app.config['DATABASE'])

# LEAGUE CREATION
    def test_create_league_stores_in_db(self):
        self.app.post('/league_creation', data=dict(
            league_name='Test League',
            sport='Basketball',
            max_teams='8'
        ), follow_redirects=True)

        with interlink.app.app_context():
            db = interlink.get_db()
            league = db.execute(
                'SELECT league_name, sport, max_teams FROM leagues WHERE league_name = ?',
                ('Test League',)
            ).fetchone()

            assert league is not None
            assert league['league_name'] == 'Test League'
            assert league['sport'] == 'Basketball'
            assert league['max_teams'] == 8

# TEAM CREATION
    def test_team_creation_shows_league_options(self):
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('League One', 'Soccer', 10))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('League Two', 'Basketball', 8))
            db.commit()

        rv = self.app.get('/team-creation')
        assert b'League One' in rv.data
        assert b'League Two' in rv.data

    def test_create_team_stores_in_db(self):
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                       ('user', generate_password_hash('123'), 'real name',' test@email.com'))
            db.commit()

        self.app.post('/login', data=dict(
            username='user',
            password='123'
        ))

        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Soccer', 10))
            db.commit()

        self.app.post('/create_team', data=dict(
            name='Test Team',
            manager='Test Manager',
            league='Test League'
        ), follow_redirects=True)

        with interlink.app.app_context():
            db = interlink.get_db()
            team = db.execute(
                'SELECT name, team_manager, league_id FROM teams WHERE name = ?',
                ('Test Team',)
            ).fetchone()

            assert team is not None
            assert team['name'] == 'Test Team'
            assert team['team_manager'] == 'Test Manager'
            assert team['league_id'] is not None

# SCORE TESTS
    def test_submit_score_requires_login(self):
        rv = self.app.get('/submit_score', follow_redirects=True)
        assert b'Please log in' in rv.data

    def test_submit_score_page_loads_with_leagues(self):
        # Create user and login
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Basketball', 8))
            db.commit()

        self.app.post('/login', data=dict(
            username='testuser',
            password='password'
        ))

        rv = self.app.get('/submit_score')
        assert b'Test League' in rv.data
        assert b'Select League' in rv.data

    def test_submit_score_shows_teams_when_league_selected(self):
        # Setup: create user, login, create league and teams
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Basketball', 8))
            db.commit()

            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team A', 'Manager A', league_id))
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team B', 'Manager B', league_id))
            db.commit()

        self.app.post('/login', data=dict(
            username='testuser',
            password='password'
        ))

        with interlink.app.app_context():
            db = interlink.get_db()
            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]

        rv = self.app.get(f'/submit_score?league_selected={league_id}')
        assert b'Team A' in rv.data
        assert b'Team B' in rv.data

    def test_submit_score_stores_in_db(self):
        # Setup
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Basketball', 8))
            db.commit()

            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team A', 'Manager A', league_id))
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team B', 'Manager B', league_id))
            db.commit()

            home_team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Team A',)).fetchone()[0]
            away_team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Team B',)).fetchone()[0]

        self.app.post('/login', data=dict(
            username='testuser',
            password='password'
        ))

        # Submit score
        self.app.post('/submit_score', data=dict(
            league_selected=league_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score='85',
            away_score='72',
            game_date='2025-01-15'
        ), follow_redirects=True)

        # Verify
        with interlink.app.app_context():
            db = interlink.get_db()
            game = db.execute(
                'SELECT league_id, home_team_id, away_team_id, home_score, away_score, game_date FROM games WHERE home_team_id = ?',
                (home_team_id,)
            ).fetchone()

            assert game is not None
            assert game['league_id'] == league_id
            assert game['home_score'] == 85
            assert game['away_score'] == 72
            assert game['game_date'] == '2025-01-15'

    def test_submit_score_rejects_non_numeric_scores(self):
        # Setup
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Basketball', 8))
            db.commit()

            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team A', 'Manager A', league_id))
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team B', 'Manager B', league_id))
            db.commit()

            home_team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Team A',)).fetchone()[0]
            away_team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Team B',)).fetchone()[0]

        self.app.post('/login', data=dict(
            username='testuser',
            password='password'
        ))

        rv = self.app.post('/submit_score', data=dict(
            league_selected=league_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score='abc',
            away_score='72',
            game_date='2025-01-15'
        ), follow_redirects=True)

        assert b'Scores must be numbers' in rv.data

    def test_submit_score_rejects_same_teams(self):
        # Setup
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Basketball', 8))
            db.commit()

            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('Team A', 'Manager A', league_id))
            db.commit()

            team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Team A',)).fetchone()[0]

        self.app.post('/login', data=dict(
            username='testuser',
            password='password'
        ))

        rv = self.app.post('/submit_score', data=dict(
            league_selected=league_id,
            home_team_id=team_id,
            away_team_id=team_id,
            home_score='85',
            away_score='72',
            game_date='2025-01-15'
        ), follow_redirects=True)

        assert b'Teams must be different' in rv.data

# JOIN TEAM TESTS
    def test_join_team_form_loads_with_sport_selection(self):
       rv = self.app.get('/join_team_form?sport=Basketball')
       assert b'Select Sport' in rv.data
       assert b'Basketball' in rv.data


    def test_join_team_form_shows_leagues_for_sport(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Basketball League 1', 'Basketball', 8))
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Basketball League 2', 'Basketball', 10))
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Soccer League', 'Soccer', 12))
           db.commit()


       rv = self.app.get('/join_team_form?sport=Basketball')
       assert b'Basketball League 1' in rv.data
       assert b'Basketball League 2' in rv.data
       assert b'Soccer League' not in rv.data


    def test_join_team_form_shows_teams_when_league_selected(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Basketball League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Team 1', 'Manager 1', league_id))
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Team 2', 'Manager 2', league_id))
           db.commit()


       rv = self.app.get('/join_team_form?sport=Basketball&league_select=Basketball League')
       assert b'Team 1' in rv.data
       assert b'Team 2' in rv.data


    def test_join_team_submit_requires_login(self):
       rv = self.app.post('/join_team_submit', data=dict(
           team='Test Team'
       ), follow_redirects=True)
       assert b'Please log in to join a team!' in rv.data


    def test_join_team_submit_stores_membership(self):
       # Setup
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Test League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Test Team', 'Manager', league_id))
           db.commit()


       self.app.post('/login', data=dict(
           username='testuser',
           password='password'
       ))


       # Join team
       self.app.post('/join_team_submit', data=dict(
           team='Test Team'
       ), follow_redirects=True)


       # Verify
       with interlink.app.app_context():
           db = interlink.get_db()
           user_id = db.execute('SELECT id FROM users WHERE username = ?', ('testuser',)).fetchone()[0]
           team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Test Team',)).fetchone()[0]


           membership = db.execute(
               'SELECT * FROM memberships WHERE user_id = ? AND team_id = ?',
               (user_id, team_id)
           ).fetchone()


           assert membership is not None


    def test_join_team_submit_prevents_duplicate_membership(self):
       # Setup
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com'))
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Test League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Test Team', 'Manager', league_id))
           db.commit()


           user_id = db.execute('SELECT id FROM users WHERE username = ?', ('testuser',)).fetchone()[0]
           team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Test Team',)).fetchone()[0]


           # Add initial membership
           db.execute('INSERT INTO memberships (user_id, team_id) VALUES (?, ?)', (user_id, team_id))
           db.commit()


       self.app.post('/login', data=dict(
           username='testuser',
           password='password'
       ))


       # Try to join again
       rv = self.app.post('/join_team_submit', data=dict(
           team='Test Team'
       ), follow_redirects=True)


       assert b'You are already a member of this team!' in rv.data


    def test_get_roster_returns_team_members(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           # Create users
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('user1', generate_password_hash('pass'), 'Player One', 'p1@test.com'))
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('user2', generate_password_hash('pass'), 'Player Two', 'p2@test.com'))


           # Create league and team
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Test League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Test Team', 'Manager', league_id))
           db.commit()


           # Add memberships
           user1_id = db.execute('SELECT id FROM users WHERE username = ?', ('user1',)).fetchone()[0]
           user2_id = db.execute('SELECT id FROM users WHERE username = ?', ('user2',)).fetchone()[0]
           team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Test Team',)).fetchone()[0]


           db.execute('INSERT INTO memberships (user_id, team_id) VALUES (?, ?)', (user1_id, team_id))
           db.execute('INSERT INTO memberships (user_id, team_id) VALUES (?, ?)', (user2_id, team_id))
           db.commit()


           # Test get_roster function
           roster = interlink.get_roster('Test Team')


           assert len(roster) == 2
           assert 'Player One' in roster
           assert 'Player Two' in roster

if __name__ == '__main__':
    unittest.main()
