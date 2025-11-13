# Iteration Report 1: InterLink Application Development

## Team Members:
  - Casey
  - Ethan
  - Hayden
  - Elle

## Report for Iteration 1, Nov 7-12, 2025

---

### Responsibilities:

*Elle*
- Set up the project structure in PyCharm
- Implement back-end Python program with basic request handlers
- Create database schema SQL implementation
- Develop basic templates and establish project organization
- Set up unit test program structure
- **User Story #1: Create New League**
  - Implement league creation form
  - Set up league data storage
  - Develop basic league display functionality
  - **Dependencies:** Requires completed database schema and basic app structure

*Casey*
- **User Story #2: Account Sign In**
  - Implement user registration and login system
  - Create secure authentication
  - Set up session management
  - **Dependencies:** Requires database schema for user storage

*Hayden*
- **User Story #3: Register Intramural Team**
  - Create team registration form
  - Implement team data storage
  - Develop basic team validation
  - **Dependencies:** Requires league system (User Story #1) and user authentication (User Story #2)

*Ethan*
- **User Story #4: Add Game Scores**
  - Create basic score submission form
  - Implement game data storage
  - **Dependencies:** Requires team system (User Story #3) and basic authentication

### What Was Completed:

All planned user stories for this iteration were completed and merged into main

*#1 Create New League (Elle)*
- Priority: 1
- League creation form functions properly
- League data gets stored into the database
- Leagues display properly on specific page

*#2 Account Sign In (Casey)*
- Priority: 2
- User registration system implemented
- User access login on nav bar of home page
- User login information is properly stored

*#3 Register Intramural Team (Hayden)*
- Priority: 3
- Team registration form functions properly
- Team data gets stored into database
- League data accessible on team registration form

*#4 Add Game Scores (Ethan)*
- Priority: 4
- Example score submission form created

### What Was Planned But Not Finished

*Frontend Styling*
- Currently, no CSS or Bootstrap
- Focused more on backend functionality

*Unittesting*
- Unittests for the first iteration features are not fully finished
- Currently, there are only unittests for league and team creation

### Troubles/Issues/Roadblocks/Difficulties Encountered

*Technical Issues*
- Some SQL reference errors. Initial database schema did not match with some SQL references made in code

*Resolution*
- The issue with our schema, as well as other minor issues that were not very notable, were all easily resolved when we worked together collaboratively and looked over the application together

### Adjustments to Overall Design

*Database Schema Modifications*
- Minor changes were made to table and column names

### One Helpful Approach

*In-Person Collaboration*

The most valuable approach during this iteration was working together in person and being able to discuss our code and what we were trying to accomplish.
We were able to solve issues quicker as looking over problems with a team is more efficient.
Furthermore, it allowed us to be more consistent with the way we implemented different features of the application. 

---

## Plan for Next Iterations

### Second Iteration: Nov 12 - Nov 19, 2025

*#5 Browse Intramural Groups (Elle)*
- Implement league browsing interface
- Add alphabetical sorting
- Create basic filtering

*#6 Join Existing Team (Hayden)*
- Implement team joining functionality
- Add player assignment system
- Update roster management

*#7 Manage Team Roster (Casey)*
- Create admin roster management interface
- Implement add/remove player functionality
- Real-time roster updates

*#8 Change Reported Score (Ethan)*
- Create score editing interface
- Implement admin authentication for edits
- Add score validation

*General Features*
- Work on CSS and Bootstrap for styling
- Develop more specific unit tests for Iteration 1 features, especially user login security
- Develop unit tests for new features in Iteration 2

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
- #14 Email Game Reminders
- #15 Calendar Game Schedules