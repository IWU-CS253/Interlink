Made at this website: https://dbdiagram.io/d ,  put in the left side to see structure.

Table users {
  id integer [primary key]
  username varchar [unique, not null]
   email varchar [unique, not null]
  role varchar
  created_at timestamp
  
}

Table leagues{
  id integer [primary key]
  name         varchar [not null]
  sport        varchar  
  season       varchar 
  created_by   integer [not null, ref: > users.id]
  created_at   datetime 
}

Table teams{
  id           integer [pk, increment]
  name         varchar [not null]
  league_id    integer [ref: > leagues.id]
  captain_id   integer [ref: > users.id]
  created_at   datetime [default: `CURRENT_TIMESTAMP`]

  // A league cannot have duplicate team names
  Indexes {
    (league_id, name) [unique]
  }
}
Table games{
  id             integer [pk, increment]
  league_id      integer [ref: > leagues.id]
  home_team_id   integer [ref: > teams.id]
  away_team_id   integer [ref: > teams.id]
  home_score     int
  away_score     int
  game_date      datetime
  created_at     datetime [default: `CURRENT_TIMESTAMP`]

  Indexes {
    league_id
    game_date
  }
}

Table memberships {
  user_id   integer [pk, not null, ref: > users.id]
  team_id   integer [pk, not null, ref: > teams.id]
  role      varchar [default: 'player'] // e.g., 'captain', 'player'
  joined_at datetime [default: `CURRENT_TIMESTAMP`]

}
