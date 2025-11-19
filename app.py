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
    from seed import seed
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    seed()


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
    search = request.args.get('search', None)
    db = get_db()

    if search:
        cur = db.execute('SELECT id, league_name, sport, max_teams, status FROM leagues where SPORT=?', (search,))
        leagues = cur.fetchall()

    else:
        cur = db.execute("SELECT id, league_name, sport, max_teams, status from leagues")
        leagues = cur.fetchall()

    return render_template('homepage.html', leagues=leagues)
    # db = get_db()
    # cur = db.execute("SELECT id, league_name,sport,max_teams,status from leagues where status in ('active','signup') order by status desc, created_at")
    # leagues = cur.fetchall()
    # return render_template('homepage.html', leagues=leagues)

@app.route('/team_view', methods=["GET"])
def team_view():
    team_name= request.args.get("team_name")
    league_name= request.args.get("league_name")
    team_manager= request.args.get("team_manager")
    sport= request.args.get("sport")
    league_status = request.args.get('league_status')

    return render_template('team_view.html', team_name=team_name, league_name=league_name, team_manager=team_manager, sport=sport, league_status=league_status)

@app.route('/league_creation', methods=["GET", "POST"])
def league_creation():
    if request.method == "POST":
        db = get_db()
        db.execute("INSERT into leagues (league_name, sport, max_teams) VALUES (?, ?, ?)", [request.form["league_name"], request.form["sport"], request.form["max_teams"]])
        db.commit()

        flash("League created successfully.")
        return redirect(url_for('home_page'))

    return render_template("league_creation.html")

@app.route('/league_view', methods=["GET", "POST"])
def league_view():
    filter = request.args.get('filter', None)
    db = get_db()

    if filter:
        cur = db.execute('SELECT league_name, sport, max_teams FROM leagues where sport=? ORDER BY league_name', (filter,))
        league_rows = cur.fetchall()
        leagues = [row[0] for row in league_rows]
    else:
        cur = db.execute("SELECT league_name, sport, max_teams from leagues ORDER BY league_name")
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

@app.route('/join_team_form')
def join_team_form():
    sport_selected = request.args.get('sport')
    league_selected = request.args.get('league_select', None)
    db = get_db()
    all_leagues = []
    cur = db.execute('SELECT league_name FROM leagues WHERE sport=?',[sport_selected])
    for row in cur.fetchall():
        all_leagues.append(row[0])
    teams = []

    #Checks if a league has been selected
    if league_selected:
        selected_id_row = db.execute('SELECT id FROM leagues WHERE league_name=?', [league_selected]).fetchone()

        # Checks if the leagues row exists
        if selected_id_row:
            # Finds the teams in that league
            selected_id = selected_id_row[0]
            cur = db.execute("SELECT name, id FROM teams WHERE league_id = ?", [selected_id])
            teams = [row[0] for row in cur.fetchall()]

    return render_template('join_team.html', teams=teams, all_leagues=all_leagues, league_selected=league_selected, sport_selected = sport_selected)

@app.route('/join_team_submit', methods=["POST"])
def join_team_submit():
    if not session.get("logged_in"):
        flash("Please log in to join a team!")
        return redirect("/login")

    team_name = request.form["team"]
    username = session.get("username")
    db = get_db()

    player = get_user_by_username(username)
    user_id = player[0]
    cur = db.execute('SELECT id FROM teams where name =?', [team_name])
    team_id = cur.fetchone()[0]

    #Checks that the user is not already a member of the team
    existing = db.execute(
        'SELECT * FROM memberships WHERE user_id = ? AND team_id = ?',
        [user_id, team_id]).fetchone()

    if existing:
        flash("You are already a member of this team!")
        return redirect("/join_team_form")

    db.execute('INSERT INTO memberships (user_id, team_id) VALUES (?,?)', [user_id, team_id])
    db.commit()
    flash("Joined The Team!")
    return redirect("/join_team_form")

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
    #Try To log in
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
            session['role'] = user['role']
            flash('You were logged in')
            return redirect('/')
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('You were logged out')
    return redirect('/')

#Helper method for making sure there aren't conflicting usernames
def get_user_by_username(username):
    db = get_db()
    cur = db.execute('SELECT id, username, password_hash, role FROM users WHERE username = ?', (username,))
    return cur.fetchone()
@app.route('/signup', methods=["GET","POST"])
def signup():
    error = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        name = (request.form.get('name') or '')
        email = (request.form.get('email') or '')
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
                    'INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)',
                    (username, generate_password_hash(password), name, email)
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


