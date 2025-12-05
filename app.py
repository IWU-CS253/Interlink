import os
import operator
import random
import googleapiclient
import yagmail
import secrets
from datetime import datetime, timedelta
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, g, redirect, url_for, render_template, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False

app = Flask(__name__)

# Creates flask_limiter extension
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

app.config.update(
    DATABASE=os.path.join(app.root_path, 'interlinkData.db'),
    SECRET_KEY='testkey',  # use a strong secret in dev; env var in prod
)

# Google Calendar Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
# Error handling for Unittests
try:
    SERVICE_ACCOUNT_FILE = 'interlink-478922-f6de685de9d5.json'
except FileNotFoundError:
    pass
PUBLIC_CALENDAR_ID = '9fd94e2aa60aa8bbf719f5a47040a77c201c7a1571b950cf4f3109a9150cc447@group.calendar.google.com'

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

# Makes flask_limiter errors a flash message instead of separate page
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    flash(f'Rate limit exceeded', 'error')
    return redirect(url_for('home_page'))
@app.route('/', methods=["GET", "POST"])
def home_page():
    filter = request.args.get('filter', None)
    db = get_db()

    # Checks and applies filter to league results
    if filter:
        cur = db.execute('SELECT id, league_name, sport, max_teams, status FROM leagues where SPORT=?', (filter,))
        leagues = cur.fetchall()

    else:
        cur = db.execute("SELECT id, league_name, sport, max_teams, status from leagues")
        leagues = cur.fetchall()

    # Syncs Google Calendar games when route is run
    if GOOGLE_CALENDAR_AVAILABLE:
        success = sync_games_to_calendar()
        if success:
            # Set a flag so we know calendar is synced
            session['calendar_connected'] = True

    return render_template('homepage.html', leagues=leagues, filter=filter)

@app.route('/team_view', methods=["GET"])
def team_view():
    team_name= request.args.get("team_name")
    league_name= request.args.get("league_name")
    team_manager= request.args.get("team_manager")
    sport= request.args.get("sport")
    league_status = request.args.get('league_status')
    team_id = request.args.get('team_id')
    roster = get_roster(team_name)

    db = get_db()
    cur = db.execute("""SELECT games.id,
                               games.game_date,
                               games.home_score,
                               games.away_score,
                               teams.name  as home_team,
                               teams2.name as away_team
                                FROM games
                                 JOIN teams ON games.home_team_id = teams.id
                                 JOIN teams as teams2 ON games.away_team_id = teams2.id
                                WHERE (teams.id = ? OR teams2.id=?)
                                  AND games.home_score IS NULL
                                  AND games.away_score IS NULL
                                ORDER BY games.game_date ASC""", [team_id, team_id])
    games = cur.fetchall()

    return render_template('team_view.html', games=games, team_name=team_name, league_name=league_name,
                           team_id=team_id, team_manager=team_manager, sport=sport,
                           league_status=league_status, roster=roster)


# Helper method to get a teams roster with only their team name
def get_roster(team_name):
    db = get_db()
    # Finds a team id from the name
    team_id = db.execute('SELECT id FROM teams WHERE name=?', [team_name]).fetchone()[0]
    cur = db.execute("SELECT user_id FROM memberships WHERE team_id=?", [team_id])
    roster_ids = [row[0] for row in cur.fetchall()]
    roster=[]
    # Loops through player ids and gets their real name for display
    for player_id in roster_ids:
        cur=db.execute('SELECT name FROM users WHERE id=?',[player_id])
        roster.append(cur.fetchone()[0])
    return roster


@app.route('/league_creation', methods=["GET", "POST"])
# Sets a limit for creating leagues to 5 per hour
@limiter.limit("5 per hour", key_func=lambda:f"create_league:{get_remote_address()}")
def league_creation():
    # Logged in check
    if not session.get('logged_in'):
        flash("Please log in to access that page.")
        return redirect(url_for('login'))

    # Admin check
    activeuser = get_current_user()
    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')
    if request.method == "POST":
        db = get_db()
        db.execute("INSERT into leagues (league_name, sport, max_teams) VALUES (?, ?, ?)", [request.form["league_name"], request.form["sport"], request.form["max_teams"]])
        db.commit()

        flash("League created successfully.")
        return redirect(url_for('home_page'))

    return render_template("league_creation.html")


