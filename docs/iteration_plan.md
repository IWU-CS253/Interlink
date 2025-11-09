# Iteration Plan: Interlink Application Development
## Team Members:
  - Casey
  - Ethan
  - Hayden
  - Elle

**Important Dependencies:**
- Database schema and basic app structure must be completed before any user stories
- User authentication system (User Story #2) is required for most user-specific functionality
- League creation (User Story #1) must be implemented before team registration (User Story #3) and game management (User Story #4)
- Team registration (User Story #3) must be implemented before roster management (User Story #7) and joining teams (User Story #6)
- Game creation and scoring (User Story #4) must be implemented before standings (User Story #9) and schedule viewing (User Story #15)

## Iteration Timeline

### First Iteration: Nov 7 - Nov 12, 2025

*Structure Planning (All team members)*

*Skeleton/Infrastructure Development*
- Back-end Python program with basic request handlers (Casey)
- Database schema SQL implementation (Hayden)
- Basic templates and CSS framework (Ethan)
- Unit test program structure (Elle)

**User Stories for First Iteration:**

*#1 Create New League (Elle)*
- Priority: 1
- Implement league creation form
- Set up league data storage
- Basic league display functionality
- **Dependencies:** Requires completed database schema and basic app structure

*#2 Account Sign In (Casey)*
- Priority: 2  
- Implement user registration and login system
- Create secure authentication
- Set up session management
- **Dependencies:** Requires database schema for user storage

*#3 Register Intramural Team (Hayden)*
- Priority: 3
- Create team registration form
- Implement team data storage
- Basic team validation
- **Dependencies:** Requires league system (#1) and user authentication (#2)

*#4 Add Game Scores (Ethan)*
- Priority: 4
- Create basic score submission form
- Implement game data storage
- **Dependencies:** Requires team system (#3) and basic authentication

### Second Iteration: Nov 12 - Nov 19, 2025

*#5 Browse Intramural Groups*
- Implement league browsing interface
- Add alphabetical sorting
- Create basic filtering

*#6 Join Existing Team*
- Implement team joining functionality
- Add player assignment system
- Update roster management

*#7 Manage Team Roster*
- Create admin roster management interface
- Implement add/remove player functionality
- Real-time roster updates

*#8 Change Reported Score*
- Create score editing interface
- Implement admin authentication for edits
- Add score validation

### Third Iteration: Nov 19 - Nov 26, 2025

*#9 View League Standings*
- Implement standings calculation
- Create standings display
- Add sorting functionality

*#10 View Team Rosters*
- Create roster display pages
- Implement sport-based filtering
- Add player image support

*#11 Setup Full League*
- Implement bulk team creation
- Create league setup wizard
- Add data validation for bulk operations

*#12 Auto-Generate Schedule*
- Implement schedule generation algorithm
- Create matchup logic
- Add conflict detection

*#13 Submit Suspension Reports*
- Create suspension reporting system
- Implement player flagging
- Add referee access controls

*Stretch Goals:*
*#14 Email Game Reminders*
*#15 Calendar Game Schedules*
