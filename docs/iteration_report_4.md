# Iteration Report 4: InterLink Application Development

## Team Members:
  - Casey
  - Ethan
  - Hayden
  - Elle

## Report for Iteration 4, Nov 25 - Dec 3, 2025

---

### Responsibilities:

*Hayden*
- **Stretch Goal: Calendar Game Schedules**
  - Public schedule viewable by anyone
  - Auto-update as games are scheduled
  - Ensure calendar displays all scheduled games correctly
  - Ensure filtering by sport works properly
  - Ensure personal team schedules display accurately

*Casey*
- **Complete User Story 11 functionality: Set Up Full League**
- **Stretch Goal: Email Game Reminders**
  - Send out email reminders about upcoming games
  - Email list that is sorted by teams or leagues
  - Ensure email reminders are sent to correct recipients
  - Ensure emails contain accurate game information
  - Ensure players can opt in/out of email notification

*Elle*
- **Complete User Story 12 functionality: Auto Generate Schedules**
- **Stretch Goal: Submit Suspension Reports**
  - Allow for reports to be submitted about players to flag them
  - Ensure suspension reports are saved with player records
  - Ensure suspended players are flagged appropriately
  - Ensure suspension status is visible to referees and admins

*Ethan*
- **Stretch Goal: Team Page and Team Logos**
  - Allow for teams to have individual logos

*General Tasks (Everyone)*
- Ensure security and accessibility and code documentation completeness
- Improve Bootstrap styling and potentially add CSS styling for an overall theme
- Update unittests for new features and old features that had their functionality altered

### What Was Completed:

- **User Story 12: Auto Generate Schedules**
- **User Story 11: Set Up Full League**
- **Stretch Goal: Calendar Game Schedules**
  - A lot of progress was made on this feature, but it is not completely
finished. The calendar is displaying and autofills from the schedule generator,
but there are still some bugs that need to be addressed
- **Addressed some (not all) of the bugs/issues from User Testing Day 1**
- **Improved styling of some pages**

### What Was Planned But Not Finished

- **Part of Stretch Goal: Calendar Game Schedules**
- **Stretch Goal: Email Game Reminders**
- **Stretch Goal: Team logos**
- **Stretch Goal: Submit Suspension Reports**
- **Finish comprehensive unitttesting for all features and update specific tests**

### Troubles/Issues/Roadblocks/Difficulties Encountered

- The main issue we had was that some of our final features, which are basically the ones
included in this iteration report, turned out to be more complex in certain aspects than we
originally expected. This required us to spend a lot more time debugging and addressing these 
issues, which also limited our progress on our other individual tasks. But overall, we made 
significant progress towards implementing all our planned features. 

### Adjustments to Overall Design

- Certain features needed to be adjusted to account for the new features that were implemented,
specifically the schedule auto-generate feature. Changes had to be made to the scores form so that
instead of users being able to select the teams and input a date, they had to pick from a drop-down
of all the existing games scheduled for that league.
- Changes also had to be made to the schedule auto-generating feature so that the Google calendar feature
could take the information from the database and auto-populate the calendar with the correct date and match
information.
- We also had to adjust the way that games were displayed on the league and team pages, which only required
changing the SQL queries to fetch different columns from the table and display them in a certain order.

### One Helpful Approach

- Once again, working together and meeting up to discuss features made everything a lot smoother, especially
since these last features intersect with each other more than the features at the start did. That way, when changes
needed to be made to features that were already 'completed', it was easier to understand what needed to be changed and
how since we were working together and could discuss/show what the exact issue was. 

### Important Thing We Learned

- We learned that certain User Stories end up being much more complicated than expected, and that maybe taking some more
time at the start to think more in depth about how a feature could be implemented and what requirements it has would be
beneficial in determining whether or not it should be an actual User Story to complete or a stretch goal. 

---

## Plan for the Remaining Days

**General Tasks**
- Complete/Update Unit Tests for All Features
- Debug/Address Rest of Issues from User Testing Day 1
- Document Code & Address Accessibility Concerns

**Complete Originally Assigned Stretch Goals if Possible**
- If not, ensure that in-progress features are completed and function with already finished
features.