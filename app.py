import os
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, g, redirect, url_for, render_template, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config.update(
    DATABASE=os.path.join(app.root_path, 'interlinkData.db'),
    SECRET_KEY='testkey',  # use a strong secret in dev; env var in prod
)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/', methods=["GET", "POST"])
def home_page():
    return render_template('homepage.html')

@app.route('/team_view')
def team_view():
    db = get_db()
    cur = db.execute('SELECT name FROM teams')
    teams = [row[0] for row in cur.fetchall()]
    return render_template('team_view.html', teams=teams)

@app.route('/league_creation', methods=["GET", "POST"])
def league_creation():
    if request.method == "POST":
        db = get_db()
        db.execute("INSERT into leagues (league_name, sport, max_teams) VALUES (?, ?, ?)", [request.form["league_name"], request.form["sport"], request.form["max_teams"]])
        db.commit()

        flash("League created successfully.")
        return redirect(url_for('league_view'))

    return render_template("league_creation.html")

@app.route('/league_view')
def league_view():
    db = get_db()
    cur = db.execute("SELECT league_name, sport, max_teams from leagues")
    league_rows = cur.fetchall()
    leagues = [row[0] for row in league_rows]
    return render_template('league_view.html', leagues=leagues)

@app.route('/team-creation')
def team_creation():
    db = get_db()
    league = db.execute("SELECT league_name FROM leagues")
    league_rows = league.fetchall()
    leagues = [row[0] for row in league_rows]
    return render_template('team_creation.html', leagues = leagues)

@app.route('/create_team', methods=["POST"])
def create_team():
    if not session.get("logged_in"):
        return redirect('/login')
    else:
        db = get_db()

        league = db.execute("SELECT id FROM leagues WHERE league_name=?", [request.form["league"]])
        league_row = league.fetchone()
        league_id = league_row[0]

        db.execute("INSERT INTO teams (name, team_manager, league_id) VALUES (?,?, ?)",
                   [request.form["name"], request.form["manager"], league_id])
        db.commit()

        flash("Team created successfully")
        return redirect("/")

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    #Try To logi
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = get_user_by_username(username)

        #Error Validation
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session['username'] = user['username']
            flash('You were logged in')
            return redirect('/')
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You were logged out')
    return redirect('/')

#Helper method for making sure there aren't conflicting usernames
def get_user_by_username(username):
    db = get_db()
    cur = db.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
    return cur.fetchone()
@app.route('/signup', methods=["GET","POST"])
def signup():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''

        #Simple validation
        if not username or not password:
            error = 'Username and password are required.'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif password != confirm:
            error = 'Passwords do not match.'
        elif get_user_by_username(username) is not None:
            error = 'That username is taken.'
        else:
            #Create user In DB
            try:
                db = get_db()
                db.execute(
                    'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                    (username, generate_password_hash(password))
                )
                db.commit()
            except error:
                error = 'That username is already taken.'
            else:
                #Log in and redirect
                session['logged_in'] = True
                session['username'] = username
                flash('Account created—welcome!')
                return redirect("/")
    return render_template('signup.html', error=error)

  
@app.route('/submit', methods=['GET', 'POST'])
def submit_score():
    if request.method == 'POST':
        sport = request.form['sport']
        game_date = request.form['game_date']
        team1 = request.form['team1']
        team2 = request.form['team2']
        score1 = request.form['score1']
        score2 = request.form['score2']
    return render_template('example_scores.html')