RETROSPECTIVE SPRINT 2 (Team 13)
=====================================

The retrospective should include _at least_ the following
sections:

- [process measures](#process-measures)
- [quality measures](#quality-measures)
- [general assessment](#assessment)

## PROCESS MEASURES

### Macro statistics

- Number of stories committed vs done : 3 vs 3
  - MH-04, MH-05 and MH-06 have unit and integration tests, code review, code on dev and an E2E test with Playwright.
- Total points committed vs done : 8 vs 8
- Nr of hours planned vs spent (as a team) : 83h 30m vs 79h 15m

> Note: MH-01, MH-02 and MH-03 are sprint 1 stories. At the end of sprint 1 they were not done because their E2E tests were not on dev yet. In this sprint we finished them with tasks MH-53, MH-54, MH-65 and MH-66, counted in #0, so now they meet the DoD. Their 13 points are not in the numbers above. MH-53 and MH-54 keep the 4h estimate they had in sprint 1, but 2h 30m of their work was done and counted at the end of sprint 1, so here they have only the 30m of this sprint.

**Remember**  a story is done ONLY if it fits the Definition of Done:

- Unit Tests passing
- Code review completed
- Code present on VCS
- End-to-End tests performed

> Please refine your DoD

- Every PR is checked by another member, and the automatic tests must be green, otherwise it cannot be merged into dev.

### Detailed statistics

| Story                            | # Tasks | Points | Hours est. | Hours actual |
| -------------------------------- | ------- | ------ | ---------- | ------------ |
| _#0_                             | 17      | -      | 35h        | 30h 20m      |
| MH-04 Check availability         | 6       | 3      | 14h 30m    | 16h 05m      |
| MH-05 Provide party requirements | 6       | 2      | 13h        | 13h 10m      |
| MH-06 Change a booking           | 9       | 3      | 21h        | 19h 40m      |
| **Total**                        | **38**  | **8**  | **83h 30m**| **79h 15m**  |

> place technical tasks corresponding to story `#0` and leave out story points (not applicable in this case)

- Hours per task  <span style="color:red">per person</span>  (average, standard deviation): 1.62h, 0.95h (49 task/person pairs)

  | Person          | Tasks | Hours spent | Average | Std dev |
  | --------------- | ----- | ----------- | ------- | ------- |
  | Andrea Lanzetti | 8     | 16h 06m     | 2.01h   | 0.81h   |
  | Bai Han         | 9     | 16h         | 1.78h   | 0.72h   |
  | Edwin Liby      | 7     | 13h 24m     | 1.91h   | 0.92h   |
  | Luca Canonico   | 17    | 17h 15m     | 1.01h   | 0.86h   |
  | Zhou Xiao       | 8     | 16h 30m     | 2.06h   | 0.85h   |

- Total task estimation error ratio: sum of total hours estimation / sum of total hours spent -1 = 83.5 / 79.25 - 1 = 0.05

## QUALITY MEASURES

- Unit Testing:
  - Total hours estimated: 5h
  - Total hours spent: 5h
  - Nr of automated unit test cases: 46
  - Coverage (if available): 77% with the unit tests only, 91% with all the backend tests
- Integration testing:
  - Total hours estimated: 9h 30m
  - Total hours spent: 8h
- E2E testing:
  - Total hours estimated: 4h 30m
  - Total hours spent: 4h 45m
  - 9 automated tests with Playwright, at least one for every story of sprint 1 and sprint 2
- Code review:
  - Total hours estimated: 8h
  - Total hours spent: 7h 30m

> Note: three tasks (MH-53, MH-73, MH-88) mix integration and E2E testing, we counted them under integration.

## ASSESSMENT

- What caused your errors in estimation (if any)?

  - In total we spent 5% less than the estimate, mostly because the tasks of MH-03 kept the 4h estimate they had in sprint 1, while most of their work was done in sprint 1.
  - One member wrote the code of tasks assigned to another member, who was already working on them on his own branches.

- What lessons did you learn (both positive and negative) in this sprint?

  - Asking for an approved PR and green tests before merging into dev worked well, nothing reached dev without a review.
  - The reviews tried the features with the sample data, and they found real bugs before they reached dev.
  - We asked the PO about the rules of MH-06 at the start of the sprint, so we had the answers before writing the code.
  - When the first plan went over 80 hours we removed MH-07 right away, so the sprint stayed within our capacity.
  - Big PRs with many tasks inside were hard to review, had conflicts and repeated code that already existed.
  - We took an unclear answer of the PO as a rule, and after issue #47 we had to change how the seats of a table work.
  - The test tasks were moved to To Verify while the tests were still on a branch without a PR. The PR arrived the evening before the demo without E2E tests, so the E2E tests and the last fixes were done by another member on the last morning.

- Which improvement goals set in the previous retrospective were you able to achieve?

  - No merge into dev with failing tests or without the approval of another member: done, GitHub blocks it now.
  - Take a story only if we can finish it with its E2E test: done, all three stories have their E2E test.

- Which ones you were not able to achieve? Why?

  - Log the hours when the task is finished: most of the team did it day by day, but some members logged part of their hours a few days after the work.

- Improvement goals for the next sprint and how to achieve them (technical tasks, team coordination, etc.)

  - We would like every task to start from an updated dev, checking the code that is already there, so that PRs no longer bring back old code or repeat code that already exists.
  - We would like the E2E tests of each story in their own task, separate from the integration tests, and written right after the story is on dev.

- One thing you are proud of as a Team!!

  - In this sprint every change went into dev through a PR reviewed by another member.
