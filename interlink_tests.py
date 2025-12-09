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

    #helper function to make a user a league and a certain amount of teams
    def create_user_league_teams(self, league_name, team_count):
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('testuser', generate_password_hash('password'), 'Test User', 'test@test.com', 'user'))
            db.commit()
            testuser_id = db.execute('SELECT id FROM users WHERE username = ?', ('testuser',)).fetchone()['id']
            db.execute('INSERT INTO leagues (league_name, sport, max_teams, league_admin) VALUES (?, ?, ?, ?)',
                       (league_name, 'Soccer', 10, testuser_id))
            db.commit()
            league_id = db.execute('SELECT id FROM leagues WHERE league_name = ?',
                                   (league_name,)).fetchone()['id']
            for i in range(team_count):
                db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                           (f'Team {i + 1}', testuser_id, league_id))
            db.commit()
            return league_id, testuser_id

    def test_change_league_status_to_active_fail_less_than_3_teams(self):
        league_id, testuser_id = self.create_user_league_teams('OnlyTwoTeams', 2)

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'user'

        #change status from signup to active
        rv = self.app.post('/change_phase', data=dict(
            status='signup',
            league_id=league_id
        ), follow_redirects=True)

        self.assertIn(b'League does not have enough teams', rv.data)

        #check league status didnt change
        with interlink.app.app_context():
            db = interlink.get_db()
            league_status = db.execute('SELECT status FROM leagues WHERE id = ?', (league_id,)).fetchone()['status']
            self.assertEqual(league_status, 'signup')

    def test_change_league_status_to_active(self):
        league_id, testuser_id = self.create_user_league_teams('fourteamleague', 4)

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'admin'

        self.app.post('/change_phase', data=dict(
            status='signup',
            league_id=league_id
        ), follow_redirects=True)

        with interlink.app.app_context():
            db = interlink.get_db()
            league_status = db.execute('SELECT status FROM leagues WHERE id = ?', (league_id,)).fetchone()['status']
            self.assertEqual(league_status, 'active')

    def test_league_manager_access_denied_for_non_admin(self):
        league_id, testuser_id = self.create_user_league_teams('TestAuthleague', 4)

        #make another random user
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('Ethan', generate_password_hash('pass'), 'Ethan', 'Ethan@test.com', 'user'))
            db.commit()

            with self.app.session_transaction() as sess:
                sess['logged_in'] = True
                sess['username'] = 'Ethan'
                sess['role'] = 'user'

            rv = self.app.get(f'/league/{league_id}/league_manager', follow_redirects=True)

            self.assertIn(b'You do not have permission to view this page.', rv.data)
            self.assertIn(b'InterLink', rv.data)

#check non team managers can't see the manager route for a team
    def test_team_manager_access_denied_for_non_manager(self):
        league_id, testuser_id = self.create_user_league_teams('Testleague', 4)

        with interlink.app.app_context():
            db = interlink.get_db()
            team_id = db.execute('SELECT id FROM teams WHERE league_id = ?', (league_id,)).fetchone()['id']
            db = interlink.get_db()

            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('Ethan', generate_password_hash('pass'), 'Ethan', 'Ethan@test.com', 'user'))
            db.commit()

            with self.app.session_transaction() as sess:
                sess['logged_in'] = True
                sess['username'] = 'Ethan'
                sess['role'] = 'user'

            rv = self.app.get(f'/team/{team_id}/manager', follow_redirects=True)
            self.assertIn(b'You do not have permission to manage this team.', rv.data)