@app.route('/league/<int:league_id>/admin/delete_league', methods=["POST"])
def delete_league(league_id):
    # Logged in check
    if not session.get('logged_in'):
        flash('Please log in to access that page.')
        return redirect(url_for('login'))

    # Admin check
    activeuser = get_current_user()
    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')

    db = get_db()
    # dummy check to make sure league exists and get status
    league = db.execute(
        "SELECT id, status FROM leagues WHERE id = ?",
        (league_id,)
    ).fetchone()

    # Handles if a league does not exist
    if league is None:
        flash("League not found.")
        return redirect(url_for('home_page'))

    # Only let leagues be deleted while league is in SignUp phase
    if league['status'] != "signup":
        flash("Leagues can only be deleted while the league is in SignUp mode.")
        return redirect(url_for('league_admin', league_id=league_id))

    # Delete from Google Calendar if available
    if GOOGLE_CALENDAR_AVAILABLE:
        service = get_calendar_service()
        if service:
            # Look up each games calendar event ID from the sync table
            synced_record = db.execute(
                'SELECT calendar_event_id FROM calendar_synced_games WHERE league_id = ?',
                (league_id,)
            ).fetchall()

            if synced_record:
                for record in synced_record:
                    # Delete the event using the stored event ID
                    service.events().delete(
                        calendarId=PUBLIC_CALENDAR_ID,
                        eventId=record['calendar_event_id']
                    ).execute()

                # Remove from synced games table
                db.execute('DELETE FROM calendar_synced_games WHERE league_id = ?', (league_id,))

    # Delete games first
    db.execute("DELETE FROM games WHERE league_id = ?", (league_id,))
    # Delete all memberships for that league
    db.execute("DELETE FROM memberships WHERE league_id = ?", (league_id,))
    db.commit()
    # And the league itself
    db.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
    db.commit()
    flash(f'League has been deleted.')
    return redirect(url_for('home_page'))

def month_days(month, year):
    days_thirty_one = [1, 3, 5, 7, 8, 10, 12]
    days_thirty = [4, 6, 9, 11]
    if month in days_thirty_one:
        return 31
    elif month in days_thirty:
        return 30

    # Leap year calculation
    else:
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 29
        return 28

def date(year, month, day, add_days):
    day += add_days

    # Change to next month
    while day > month_days(month, year):
        day -= month_days(month, year)
        month += 1

        # Change to next year
        if month > 12:
            month = 1
            year += 1

    return year, month, day

@app.route('/match-schedule/<int:league_id>')
def match_schedule(league_id):
    db = get_db()
    league = db.execute('SELECT * FROM leagues WHERE id=?', [league_id]).fetchone()
    if league is None:
        flash('League does not exist!')
        return redirect(url_for('home_page'))

    games = db.execute('''
                       SELECT games.id, games.game_date, games.home_score, games.away_score, games.home_team_id,
                       games.away_team_id FROM games WHERE games.league_id = ? ORDER BY games.game_date ASC
                       ''', [league_id]).fetchall()

    team_games = []
    for game in games:
        home_team = db.execute('SELECT name FROM teams WHERE id=?', [game['home_team_id']]).fetchone()
        away_team = db.execute('SELECT name FROM teams WHERE id=?', [game['away_team_id']]).fetchone()

        game_dict = {
            'id': game['id'],
            'game_date': game['game_date'],
            'home_score': game['home_score'],
            'away_score': game['away_score'],
            'home_team_id': game['home_team_id'],
            'away_team_id': game['away_team_id'],
            'home_team': home_team['name'],
            'away_team': away_team['name']
        }
        team_games.append(game_dict)

    finished_games = []
    future_games = []

    for game in team_games:
        if game['home_score'] is None or game['away_score'] is None:
            future_games.append(game)
        else:
            finished_games.append(game)

    return render_template('match_schedule.html', league=league, future_games=future_games,
                           finished_games=finished_games)

