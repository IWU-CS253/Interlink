import os
import operator
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, g, redirect, url_for, render_template, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# Google Calendar imports
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
app = Flask(__name__)


app.config.update(
    DATABASE=os.path.join(app.root_path, 'interlinkData.db'),
    SECRET_KEY='testkey',  # use a strong secret in dev; env var in prod
)

# Google Calendar Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = "credentials.json"
REDIRECT_URI = 'http://localhost:3000/oauth2callback'

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
    filter = request.args.get('filter', None)
    db = get_db()

    if filter:
        cur = db.execute('SELECT id, league_name, sport, max_teams, status FROM leagues where SPORT=?', (filter,))
        leagues = cur.fetchall()

    else:
        cur = db.execute("SELECT id, league_name, sport, max_teams, status from leagues")
        leagues = cur.fetchall()

    return render_template('homepage.html', leagues=leagues)

@app.route('/team_view', methods=["GET"])
def team_view():
    team_name= request.args.get("team_name")
    league_name= request.args.get("league_name")
    team_manager= request.args.get("team_manager")
    sport= request.args.get("sport")
    league_status = request.args.get('league_status')
    roster = get_roster(team_name)

    return render_template('team_view.html', team_name=team_name, league_name=league_name, team_manager=team_manager, sport=sport, league_status=league_status, roster=roster)


# Helper method to get a teams roster with only their team name
def get_roster(team_name):
    db = get_db()
    team_id = db.execute('SELECT id FROM teams WHERE name=?', [team_name]).fetchone()[0]
    cur = db.execute("SELECT user_id FROM memberships WHERE team_id=?", [team_id])
    roster_ids = [row[0] for row in cur.fetchall()]
    roster=[]
    for player_id in roster_ids:
        cur=db.execute('SELECT name FROM users WHERE id=?',[player_id])
        roster.append(cur.fetchone()[0])
    return roster



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
    user = get_current_user()
    db = get_db()

    user_id = user["id"]
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

#copy of the join_team_submit but refactored for the admin page so admins can add players to teams a lot quicker
@app.route('/league/<int:league_id>/admin/add_player', methods=['POST'])
def admin_add_player(league_id):
    #admin check
    if not session.get('logged_in'):
        flash("Please log in to access that page.")
        return redirect(url_for('login'))

    activeuser = get_current_user()
    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')

    db = get_db()

    #From the admin form
    team_name = request.form.get('team_name') or request.form.get('team')
    username = (request.form.get('username') or '').strip()

    if not team_name or not username:
        flash("Team name and username are required.")
        return redirect(url_for('league_admin', league_id=league_id))

    #Find the team in this league
    team_row = db.execute(
        "SELECT id FROM teams WHERE name = ? AND league_id = ?",
        (team_name, league_id)
    ).fetchone()

    if team_row is None:
        flash("Team not found in this league.")
        return redirect(url_for('league_admin', league_id=league_id))

    team_id = team_row['id']

    #find the user by username
    user_row = get_user_by_username(username)
    if user_row is None:
        flash(f'User "{username}" not found.')
        return redirect(url_for('league_admin', league_id=league_id))

    user_id = user_row['id']

    #check if already on this team
    existing = db.execute(
        "SELECT 1 FROM memberships WHERE user_id = ? AND team_id = ?",
        (user_id, team_id)
    ).fetchone()

    if existing:
        flash(f'"{username}" is already on {team_name}.')
        return redirect(url_for('league_admin', league_id=league_id))

    #add to memberships
    db.execute(
        "INSERT INTO memberships (user_id, team_id) VALUES (?, ?)",
        (user_id, team_id)
    )
    db.commit()

    flash(f'Added "{username}" to {team_name}.')
    return redirect(url_for('league_admin', league_id=league_id))

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

    league_selected = request.args.get('league_selected')
    teams = []

    if request.method == 'POST':
        league_selected = request.form['league_selected']
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
                    [league_selected, home_team_id, away_team_id, home_score, away_score, game_date])
                db.commit()
                flash('Score submitted successfully!')
                return redirect(url_for('view_scores'))
            except:
                flash('Error Saving Score')
    if league_selected:
            cur = db.execute("SELECT name, id FROM teams WHERE league_id = ?", [league_selected])
            teams = cur.fetchall()

    leagues = db.execute("SELECT id, league_name FROM leagues").fetchall()

    return render_template('submit_score.html', leagues=leagues, teams=teams, league_selected = league_selected)