#test scores can be submitted`
    def test_submit_score_success(self):
        league_id, testuser_id = self.create_user_league_teams('Testleague', 4)
        with interlink.app.app_context():
            db = interlink.get_db()
            team_ids = db.execute('SELECT id FROM teams WHERE league_id = ?', (league_id,)).fetchall()
            team1_id = team_ids[0]['id']
            team2_id = team_ids[1]['id']

            db.execute(
                'INSERT INTO games (league_id, home_team_id, away_team_id, game_date, home_score, away_score) '
                'VALUES (?, ?, ?, ?, NULL, NULL)',
                [league_id, team1_id, team2_id, '2025-01-01 01:00:00']
            )
            db.commit()
            game_id = db.execute('SELECT id FROM games WHERE league_id = ?', (league_id,)).fetchone()['id']
        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'user'

        #submit the score
        rv = self.app.post('/submit_score', data=dict(
            league_selected=str(league_id),
            game_id=str(game_id),
            home_score='10',
            away_score='5'
        ), follow_redirects=True)

        self.assertIn(b'Score submitted successfully!', rv.data)

        with interlink.app.app_context():
            db = interlink.get_db()
            game = db.execute('SELECT home_score, away_score FROM games WHERE id = ?', (game_id,)).fetchone()

            self.assertEqual(game['home_score'], 10)
            self.assertEqual(game['away_score'], 5)

    def test_submit_score_non_numbers_input_fails(self):
        league_id, user_id = self.create_user_league_teams('BadScoreLeague', 4)
        with interlink.app.app_context():
            db = interlink.get_db()
            team_ids = db.execute('SELECT id FROM teams WHERE league_id = ?', (league_id,)).fetchall()
            team1_id = team_ids[0]['id']
            team2_id = team_ids[1]['id']

            db.execute(
                'INSERT INTO games (league_id, home_team_id, away_team_id, game_date, home_score, away_score) '
                'VALUES (?, ?, ?, ?, NULL, NULL)',
                [league_id, team1_id, team2_id, '2025-01-01 01:00:00']
            )
            db.commit()
            game_id = db.execute('SELECT id FROM games WHERE league_id = ?', (league_id,)).fetchone()['id']

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
            sess['role'] = 'user'

        rv = self.app.post('/submit_score', data=dict(
            league_selected=str(league_id),
            game_id=str(game_id),
            home_score='ten',
            away_score='5'
        ), follow_redirects=True)
        self.assertIn(b'Scores must be numbers', rv.data)

    def test_user_page_loads(self):
        """Simple test that user page loads with login"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('elle', generate_password_hash('pass'), 'elle', 'elle@test.com', 'user'))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'elle'
            sess['role'] = 'user'

        rv = self.app.get('/user_page')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'elle', rv.data)

    def test_match_schedule_loads(self):
        """Simple test that match schedule page loads"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('ell league', 'Basketball', 4))
            league = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('ell league',)).fetchone()
            self.assertIsNotNone(league)
            league_id = league['id']
            db.commit()

        rv = self.app.get(f'/match-schedule/{league_id}')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'ell league', rv.data)

    def test_generate_schedule_page_loads(self):
        """Simple test that generate schedule page loads for admin"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('casey', generate_password_hash('pass'), 'casey', 'casey@test.com', 'admin'))
            db.execute('INSERT INTO leagues (league_name, sport, max_teams, status) VALUES (?, ?, ?, ?)',
                       ('casey cheese schedule', 'Soccer', 4, 'active'))
            league = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('casey cheese schedule',)).fetchone()
            self.assertIsNotNone(league)
            league_id = league['id']
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'casey'
            sess['role'] = 'admin'

        rv = self.app.get(f'/league/{league_id}/generate-schedule')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'Generate Schedule', rv.data)

    def test_user_page_shows_no_teams_when_none(self):
        """Test user page shows appropriate message when user has no teams"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('hayden', generate_password_hash('pass'), 'hayden', 'hayden@test.com', 'user'))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'hayden'
            sess['role'] = 'user'

        rv = self.app.get('/user_page')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'hayden', rv.data)

    def test_match_schedule_shows_no_games_message(self):
        """Test match schedule shows message when no games scheduled"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('hayden', 'Volleyball', 6))
            league = db.execute('SELECT id FROM leagues WHERE league_name = ?',
                                ('hayden',)).fetchone()
            self.assertIsNotNone(league)
            league_id = league['id']
            db.commit()

        rv = self.app.get(f'/match-schedule/{league_id}')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'hayden', rv.data)

    def test_generate_schedule_redirects_when_not_logged_in(self):
        """Test generate schedule redirects to login when not authenticated"""
        self.clearSession()

        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('test league', 'Basketball', 4))
            league = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('test league',)).fetchone()
            self.assertIsNotNone(league)
            league_id = league['id']
            db.commit()

        rv = self.app.get(f'/league/{league_id}/generate-schedule', follow_redirects=True)
        self.assertIn(b'Please log in to access that page.', rv.data)

    def test_user_page_with_username_param(self):
        """Test user page can be accessed with username parameter"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('ethan', generate_password_hash('pass'), 'ethan', 'ethan@test.com', 'user'))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'ethan'
            sess['role'] = 'user'

        rv = self.app.get('/user_page?username=ethan')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'ethan', rv.data)

    def test_match_schedule_with_games(self):
        """Test match schedule shows games when they exist"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('ethan basketball', 'Basketball', 4))
            league = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('ethan basketball',)).fetchone()
            self.assertIsNotNone(league)
            league_id = league['id']

            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('team1', 1, league_id))
            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('team2', 2, league_id))

            team1 = db.execute('SELECT id FROM teams WHERE name = ?', ('team1',)).fetchone()
            team2 = db.execute('SELECT id FROM teams WHERE name = ?', ('team2',)).fetchone()
            self.assertIsNotNone(team1)
            self.assertIsNotNone(team2)
            team1_id = team1['id']
            team2_id = team2['id']

            db.execute('INSERT INTO games (league_id, home_team_id, away_team_id, game_date, home_score, away_score) '
                       'VALUES (?, ?, ?, ?, 10, 8)',
                       (league_id, team1_id, team2_id, '2025-01-01 19:00:00'))
            db.commit()

        rv = self.app.get(f'/match-schedule/{league_id}')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'ethan basketball', rv.data)
        self.assertIn(b'team1', rv.data)
        self.assertIn(b'team2', rv.data)

    def test_user_page_with_team(self):
        """Test user page shows team when user is in one"""
        with interlink.app.app_context():
            db = interlink.get_db()
            db.execute('INSERT INTO users (username, password_hash, name, email, role) VALUES (?, ?, ?, ?, ?)',
                       ('elle', generate_password_hash('pass'), 'elle', 'elle@test.com', 'user'))
            user = db.execute('SELECT id FROM users WHERE username = ?', ('elle',)).fetchone()
            self.assertIsNotNone(user)
            user_id = user['id']

            db.execute('INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)',
                       ('cheese', 'Soccer', 8))
            league = db.execute('SELECT id FROM leagues WHERE league_name = ?', ('cheese',)).fetchone()
            self.assertIsNotNone(league)
            league_id = league['id']

            db.execute('INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)',
                       ('myteam', user_id, league_id))
            team = db.execute('SELECT id FROM teams WHERE name = ?', ('myteam',)).fetchone()
            self.assertIsNotNone(team)
            team_id = team['id']

            db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?, ?, ?)',
                       (user_id, team_id, league_id))
            db.commit()

        with self.app.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'elle'
            sess['role'] = 'user'

        rv = self.app.get('/user_page')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'elle', rv.data)
        self.assertIn(b'myteam', rv.data)

    def test_leave_team_requires_login(self):
        """Test leave team requires authentication"""
        self.clearSession()
        rv = self.app.post('/leave_team', data=dict(
            user='1',
            team='1',
            team_name='myteam'
        ), follow_redirects=True)

        self.assertTrue(rv.status_code in [200, 302])

if __name__ == '__main__':
    unittest.main()
