SPRINT 1 RETROSPECTIVE (Team 13)
================================

The retrospective includes the following sections:

- [process measures](#process-measures)
- [quality measures](#quality-measures)
- [general assessment](#assessment)

## PROCESS MEASURES

### Macro statistics

- Number of stories committed vs done : 3 vs 2
- Total points committed vs done : 13 vs 3
- Nr of hours planned vs spent (as a team) : 80h vs 72h

**Remember**  a story is done ONLY if it fits the Definition of Done:

- Unit Tests passing
- Code review completed
- Code present on VCS
- End-to-End tests performed

> Please refine your DoD

### Detailed statistics


| Story                       | # Tasks | Points | Hours est. | Hours actual |
| --------------------------- | ------- | ------ | ---------- | ------------ |
| _#0_ Infrastructure & Auth | 13      | -      | 37h        | 35h          |
| #2 Define slot capacity     | 8       | 5      | 15h 30m    | 15h          |
| #1 Book a table             | 9       | 5      | 18h 30m    | 17h 10m      |
| #3 Recieve confirmation     | 5       | 3      | 9h         | 4h 30m       |

> place technical tasks corresponding to story `#0` and leave out story points (not applicable in this case)

- Hours per task  <span style="color:red">per person</span>  (average, standard deviation)
  average: 1.95h, standard deviation: 0.67h(40m)
- Total task estimation error ratio: sum of total hours estimation / sum of total hours spent -1
  $\frac{80\text{h (estimation)}}{72\text{h (spent)}} - 1 = 0.111$ Total task estimation error ratio = 11.1%

## QUALITY MEASURES

- Unit Testing:
  - Total hours estimated
    7.5 h
  - Total hours spent
    7 h
  - Nr of automated unit test cases
    18
- Integration testing:
  - Total hours estimated
    5 h
  - Total hours spent
    3.5 h
- E2E testing:
  - Total hours estimated
    4 h
  - Total hours spent
    1 h
- Code review:
  - Total hours estimated
    4.5 h
  - Total hours spent
    4.5 h

## ASSESSMENT

- What caused your errors in estimation (if any)?

  - Some team members worked remotely, which negatively impacted overall collaboration efficiency. However, when estimating task times, we did not adequately account for the extra communication overhead and delays caused by asynchronous collaboration due to remote work.

  * Testing started too late, causing all tasks to pile up and be closed at the very end of the sprint. The bottleneck shifted to the testing phase, causing many movements happened late.
  * Poor communication during API integration led to misunderstandings. Fixing these integration issues took extra time that was not covered in our initial estimates.
- What lessons did you learn (both positive and negative) in this sprint?

  - **Positive:** The team's awareness of code quality and testing has improved. Learning from the previous sprint, we attempted to integrate code earlier this time, avoiding the disaster of merging in the last few hours.
  - **Negative:** We realized that the "three-line check-in in the chat every day" and "replying within 24 hours" rules set in the last sprint are highly insufficient for tasks requiring high-frequency, synchronous interaction, such as API integration. Furthermore, if testing does not proceed concurrently with development, task cards will still pile up at the last minute.
- Which improvement goals set in the previous retrospective were you able to achieve?

  - We partially achieved the goal to "integrate early." Compared to the last sprint, we front-loaded the integration of backend business logic with the frontend, preventing all conflicts from clustering on the day before the demo.
- Which ones you were not able to achieve? Why?

  - We failed to completely avoid the phenomenon of "closing tasks in a batch at the end (a steep drop at the tail of the burndown chart)." Although code integration was moved up, testing started too late, causing tasks that met the Definition of Done to still pile up and only be moved to the 'Done' column at the very end.
- Improvement goals for the next sprint and how to achieve them (technical tasks, team coordination, etc.)

  1. **Implement Shift-left Testing and Incremental Task Closing:** To address task pile-ups caused by late testing, the next sprint requires testing to be synchronized with code development. Unit tests must be written alongside the development of each story. Developers must test and move the task cards immediately after completing a minor feature, rather than leaving it for one person to batch process at the end.
  2. **Establish API Contracts and Set Core Working Hours:** To address delayed API communication and inefficiencies from remote work, the frontend and backend must collaboratively define and freeze API documentation in a meeting before writing any code. Additionally, we will set a specific half-hour of "Core Hours" every two days for both remote and local members. During this time, everyone must be online and responsive, dedicated strictly to resolving blockers that require high-frequency communication, such as API integration.
- One thing you are proud of as a Team!!

  - Despite facing the challenges of remote work and communication barriers during API integration, the team ultimately worked together to resolve the interface issues. Moreover, compared to the previous sprint, we demonstrated a more mature perspective in reflecting on deeper process issues, such as our testing cadence and remote collaboration.