# kept this route because submit score would get both flash messages in try/except
@app.route('/scores')
def view_scores():
    return redirect(url_for('home_page'))

@app.route('/league/<int:league_id>/admin/delete_team', methods=['POST'])
def del_team(league_id):
    #admin check
    if not session.get('logged_in'):
        flash('Please log in to access that page.')
        return redirect(url_for('login'))

    activeuser = get_current_user()
    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')

    db = get_db()
    #dummy check to make sure league exists and get status
    league = db.execute(
        "SELECT id, status FROM leagues WHERE id = ?",
        (league_id,)
    ).fetchone()
    if league is None:
        flash("League not found.")
        return redirect(url_for('league_page', league_id=league_id))
    #Only let teams be deleted while league is in SignUp phase
    if league['status'] != "signup":
        flash("Teams can only be deleted while the league is in SignUp mode.")
        return redirect(url_for('league_admin', league_id=league_id))

    team_id = request.form.get('team_id')
    #check team is real
    if not team_id or not team_id.isdigit():
        flash('Invalid team.')
        return redirect(url_for('league_admin', league_id=league_id))
    team_id = int(team_id)
    #make sure team belongs to this league
    team_row = db.execute(
        "SELECT id, name FROM teams WHERE id = ? AND league_id = ?",
        (team_id, league_id)
    ).fetchone()
    if team_row is None:
        flash('Team not found in this league.')
        return redirect(url_for('league_admin', league_id=league_id))

    #Delete all memberships for that team
    db.execute("DELETE FROM memberships WHERE team_id = ?", (team_id,))
    #And the team itself
    db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
    db.commit()
    flash(f'Team "{team_row["name"]}" deleted.')
    return redirect(url_for('league_admin', league_id=league_id))

#helper for admin page
def get_current_user():
    username = session.get('username')
    if not username:
        return None
    return get_user_by_username(username)

@app.route('/league/<int:league_id>')
def league_page(league_id):
    db = get_db()

    league = db.execute('SELECT * FROM leagues WHERE id = ?', (league_id,)).fetchone()

    if league is None:
        flash("League not found")
        return redirect(url_for('league_view'))

    teams = db.execute('SELECT * FROM teams WHERE league_id = ?', (league_id,)).fetchall()

    standings = get_standings(league_id)
    games = get_league_games(league_id)

    # Sort by wins/name
    sort_by = request.args.get('sort', 'wins')

    if sort_by == 'wins':
        standings = sorted(standings, key=operator.itemgetter('wins'), reverse=True)
    elif sort_by == 'name':
        standings = sorted(standings, key=operator.itemgetter('team_name'))

    return render_template('league_page.html',
                           league=league,
                           teams=teams,
                           standings=standings,
                           games=games,
                           sort_by=sort_by)


@app.route('/league/<int:league_id>/admin')
def league_admin(league_id):
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
    league = db.execute("SELECT * FROM leagues WHERE id = ?",(league_id,)).fetchone()
    if league is None:
        flash("League doesn't exist")
        return redirect(url_for("league_view"))

    #Get all teams in the league
    team_rows = db.execute(
        "SELECT id, name FROM teams WHERE league_id = ? ORDER BY name",
        (league_id,)
    ).fetchall()

    #Use get_roster(team_name) for each team
    teams = []
    for row in team_rows:
        roster_names = get_roster(row['name'])
        teams.append({
            'id': row['id'],
            'name': row['name'],
            'roster': roster_names,
        })

    #get all games for the league, and break it up into different python variables so we can more easily use different parts of it to
    # display easier in the admin panel
    games = db.execute(""" SELECT g.id, g.game_date, g.home_score, g.away_score, t1.name AS home_team, t2.name AS away_team
                       FROM games g JOIN teams t1 ON g.home_team_id = t1.id JOIN teams t2 ON g.away_team_id = t2.id
                       WHERE g.league_id = ?
                       ORDER BY g.game_date DESC
                       """, (league_id,)).fetchall()

    return render_template(
        'league_admin.html',
        league=league,
        teams=teams,
        games=games
    )