@app.route('/submit_score', methods=['GET', 'POST'])
def submit_score():
    if not session.get('logged_in'):
        flash('Please log in to submit scores.')
        return redirect(url_for('login'))

    db = get_db()

    if request.method == 'POST':
        league_id = request.form['league_id']
        home_team_id = request.form['home_team_id']
        away_team_id = request.form['away_team_id']
        home_score = request.form['home_score']
        away_score = request.form['away_score']
        game_date = request.form['game_date']

        # Simple validation
        if not home_score.isdigit() or not away_score.isdigit():
            flash('Scores must be numbers')
        elif int(home_score) < 0 or int(away_score) < 0:
            flash('Scores cannot be negative')
        elif home_team_id == away_team_id:
            flash('Teams must be different')
        else:
            try:
                db.execute(
                    "INSERT into games (league_id, home_team_id, away_team_id, home_score, away_score, game_date) VALUES (?, ?, ?, ?, ?, ?)",
                    [league_id, home_team_id, away_team_id, home_score, away_score, game_date])
                db.commit()
                flash('Score submitted successfully!')
                return redirect(url_for('view_scores'))
            except:
                flash('Error Saving Score')

    leagues = db.execute("SELECT id, league_name FROM leagues")
    teams = db.execute("SELECT id, name FROM teams")
    return render_template('submit_score.html', leagues=leagues.fetchall(), teams=teams.fetchall())
@app.route('/scores')
def view_scores():
    db = get_db()
    cur = db.execute("SELECT games.id, games.game_date, games.home_score, games.away_score, teams.name as home_team,"
                     " teams2.name as away_team FROM games JOIN teams ON games.home_team_id = "
                     "teams.id JOIN teams as teams2 ON games.away_team_id = teams2.id ORDER BY games.game_date DESC")
    games = cur.fetchall()

    #Still working on admin chck

    return render_template('score_view.html', games=games)

@app.route('/del_team', methods=['GET','POST'])
def del_team():
    return render_template('/')

#helper for admin page
def get_current_user():
    username = session.get('username')
    if not username:
        return None
    return get_user_by_username(username)

@app.route('/league_manage')
def league_manage():
    #first check that user is logged in
    if not session.get('logged_in'):
        flash('Please log in to access that page.')
        return redirect(url_for('login'))

    #get active user from helper function and then check if they exist and are admin
    activeuser = get_current_user()

    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to view that page.")
        return redirect('/')

    #actual logic before redirect
    db = get_db()
    cur = db.execute(
        "SELECT id, league_name, sport, max_teams, status "
        "FROM leagues ORDER BY created_at DESC"
    )
    leagues = cur.fetchall()
    return render_template('league_manage.html', leagues=leagues)

@app.route('/league/<int:league_id>')
def league_page(league_id):
    db = get_db()

    league = db.execute('SELECT * FROM leagues WHERE id = ?', (league_id,)).fetchone()

    if league is None:
        flash("League not found")
        return redirect(url_for('league_view'))

    teams = db.execute('SELECT * FROM teams WHERE league_id = ?', (league_id,)).fetchall()
    return render_template('league_page.html',
                           league=league,
                           teams=teams)

@app.route('/change_phase', methods=["GET"])
def change():
    league_status=request.args.get('status')
    db = get_db()
    if league_status=="SignUp":
        db.execute('UPDATE leagues SET status = "Active"')
    elif league_status=="Active":
        db.execute('UPDATE leagues SET status = "SignUp"')
    db.commit()
    return redirect('/')
  
@app.route('/edit_score', methods=['GET', 'POST'])
def edit_score():
    #ADMIN CHECK STILL NEEDED
    db = get_db()

    game_id = request.args.get('game_id')

    if not game_id or not game_id.isdigit():
        flash('Game not found.')
        return redirect(url_for('view_scores'))

    if request.method == 'POST':
        home_score = request.form['home_score']
        away_score = request.form['away_score']

        if not home_score.isdigit() or not away_score.isdigit():
            flash('Scores must be numbers')
        elif int(home_score) < 0 or int(away_score) < 0:
            flash('Scores cannot be negative')
        else:
            db.execute("UPDATE games SET home_score = ?, away_score = ? WHERE id = ?",[home_score, away_score, game_id])
            db.commit()
            flash('Score updated successfully!')
            return redirect(url_for('view_scores'))

    game = db.execute("SELECT id, home_score, away_score, game_date FROM games WHERE id = ?", [game_id])
    game = game.fetchone()

    if not game:
        flash('Game not found.')
        return redirect(url_for('view_scores'))

    return render_template('edit_score.html', game=game)
