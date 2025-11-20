# Iteration Report 2: InterLink Application Development

## Team Members:
  - Casey
  - Ethan
  - Hayden
  - Elle

## Report for Iteration 2, Nov 12-19, 2025

---

### Responsibilities:

*Elle*
- **User Story #5: Browse Intramural Groups**
  - Allow for users to browse through leagues based on sport
  - List leagues alphabetically for easier searching
  - Ensure all leagues are shown, filtering works properly, groups are sorted alphabetically

*Hayden*
- Reorganized structure of application, changed display of leagues, dynamic routing
- **User Story #6: Join Existing Team**
  - Allow players to join existing teams
  - Ensure that players get assigned to a team
  - Only existing teams are able to be joined
  - Team information consistent across displays

*Casey*
- Changed login page, adjusted schema accordingly with admin implementation
- **User Story #7: Manage Team Roster**
  - Create admin roster management interface
  - Ensure players can be successfully added to team
  - Ensure players can be successfully removed from team
  - Ensure team roster updates are reflected in real-time

*Ethan*
- **User Story #8: Change Reported Score**
  - Allow reported scores to be adjusted
  - Created editing form for existing scores with admin authentication
  - Ensure score changes are accurate and saved correctly

### What Was Completed:

All planned user stories for this iteration were completed and merged into main.

Additionally, some bootstrap styling was added to the application, and edits were made to unit tests. 

### What Was Planned But Not Finished

*Comprehensive Unittesting*
- Unittests for the first iteration features are not fully finished
- Currently, there are only unittests for league and team creation

### Troubles/Issues/Roadblocks/Difficulties Encountered

*SQL Injection/Vulnerabilities*
- Noticed potential issues with security after watching the security video. 
- We plan to address these issues and make changes in the next iteration, since this was noticed very recently

### Adjustments to Overall Design

*Database Schema Modifications*
- Changes were made based on implementation of new features. Consists of renaming column and/or adding new column

### One Helpful Approach

*Being Proactive*
- It helps that our team members are very communicative and proactive with this project. For example, some people were
more productive with their task and finished quickly, and instead of sitting back, made small tweaks with styling and
back-end functionality. This makes our process later much smoother, as it could reduce the debugging we need to do
and also helps with the features we have yet to implement. 

### New: Important Thing We Learned

*Problem Solving*
- Today during our stand-up we learned that it is important for us to actually run into some issues in order
to properly experience the teamwork aspect of the project. Everything has been going rather smoothly, so we have
not really needed to resolve any serious conflicts yet. 

---

## Plan for Next Iterations

### Third Iteration: Nov 19 - Nov 25, 2025

*#9 View League Standings (Ethan)*
- Show team stats like wins, losses
- Sort team by wins (option)
- Keep updated, chronological data of games
- Sort by sport, show date and time

*#10 View Team Rosters (Hayden)*
- Ensure team members are displayed properly
- Allow for sorting by sport

*#11 Setup Full League (Casey)*
- Set up league with pre-made teams to register multiple people at once
- Ensure bulk team creation form accepts multiple teams
- Ensure all teams and players are stored correctly
- Ensure league setup completes without data loss

*#12 Auto-Generate Schedule (Elle)*
- Generate season schedule for leagues that sets up teams to play each team twice
- Ensure schedule generation creates all required matchups
- Ensure each team plays the other twice
- Ensure no scheduling conflicts or overlaps occur

*General Features*
- Work on MORE CSS and Bootstrap for styling
- Develop comprehensive unittests for Iteration 1 & 2 features
- Address SECURITY issues like SQL injection vulnerabilities

### Final Iteration (Focus on Stretch Goals): Nov 25 - Dec 3, 2025 

*Stretch Goals:*
- #13 Submit Suspension Reports
- #14 Email Game Reminders
- #15 Calendar Game Schedules

*Debugging & Security*