@app.route('/league/<int:league_id>/admin/remove_player', methods=['POST'])
def remove_player(league_id):
    #admin check
    if not session.get('logged_in'):
        flash('Please log in to access that page.')
        return redirect(url_for('login'))

    activeuser = get_current_user()
    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')

    db = get_db()

    team_name = request.form.get('team_name')
    player_name = request.form.get('player_name')
    if not team_name or not player_name:
        flash('Bad request.')
        return redirect(url_for('league_admin', league_id=league_id))
    selectedTeam = db.execute(
        "SELECT id FROM teams WHERE name = ? AND league_id = ?",
        (team_name, league_id)
    ).fetchone()

    if selectedTeam is None:
        flash('Team not found.')
        return redirect(url_for('league_admin', league_id=league_id))

    team_id = selectedTeam['id']

    #get_roster uses users.name, so we match on name here
    user_row = db.execute(
        "SELECT id FROM users WHERE name = ?",
        (player_name,)
    ).fetchone()

    if user_row is None:
        flash(f'Player "{player_name}" not found.')
        return redirect(url_for('league_admin', league_id=league_id))

    user_id = user_row['id']

    #Remove from memberships
    db.execute(
        "DELETE FROM memberships WHERE user_id = ? AND team_id = ?",
        (user_id, team_id)
    )
    db.commit()

    flash(f'Removed {player_name} from {team_name}.')
    return redirect(url_for('league_admin', league_id=league_id))


@app.route('/change_phase', methods=["GET"])
def change():
    league_status=request.args.get('status')
    db = get_db()
    if league_status=="SignUp":
        db.execute('UPDATE leagues SET status = "Active"')
    elif league_status=="active":
        db.execute('UPDATE leagues SET status = "SignUp"')
    db.commit()
    return redirect('/')
  
@app.route('/edit_score', methods=['GET', 'POST'])
def edit_score():
    activeuser = get_current_user()

    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to view that page.")
        return redirect('/')
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
            return redirect(url_for('home_page'))

    game = db.execute("SELECT id, home_score, away_score, game_date FROM games WHERE id = ?", [game_id])
    game = game.fetchone()

    if not game:
        flash('Game not found.')
        return redirect(url_for('home_page'))

    return render_template('edit_score.html', game=game)


# Helper for standings
def get_standings(league_id):
    db = get_db()
    cur = db.execute('SELECT id, name FROM teams WHERE league_id = ?', [league_id])
    teams = cur.fetchall()

    standings = []
    for team in teams:
        # wins
        cur = db.execute(
            'SELECT COUNT(*) FROM games WHERE league_id = ? AND ((home_team_id = ? AND home_score > away_score) OR (away_team_id = ? AND away_score > home_score))',[league_id, team['id'], team['id']])
        wins = cur.fetchone()[0]

        # losses
        cur = db.execute(
            'SELECT COUNT(*) FROM games WHERE league_id = ? AND ((home_team_id = ? AND home_score < away_score) OR (away_team_id = ? AND away_score < home_score))',[league_id, team['id'], team['id']])
        losses = cur.fetchone()[0]

        standings.append({
            'team_id': team['id'],
            'team_name': team['name'],
            'wins': wins,
            'losses': losses
        })

    return standings

#Helper for league games
def get_league_games(league_id):
    db = get_db()
    cur = db.execute("SELECT games.id, games.game_date, games.home_score, games.away_score, teams.name as home_team, teams2.name as away_team FROM games JOIN teams ON games.home_team_id = teams.id JOIN teams as teams2 ON games.away_team_id = teams2.id WHERE games.league_id = ? ORDER BY games.game_date DESC", [league_id])
    games = cur.fetchall()
    return games

if __name__ == '__main__':
    app.run(port=3000)