@app.route('/league/<int:league_id>/generate-schedule', methods=['GET', 'POST'])
def generate_schedule(league_id):
    # admin check
    if not session.get('logged_in'):
        flash("Please log in to access that page.")
        return redirect(url_for('login'))

    activeuser = get_current_user()
    if activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')

    db = get_db()

    league = db.execute('SELECT * FROM leagues WHERE id=?', [league_id]).fetchone()
    teams = db.execute('SELECT id, name FROM teams WHERE league_id=?', [league_id]).fetchall()
    if league is None:
        flash('League does not exist!')
        return redirect(url_for('home_page'))

    if request.method == 'POST':

        starting_date = request.form['start_date']
        games_week = int(request.form.get('games_per_week'))
        clear_unplayed = request.form.get('clear_existing')

        if clear_unplayed == 'on':
            games = db.execute('SELECT * FROM games WHERE league_id=? and home_score IS NULL AND away_score IS NULL',
                               [league_id]).fetchall()

            # Delete from Google Calendar if available
            if GOOGLE_CALENDAR_AVAILABLE:
                service = get_calendar_service()
                if service:
                    # Look up each games calendar event ID from the sync table
                    for game in games:
                        synced_record = db.execute(
                            'SELECT calendar_event_id FROM calendar_synced_games WHERE game_id = ?',
                            [game['id']]
                        ).fetchone()

                        if synced_record:
                                # Delete the event using the stored event ID if games are found
                                try:
                                    service.events().delete(
                                        calendarId=PUBLIC_CALENDAR_ID,
                                        eventId=synced_record['calendar_event_id']
                                    ).execute()
                                # Error handling for if a game was already deleted
                                except googleapiclient.errors.HttpError as e:
                                    if e.resp.status == 410:  # Resource already deleted
                                        print(f"Calendar event {game['calendar_event_id']} already deleted")
                                        pass
                                # Remove from synced games table
                                db.execute('DELETE FROM calendar_synced_games WHERE game_id = ?', [game['id']])

            # Remove the unplayed games from the games table
            db.execute('DELETE FROM games WHERE league_id=? AND home_score IS NULL AND away_score IS NULL', [league_id])
            db.commit()
            flash('Games successfully cleared!')


        pairings = []
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                pairings.append((teams[i]['id'], teams[j]['id']))
                pairings.append((teams[j]['id'], teams[i]['id']))
        random.shuffle(pairings)

        start_date = starting_date.split('-')
        year = int(start_date[0])
        month = int(start_date[1])
        day = int(start_date[2])
        current_game_count = 0
        for home_id, away_id in pairings:
            if month < 10:
                month_str = '0' + str(month)
            else:
                month_str = str(month)

            if day < 10:
                day_str = '0' + str(day)
            else:
                day_str = str(day)

            game_date = str(year) + '-' + month_str + '-' + day_str + ' 19:00:00'

            db.execute('INSERT INTO games (league_id, home_team_id, away_team_id, game_date, home_score, away_score) '
                       'VALUES (?, ?, ?, ?, NULL, NULL)',
                [league_id, home_id, away_id, game_date])

            current_game_count += 1
            if current_game_count >= games_week:
                result = date(year, month, day, 7)
                year = result[0]
                month = result[1]
                day = result[2]
                current_game_count = 0
            else:
                result = date(year, month, day, 3)
                year = result[0]
                month = result[1]
                day = result[2]

        db.commit()
        flash('Games generated!')
        return redirect(url_for('match_schedule', league_id=league_id))

    row = db.execute('SELECT COUNT(*) as count FROM games WHERE league_id=? AND home_score IS NULL',
                     [league_id]).fetchone()
    existing_games = row['count']

    return render_template('generate_schedule.html', league=league, teams=teams, num_teams=len(teams),
                           existing_games=existing_games)
