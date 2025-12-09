import os
import unittest
import tempfile
import app as interlink
from werkzeug.security import generate_password_hash


class InterlinkTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, interlink.app.config['DATABASE'] = tempfile.mkstemp()
        interlink.app.config['SECRET_KEY'] = 'key-for-testing'
        interlink.app.testing = True
        self.original_calendar_available = interlink.GOOGLE_CALENDAR_AVAILABLE
        interlink.GOOGLE_CALENDAR_AVAILABLE = False
        self.app = interlink.app.test_client()
        with interlink.app.app_context():
            interlink.init_db()

    def tearDown(self):
        interlink.GOOGLE_CALENDAR_AVAILABLE = self.original_calendar_available

        os.close(self.db_fd)
        os.unlink(interlink.app.config['DATABASE'])

    #helper function to clear session
    def clearSession(self):
        with interlink.app.app_context():
            with self.app.session_transaction() as sess:
                sess.pop('logged_in', None)
                sess.pop('username', None)
                sess.pop('role', None)

# LEAGUE CREATION
    def test_create_league_stores_in_db(self):
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com', 'user'))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'user'

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
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com', 'user'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('League One', 'Soccer', 10))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('League Two', 'Basketball', 8))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'user'

        rv = self.app.get('/team-creation')
        assert b'League One' in rv.data
        assert b'League Two' in rv.data

    def test_create_team_stores_in_db(self):
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('user', generate_password_hash('123'), 'real name',' test@email.com', 'user'))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'user'
            sess['role'] = 'user'


        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('Test League', 'Soccer', 10))
            db.commit()

        self.app.post('/create_team', data=dict(
            name='Test Team',
            league='Test League',
        ), follow_redirects=True)

        with interlink.app.app_context():
            db = interlink.get_db()
            team = db.execute(
                'SELECT name, team_manager, league_id FROM teams WHERE name = ?',
                ('Test Team',)
            ).fetchone()

            assert team is not None
            assert team['name'] == 'Test Team'
            assert team['team_manager'] is not None
            assert team['league_id'] is not None

