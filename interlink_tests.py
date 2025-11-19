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
            db.execute('INSERT INTO users (username, password_hash,name,email) VALUES (?, ?,?,?)',
                       ('user', generate_password_hash('123')),'real name','test@email.com')
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


if __name__ == '__main__':
    unittest.main()