@app.route('/team-creation')
def team_creation():
    db = get_db()
    # Gets all the league names for the creation choices
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
    cur = db.execute('SELECT league_name FROM leagues WHERE sport=? and status != "active"',[sport_selected])
    for row in cur.fetchall():
        all_leagues.append(row[0])
    teams = []

    #Checks if a league has been selected
    if league_selected:
        selected_id_row = db.execute("SELECT id FROM leagues WHERE league_name=?", [league_selected]).fetchone()

        # Checks if the leagues row exists
        if selected_id_row:
            # Finds the teams in that league
            selected_id = selected_id_row[0]
            cur = db.execute("SELECT name, id FROM teams WHERE league_id = ?", [selected_id])
            teams = [row[0] for row in cur.fetchall()]

    return render_template('join_team.html', teams=teams, all_leagues=all_leagues, league_selected=league_selected, sport_selected = sport_selected)

@app.route('/join_team_submit', methods=["POST"])
def join_team_submit():
    # Checks that a user is logged in
    if not session.get("logged_in"):
        flash("Please log in to join a team!")
        return redirect("/login")

    league_name = request.form["league_hidden"]
    team_name = request.form["team"]
    user = get_current_user()
    db = get_db()

    # Gets the required ids
    user_id = user["id"]
    cur = db.execute('SELECT id FROM teams where name =?', [team_name])
    team_id = cur.fetchone()[0]
    league_id = db.execute('SELECT id FROM leagues where league_name =?', [league_name]).fetchone()[0]

    #Checks that the user is not already a member of the team
    existing = db.execute(
        'SELECT * FROM memberships WHERE user_id = ? AND team_id = ?',
        [user_id, team_id]).fetchone()

    if existing:
        flash("You are already a member of this team!")
        return redirect("/join_team_form")

    # Checks that a user is not already a member of a team in the league
    in_league = db.execute(
        'SELECT * FROM memberships WHERE user_id = ? AND league_id = ?',
        [user_id, league_id]).fetchone()

    if in_league:
        flash("You are already a member of a team in this league!")
        return redirect("/join_team_form")

    db.execute('INSERT INTO memberships (user_id, team_id, league_id) VALUES (?,?,?)', [user_id, team_id, league_id])
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
# Creates a limit on team creations per hour
@limiter.limit("5 per hour", key_func=lambda:f"create_team:{get_remote_address()}")
def create_team():
    activeuser = get_current_user()
    # Checks that a user is logged in
    if not session.get("logged_in"):
        return redirect('/login')
    # Checks that a user is admin
    elif activeuser is None or activeuser['role'] != "admin":
        flash("You do not have permission to do that.")
        return redirect('/')

    else:
        db = get_db()

        # Gets the team name from the form
        team_name = (request.form.get("name") or "").strip()

        # Checks that the team name blank is filled in
        if not team_name:
            flash("Team name is required.")
            return redirect(url_for('team_creation'))

        # Gets the league as well as its id and max number of teams
        league = db.execute("SELECT id, max_teams FROM leagues WHERE league_name=?", [request.form["league"]])
        league_row = league.fetchone()
        league_id = league_row["id"]
        max_teams = league_row["max_teams"]

        #don't allow more teams then max teams for league and don't allow
        #duplicate team names
        teamCount = db.execute(
            "SELECT COUNT(*) FROM teams WHERE league_id = ?",
            (league_id,)
        ).fetchone()[0]

        if max_teams is not None and teamCount >= max_teams:
            flash("This league is already at its max number of teams.")
            return redirect(url_for('team_creation'))
        existing_team = db.execute(
            "SELECT 1 FROM teams WHERE league_id = ? AND name = ?",
            (league_id, team_name)
        ).fetchone()

        if existing_team:
            flash("A team with that name already exists in this league.")
            return redirect(url_for('team_creation'))

        # Inserts new team into table
        db.execute("INSERT INTO teams (name, team_manager, league_id) VALUES (?,?, ?)",
                   [request.form["name"], request.form["manager"], league_id])
        db.commit()

        flash("Team created successfully")
        return redirect("/")


