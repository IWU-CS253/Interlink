# Create New League
-----------------------
As a league admin, I want to create a new league for a specific sport, season, and scheduling rules so that I can organize competitions.

 - Priority: 1
 - Estimate: Long, because it requires us to first implement all the logic regarding how data is stored. We would need to have the main pages set up for at least displaying teams to test that the leagues are able to be created, and the basic form to input information for league creation
 - Confirmation:

   1. Ensure league information is stored
   2. Ensure league information is displayed correctly
   3. Ensure players can be added to the league as well as teams

# Account Sign In
-----------------------
As a player, I want to create an account and sign in so that I can see my team and schedule.

 - Priority: 2
 - Estimate: medium length, it requires the login screen and storage of account information and a sign-up page
 - Confirmation:

   1. Ensure sign-up page creates an account and stores the login information
   2. Ensure that the account information is verifiable and sign-in works
   3. Ensure that people aren't able to maneuver into an account (secure login)

# Register Intramural Team
-----------------------
As a student, I want to register/create an intramural team for a sport so that I can compete in leagues.

Allow users to select from available sports and enter basic information
Create a roster with a limited number of members
Verify legitimacy of entries (student status, no duplicate team memberships)

 - Priority: 3
 - Estimate: Short, requires a form and storage method
 - Confirmation:

   1. Ensure team creation form submission stores input data
   2. Ensure that duplicate teams are not able to be created

# Add Game Scores
-----------------------
As a scorekeeper/team captain, I want to add game scores and player stats after games so that records are kept up to date.

Score upload form for authorized users only
Tag scores with sport/league information

 - Priority: 4
 - Estimate: Not long for basic implementation
 - Confirmation:

   1. Ensure box score form submission stores input data
   2. Ensure that every player can only have one stat per category

# Browse Intramural Groups
-----------------------
As a student, I want to browse available intramural groups/clubs so that I can find ones I'm interested in.

Listed alphabetically for easier searching
Link to meeting times and location information
Sort by date or season depending on sport

 - Priority: 5
 - Estimate: Not too complicated using SQL queries
 - Confirmation:

   1. Ensure that all leagues are shown
   2. Ensure that the filter properly filters leagues
   3. Ensure that the groups are shown alphabetically

# Join Existing Team
-----------------------
As a player, I want to put my name in to join a team so that I can play even without forming my own team.

Allow players to request to join existing teams or be randomly assigned

 - Priority: 6
 - Estimate: Short-medium depending on implementation
 - Confirmation:

   1. Ensure that players who do not find a team get assigned
   2. Ensure that players are only able to join existing teams
   3. Ensure that player information is saved to the roster of the team they join
   4. Ensure that the team information is consistent across pages/displays

# Manage Team Roster
-----------------------
As a league admin, I want to add or remove players from a team so that rosters stay current as they join or leave the league.

 - Priority: 7
 - Estimate: Short, requires form for adding/removing players and updating team roster storage
 - Confirmation:

   1. Ensure players can be successfully added to a team
   2. Ensure players can be successfully removed from a team
   3. Ensure team roster updates are reflected in real-time

# Change Reported Score
-----------------------
As a league admin, I want to change a reported score so that incorrect scores can be corrected.

 - Priority: 8
 - Estimate: Short, requires an edit form for existing scores with admin authentication
 - Confirmation:

   1. Ensure admin can access score editing interface
   2. Ensure score changes are saved correctly
   3. Ensure updated scores recalculate standings appropriately

# View League Standings
-----------------------
As a player, I want to see league standings so that I can track team performance.

Show stats like wins, losses
Option to sort teams by wins
Keep updated, chronological data of games
Sort by sport, show date and time

 - Priority: 9
 - Estimate: Longer due to calculations from multiple tables
 - Confirmation:

   1. Ensure standings display correct win/loss records
   2. Ensure sorting functionality works properly
   3. Ensure standings update after new game results are added

# View Team Rosters
-----------------------
As a student/athlete, I want to see the rosters of each intramural team so that I know who is on each team.

Allow sorting by sport
Clearly display team and members with images

 - Priority: 10
 - Estimate: Half an hour
 - Confirmation:

   1. Ensure all team rosters are displayed correctly
   2. Ensure sorting by sport functions properly
   3. Ensure player names and images appear correctly

# Setup Full League
-----------------------
As an administrator, I want to set up a full league with premade teams so that I can register many people at once.

 - Priority: 11
 - Estimate: Short, requires a form and storage method
 - Confirmation:

   1. Ensure bulk team creation form accepts multiple teams
   2. Ensure all teams and players are stored correctly
   3. Ensure league setup completes without data loss

# Auto-Generate Schedule
-----------------------
As a league admin, I want to auto-generate a season schedule so that each team plays each other team twice.

 - Priority: 12 - autogenerated isn't necessary however it wouldn't be a heavy load, it just requires some complicated logic
 - Estimate: Couple hours most likely
 - Confirmation:

   1. Ensure schedule generation creates all required matchups
   2. Ensure each team plays every other team exactly twice
   3. Ensure no scheduling conflicts or overlaps occur

# Submit Suspension Reports
-----------------------
As a referee, I want to submit reports on suspensions or trouble so that future refs know which players can't play.

Add suspended flag to player schema

 - Priority: 13 - simple and useful for rule enforcement
 - Estimate: Short
 - Confirmation:

   1. Ensure suspension reports are saved with player records
   2. Ensure suspended players are flagged appropriately
   3. Ensure suspension status is visible to referees and admins

# Email Game Reminders
-----------------------
As a player, I want to get email reminders about upcoming games and season signups so that I don't miss important dates.

Email list sorted by sport or group
Accessible to admins for sending notifications

 - Priority: 14
 - Estimate: Not sure - requires email integration research
 - Confirmation:

   1. Ensure email reminders are sent to correct recipients
   2. Ensure emails contain accurate game information
   3. Ensure players can opt in/out of email notifications

# Calendar Game Schedules
-----------------------
As an administrator/player, I want to have a calendar that shows game schedules so that I can easily view upcoming games.

Filter by sport or view all games
View games for teams you're part of
Public schedule viewable by anyone

 - Priority: 15
 - Estimate: Long - requires communication and visualization system
 - Confirmation:

   1. Ensure calendar displays all scheduled games correctly
   2. Ensure filtering by sport works properly
   3. Ensure personal team schedules display accurately