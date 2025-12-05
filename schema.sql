-- USERS
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    name TEXT NOT NULL,
    email TEXT not null
);

-- LEAGUES
CREATE TABLE leagues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_name TEXT NOT NULL,
    sport TEXT,
    max_teams INTEGER NOT NULL,
    admin INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT not null default 'signup',
    FOREIGN KEY (admin) REFERENCES users(id)
);

-- TEAMS
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    league_id INTEGER,
    team_manager INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (team_manager) REFERENCES users(id),
    UNIQUE (league_id, name)  -- prevent duplicate team names per league
);

-- GAMES
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER,
    home_team_id INTEGER,
    away_team_id INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    game_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (away_team_id) REFERENCES teams(id)
);

CREATE INDEX idx_games_league_id ON games(league_id);
CREATE INDEX idx_games_game_date ON games(game_date);

-- MEMBERSHIPS
CREATE TABLE memberships (
    user_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    league_id INTERGER NOT NULL,
    role TEXT DEFAULT 'player',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, team_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (league_id) REFERENCES leagues(id)
);

-- SYNCED CALENDAR GAMES
CREATE TABLE calendar_synced_games (
    game_id INTEGER PRIMARY KEY,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calendar_event_id TEXT,
    FOREIGN KEY (game_id) REFERENCES games(id)
);

CREATE INDEX idx_calendar_synced_games_game_id ON calendar_synced_games(game_id);