@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    username=""
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
    return render_template('login.html', error=error, username=username)

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
    form_info = {
        'username' : "",
        'name': "",
        'email': "",
    }

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        name = (request.form.get('name') or '')
        email = (request.form.get('email') or '')
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''

        form_info = {
            'username': username,
            'name': name,
            'email': email,
        }

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
                existing_email = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
                if existing_email:
                    error = 'An account with this email already exists.'
                else:
                    verification_token = secrets.token_urlsafe(32)
                    db.execute(
                        'INSERT INTO pending_registrations (username, email, name, password_hash, verification_token) VALUES (?, ?, ?, ?, ?)',
                        (username, email, name, generate_password_hash(password), verification_token)
                    )
                    db.commit()

                    pending_id = db.execute('SELECT id FROM pending_registrations WHERE username=?', (username,)).fetchone()[0]

                    email_sent = send_verification_email(email, username, verification_token, pending_id)
                    if email_sent:
                        flash('Verification email sent')
                        return redirect("/")
            except error:
                error = 'That username is already taken.'
            else:
                #Log in and redirect
                session['logged_in'] = True
                session['username'] = username
                flash('Account created—welcome!')
                return redirect("/")
    return render_template('signup.html', error=error, form_info=form_info)


@app.route('/submit_score', methods=['GET', 'POST'])
def submit_score():
    if not session.get('logged_in'):
        flash('Please log in to submit scores.')
        return redirect(url_for('login'))
    db = get_db()

    league_selected = request.args.get('league_selected')
    unfinished_games = []

    if request.method == 'POST':
        league_selected = request.form['league_selected']
        game_id = request.form['game_id']
        home_score = request.form['home_score']
        away_score = request.form['away_score']
        # Simple validation
        if not home_score.isdigit() or not away_score.isdigit():
            flash('Scores must be numbers')
        elif int(home_score) < 0 or int(away_score) < 0:
            flash('Scores cannot be negative')
        else:
            try:
                db.execute(
                    'UPDATE games SET home_score=?, away_score=? WHERE id=?',
                    [home_score, away_score, game_id])
                db.commit()
                flash('Score submitted successfully!')
                return redirect(url_for('view_scores'))
            except:
                flash('Error Saving Score')
    if league_selected:
            cur = db.execute('''SELECT games.id, games.game_date, home.name as home_team, away.name as away_team
                           FROM games JOIN teams home ON games.home_team_id = home.id JOIN teams away ON games.away_team_id = away.id
                           WHERE games.league_id = ? AND games.home_score IS NULL AND games.away_score IS NULL
                           ORDER BY games.game_date ASC ''', [league_selected])
            unfinished_games = cur.fetchall()

    leagues = db.execute("SELECT id, league_name FROM leagues").fetchall()

    return render_template('submit_score.html', leagues=leagues, unfinished_games=unfinished_games, league_selected = league_selected)

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
        return redirect(url_for("home_page"))

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
                       ORDER BY g.game_date ASC
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


@app.route('/change_phase', methods=["POST"])
def change_league_status():
    league_status = request.form['status']
    league_id = request.form['league_id']
    db = get_db()
    if league_status=="signup":
        db.execute('UPDATE leagues SET status = "active" WHERE id=?',[league_id])
    elif league_status=="active":
        db.execute('UPDATE leagues SET status = "signup" WHERE id=?',[league_id])
    db.commit()
    return redirect(url_for('league_admin', league_id=league_id))
  
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