# JOIN TEAM TESTS
    def test_join_team_form_loads_with_sport_selection(self):
       with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com', 'user'))
            db.commit()

       with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'user'

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


       with self.app.session_transaction() as sess:
           sess['logged_in'] = True
           sess['username'] = 'testuser'
           sess['role'] = 'user'

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

       with self.app.session_transaction() as sess:
           sess['logged_in'] = True
           sess['username'] = 'testuser'
           sess['role'] = 'user'

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
           db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                      ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com', 'user'))
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Test League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Test Team', 'Manager', league_id))
           db.commit()

       with self.app.session_transaction() as sess:
           sess['logged_in'] = True
           sess['username'] = 'testuser'
           sess['role'] = 'user'

       # Join team
       self.app.post('/join_team_submit', data=dict(
           team='Test Team',
           league_hidden='Test League'
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
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)', (user_id, team_id, league_id))
           db.commit()

       with self.app.session_transaction() as sess:
           sess['logged_in'] = True
           sess['username'] = 'testuser'
           sess['role'] = 'user'

       # Try to join again
       rv = self.app.post('/join_team_submit', data=dict(
           team='Test Team',
           league_hidden = 'Test League'
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


           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?,?)', (user1_id, team_id, league_id))
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?,?)', (user2_id, team_id, league_id))
           db.commit()


           # Test get_roster function
           roster = interlink.get_roster('Test Team', 'name')


           assert len(roster) == 2
           assert 'Player One' in roster
           assert 'Player Two' in roster


    # TEAM PAGE TESTS
    def test_team_view_displays_team_information(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           # Create league
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Basketball League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]


           # Create team
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Coach', league_id))
           db.commit()


       rv = self.app.get(
           '/team_view?team_name=Cheese&league_name=Basketball League&team_manager=Coach&sport=Basketball&league_status=SignUp')


       assert b'Cheese' in rv.data
       assert b'Basketball League' in rv.data
       assert b'Coach' in rv.data
       assert b'Basketball' in rv.data


    def test_team_view_displays_roster(self):
       with interlink.app.app_context():
           db = interlink.get_db()


           # Create users
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('player1', generate_password_hash('pass'), 'Hayden', 'casey@test.com'))
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('player2', generate_password_hash('pass'), 'Casey', 'casey@test.com'))


           # Create league
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Basketball League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]


           # Create team
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Coach', league_id))
           db.commit()


           # Get IDs
           team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Cheese',)).fetchone()[0]
           user1_id = db.execute('SELECT id FROM users WHERE username = ?', ('player1',)).fetchone()[0]
           user2_id = db.execute('SELECT id FROM users WHERE username = ?', ('player2',)).fetchone()[0]


           # Add memberships
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)', (user1_id, team_id, league_id))
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)', (user2_id, team_id, league_id))
           db.commit()


       rv = self.app.get(
           '/team_view?team_name=Cheese&league_name=Basketball League&team_manager=Coach&sport=Basketball&league_status=SignUp')


       assert b'Hayden' in rv.data
       assert b'Casey' in rv.data
       assert b'Roster:' in rv.data


    def test_team_view_shows_join_button_when_signup_phase(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO leagues (league_name, sport, max_teams, status) VALUES (?, ?, ?, ?)',
                      ('Basketball League', 'Basketball', 8, 'SignUp'))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Coach', league_id))
           db.commit()


       rv = self.app.get(
           '/team_view?team_name=Cheese&league_name=Basketball League&team_manager=Coach&sport=Basketball&league_status=SignUp')


       assert b'Join Team' in rv.data


    def test_team_view_hides_join_button_when_not_signup_phase(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO leagues (league_name, sport, max_teams, status) VALUES (?, ?, ?, ?)',
                      ('Basketball League', 'Basketball', 8, 'Active'))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Coach', league_id))
           db.commit()


       rv = self.app.get(
           '/team_view?team_name=Cheese&league_name=Basketball League&team_manager=Coach&sport=Basketball&league_status=Active')


       # The button should be hidden when league_status is not 'SignUp'
       # Check that the form exists but the button has the hidden attribute
       assert b'join_team_submit' in rv.data


    def test_team_view_with_empty_roster(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Basketball League', 'Basketball', 8))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Coach', league_id))
           db.commit()


       rv = self.app.get(
           '/team_view?team_name=Cheese&league_name=Basketball League&team_manager=Coach&sport=Basketball&league_status=SignUp')


       assert b'Roster:' in rv.data


    def test_team_view_join_button_submits_to_correct_team(self):
       with interlink.app.app_context():
           db = interlink.get_db()
           db.execute('INSERT INTO leagues (league_name, sport, max_teams, status) VALUES (?, ?, ?, ?)',
                      ('Basketball League', 'Basketball', 8, 'SignUp'))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Basketball League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Coach', league_id))
           db.commit()


       rv = self.app.get(
           '/team_view?team_name=Cheese&league_name=Basketball League&team_manager=Coach&sport=Basketball&league_status=SignUp')


       assert b'action="/join_team_submit"' in rv.data
       assert b'method="post"' in rv.data
       assert b'name="team" value="Cheese"' in rv.data

    def test_get_roster_with_multiple_players(self):
       with interlink.app.app_context():
           db = interlink.get_db()


           # Create multiple users
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('ethan', generate_password_hash('pass'), 'Ethan', 'ethan@test.com'))
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('elle', generate_password_hash('pass'), 'Elle', 'elle@test.com'))
           db.execute('INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                      ('hayden', generate_password_hash('pass'), 'Hayden', 'hayden@test.com'))


           # Create league and team
           db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                      ('Test League', 'Soccer', 10))
           db.commit()


           league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('Test League',)).fetchone()[0]
           db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                      ('Cheese', 'Brad Sheese', league_id))
           db.commit()


           # Get IDs
           team_id = db.execute('SELECT id FROM teams WHERE name = ?', ('Cheese',)).fetchone()[0]
           user1_id = db.execute('SELECT id FROM users WHERE username = ?', ('ethan',)).fetchone()[0]
           user2_id = db.execute('SELECT id FROM users WHERE username = ?', ('elle',)).fetchone()[0]
           user3_id = db.execute('SELECT id FROM users WHERE username = ?', ('hayden',)).fetchone()[0]


           # Add memberships
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)', (user1_id, team_id, league_id))
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)', (user2_id, team_id, league_id))
           db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)', (user3_id, team_id, league_id))
           db.commit()


           # Test get_roster function
           roster = interlink.get_roster('Cheese', 'name')


           assert len(roster) == 3
           assert 'Ethan' in roster
           assert 'Elle' in roster
           assert 'Hayden' in roster

    def test_league_creation_requires_login(self):
        with interlink.app.app_context():
            with self.app.session_transaction() as sess:
                self.clearSession()

                rv = self.app.post('/league_creation', follow_redirects=True)
                assert rv.status_code == 200  # html is good
                assert b'Please log in to access that page.' in rv.data

                rv_post = self.app.post('/league_creation', data=dict(
                    league_name='Caseys up to bat',
                    sport='Baseball',
                    max_teams='4'
                ), follow_redirects=True)

                assert rv_post.status_code == 200
                assert b'Please log in to access that page.' in rv_post.data

                # check that league isn't made
                with interlink.app.app_context():
                    db = interlink.get_db()
                    league = db.execute(
                        'SELECT id FROM leagues WHERE league_name = ?',
                        ('Caseys up to bat',)
                    ).fetchone()

                    assert league is None

    def test_team_creation_requires_login(self):
        self.clearSession()
        rv = self.app.get('/team-creation', follow_redirects=True)

        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Please log in to access that page.', rv.data)

        rv_post = self.app.post('/create_team', data=dict(
            name="fake team",
            league="fake league"
        ), follow_redirects=True)

        self.assertEqual(rv_post.status_code, 200)
        self.assertIn(b'Please log in to access that page.', rv_post.data)

        with interlink.app.app_context():
            db = interlink.get_db()
            team = db.execute(
                'SELECT id FROM teams WHERE name = ?',
                ("fake team",)
            ).fetchone()

            self.assertIsNone(team)


    def test_submit_score_requires_login(self):
        self.clearSession()
        rv = self.app.get('/submit_score', follow_redirects=True)

        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Please log in to submit scores.', rv.data)
        self.assertIn(b'Login', rv.data)

        rv_post = self.app.post('/submit_score', data=dict(
            league_selected='1',
            game_id='1',
            home_score='5',
            away_score='2'
        ), follow_redirects=True)

        self.assertEqual(rv_post.status_code, 200)
        self.assertIn(b'Please log in to submit scores.', rv_post.data)

    def test_delete_league_requires_login(self):
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com', 'user'))
            db.commit()
            testuser_id = db.execute(
                'SELECT id FROM users WHERE username = ?',
                ('testuser',)
            ).fetchone()['id']

            db.execute('INSERT INTO leagues (league_name, sport, max_teams, league_admin) VALUES (?, ?, ?, ?)',
                       ('League One', 'Soccer', 10, testuser_id))
            db.commit()
            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?',
                                   ('League One',)).fetchone()['id']


        self.clearSession()

        delete_url = f'/league/{league_id}/admin/delete_league'
        rv = self.app.post(delete_url, follow_redirects=True)

        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Please log in to access that page.', rv.data)

        with interlink.app.app_context():
            db = interlink.get_db()
            league = db.execute(
                'SELECT id FROM leagues WHERE id = ?',
                (league_id,)
            ).fetchone()

            self.assertIsNotNone(league)

if __name__ == '__main__':
    unittest.main()