# GOOGLE CALENDAR METHODS
def get_calendar_service():
    """Get Google Calendar service with service account credentials"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        return None

    # Creates the credentials using the service account .json file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # Builds the Google calendar resource
    service = build('calendar', 'v3', credentials=credentials)
    return service

def create_game_event(game):
    """Creates the calendar event for a game in database"""
    date = str(game['game_date'])

    # Puts the date into the expected format for Google Calendar
    if ' ' in date:
        date_part = date.split(' ')[0]
    elif 'T' in date:
        date_part = date.split('T')[0]
    else:
        date_part = date
    time_part = '19:00:00'

    # Create start datetime (7 PM)
    start_datetime = f"{date_part}T{time_part}"

    # Formats the start dateTime
    start_dt = datetime.strptime(start_datetime, '%Y-%m-%dT%H:%M:%S')
    # Formats and adds 2hrs to the end dateTime
    end_dt = start_dt + timedelta(hours=2)
    end_datetime = end_dt.strftime('%Y-%m-%dT%H:%M:%S')

    # Assigns a color based on the league's id
    color = str(game['league_id'])

    # Creates the event
    event = {
        'summary': f"{game['home_team']} vs {game['away_team']}", # Makes the Title
        'description': f"League: {game['league_name']}\nSport: {game['sport']}\nScore: {game['home_score']} - {game['away_score']}\n\nHome Team: {game['home_team']}\nAway Team: {game['away_team']}",
        'start': {
            'dateTime': start_datetime,
            'timeZone': 'America/Chicago'
        },
        'end': {
            'dateTime': end_datetime,
            'timeZone': 'America/Chicago'
        },
        'colorId': color,
    }
    return event

def sync_games_to_calendar():
    """Sync games within 30 days to Google Calendar"""
    service = get_calendar_service()
    if not service:
        flash("Service not working for calendar")
        return False

    db = get_db()

    # Gets the date and the date 30 days from today for the server syncing limit
    today = datetime.now().date()
    next_week = today + timedelta(days=30)
    today_str = today.strftime('%Y-%m-%d')
    next_week_str = next_week.strftime('%Y-%m-%d')

    # Get all games within 30 days from database
    games = db.execute("""
                       SELECT games.id,
                              games.game_date,
                              games.league_id,
                              games.home_score,
                              games.away_score,
                              home_team.name as home_team,
                              away_team.name as away_team,
                              leagues.league_name,
                              leagues.sport
                       FROM games
                                JOIN teams home_team ON games.home_team_id = home_team.id
                                JOIN teams away_team ON games.away_team_id = away_team.id
                                JOIN leagues ON games.league_id = leagues.id
                           WHERE games.game_date >= ? AND games.game_date <= ?
                       ORDER BY games.game_date
                       """,[today_str, next_week_str]).fetchall()

    # Get already synced game IDs from database
    synced_games = db.execute('SELECT game_id FROM calendar_synced_games').fetchall()
    synced_game_ids = set(row['game_id'] for row in synced_games)

    # Only sync games that aren't already tracked as synced
    new_games = []
    for game in games:
        if game['id'] not in synced_game_ids:
            new_games.append(game)
        elif game['id'] in synced_game_ids:
            continue

    # Ends the process if no new games
    if len(new_games) == 0:
        return True

    # Loops through the new games creating events and adding them to the calendar
    for game in new_games:
        event = create_game_event(game)
        # Insert new event
        created_event = service.events().insert(
            calendarId=PUBLIC_CALENDAR_ID,
            body=event
        ).execute()
        # Store the game_id and calendar event_id in the database
        db.execute(
            'INSERT INTO calendar_synced_games (game_id, league_id, calendar_event_id) VALUES (?, ?,?)',
            [game['id'], game['league_id'], created_event['id']]
        )
        db.commit()
    flash('All games synced')
    return True

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
    cur = db.execute("""SELECT games.id, games.game_date, games.home_score, games.away_score, 
                       teams.name as home_team, teams2.name as away_team 
                       FROM games 
                       JOIN teams ON games.home_team_id = teams.id 
                       JOIN teams as teams2 ON games.away_team_id = teams2.id 
                       WHERE games.league_id = ? AND games.home_score IS NOT NULL AND games.away_score IS NOT NULL
                       ORDER BY games.game_date ASC""", [league_id])
    games = cur.fetchall()
    return games

@app.route('/whole_league_creation', methods=["GET", "POST"])
def whole_league_creation():
        if not session.get("logged_in"):
            flash("Please log in to create a league and teams.")
            return redirect(url_for('login'))

        activeuser = get_current_user()
        if activeuser is None or activeuser['role'] != "admin":
            flash("You do not have permission to do that.")
            return redirect('/')

        if request.method == "GET":
            #Firstly only show the league form
            return render_template("whole_league_creation.html", step=1)

        #Get the step, step 1 is just making the league and step 2 is making the teams
        step = request.form.get('step', '1')
        if step == '1':
            league_name = request.form.get('league_name')
            sport = request.form.get('sport')
            maxteams = request.form.get('max_teams')
            error = None

            db = get_db()
            leagues = db.execute('SELECT league_name FROM leagues').fetchall()[0]
            for name in leagues:
                if league_name == name:
                    error = "League name already taken"
            if not league_name:
                error = "League name required"
            elif not sport:
                error = "Sport is required"
            else:
                if int(maxteams) <= 1:
                    error = "Max teams must be 2 or more"

            if error:
                flash(error, "error")
                return render_template("whole_league_creation.html",
                                       step =1,
                                       league_name=league_name,
                                       sport=sport,
                                       max_teams=maxteams)

            #If no error, move onto step 2
            return render_template("whole_league_creation.html",
                                   step=2,
                                   league_name=league_name,
                                   sport=sport,
                                   max_teams=int(maxteams))
        elif step == '2':
            league_name = request.form.get('league_name')
            sport = request.form.get('sport')
            maxteams = int(request.form.get('max_teams'))

            rawTeamNames = request.form.getlist('team_names[]')
            separatedTeamNames = [t.strip() for t in rawTeamNames if t.strip()]

            if len(separatedTeamNames) > maxteams:
                flash(f"You added {len(separatedTeamNames)} teams but max is {maxteams}.", "error")
                return render_template(
                    "whole_league_creation.html",
                    step=2,
                    league_name=league_name,
                    sport=sport,
                    max_teams=maxteams,
                    team_names=rawTeamNames
                )
            db = get_db()

            # Insert league (column is max_teams per your other routes)
            cur = db.execute(
                "INSERT INTO leagues (league_name, sport, max_teams) VALUES (?, ?, ?)",
                (league_name, sport, maxteams)
            )
            league_id = cur.lastrowid

            #Team manager defaults to current user
            current_user = get_current_user()
            default_manager = current_user['username']

            for name in separatedTeamNames:
                db.execute(
                    "INSERT INTO teams (name, team_manager, league_id) VALUES (?, ?, ?)",
                    (name, default_manager, league_id)
                )

            db.commit()

            flash("League and teams created successfully.")
            return redirect(url_for('home_page'))

# Route for the verification link that moves users from pending to actual users table
@app.route('/verify-email/<int:pending_id>/<token>')
def verify_email(pending_id, token):
    db = get_db()

    # Get pending registration
    pending = db.execute(
        'SELECT id, username, email, name, password_hash FROM pending_registrations WHERE id = ? AND verification_token = ?',
        (pending_id, token)
    ).fetchone()

    if pending is None:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('home_page'))

    # Check again if username or email already exists in users table
    existing_user = db.execute(
        'SELECT id FROM users WHERE username = ? OR email = ?',
        (pending['username'], pending['email'])
    ).fetchone()

    if existing_user:
        # Remove the pending registration
        db.execute('DELETE FROM pending_registrations WHERE id = ?', (pending_id,))
        db.commit()
        flash('Username or email already exists. Please use a different one.', 'error')
        return redirect(url_for('signup'))

    # Create the actual user account
    db.execute(
        'INSERT INTO users (username, password_hash, name, email, email_verified) VALUES (?, ?, ?, ?, ?)',
        (pending['username'], pending['password_hash'], pending['name'], pending['email'], True)
    )

    # Remove from pending registrations
    db.execute('DELETE FROM pending_registrations WHERE id = ?', (pending_id,))

    db.commit()

    flash('Email verified successfully! Your account has been created. You can now log in.', 'success')
    return redirect(url_for('login'))


def send_verification_email(to_email, username, token, pending_id):
    """Send account verification email using yagmail"""
    try:
        # Create verification link
        verification_link = f"http://127.0.0.1:5000/verify-email/{pending_id}/{token}"

        # Email content
        subject = "Verify Your Interlink Account"
        text_content = f"""
        Welcome to Interlink, {username}!

        Please verify your email address by visiting this link:

        {verification_link}

        This link will expire in 24 hours.

        If you didn't create this account, please ignore this email.
        """

        # Send email with yagmail
        yag = yagmail.SMTP("interlinkfall25@gmail.com", "fbts pwrs bwge xmbm")
        yag.send(
            to=to_email,
            subject=subject,
            contents=[text_content]
        )

        print(f"Verification email sent to {to_email}")
        return True

    except Exception as e:
        print(f"Failed to send verification email: {e}")
        # Don't fail signup if email fails, just warn user
        return False

if __name__ == '__main__':
    app.run(port=3000)