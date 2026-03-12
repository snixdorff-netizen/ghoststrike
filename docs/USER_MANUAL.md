# GhostStrike Alpha User Manual

## Purpose

GhostStrike is an alpha product-development workspace. It helps you turn an idea or product challenge into structured outputs across research, concepting, evaluation, launch planning, and measurement.

This alpha is designed for testing. Some outputs are deterministic and some platform behaviors are still being refined.

## Logging In

1. Open the GhostStrike URL in your browser.
2. Enter the email and password provided by the GhostStrike team.
3. Click `Log In`.

If you were invited to collaborate on an existing project, you may also receive an invitation token. That token belongs in the `Accept Invitation Token` form, not in the password field.

## Main Areas

### Access

- Use this area to log in.
- If the team gave you an invitation token for a shared project, paste it into `Accept Invitation Token`.

### Start a Project

- Enter a project name.
- Enter a product brief with the problem, target user, constraints, and goal.
- Click `Create Project`.

### Projects

- Shows the projects you own and the projects shared with you.
- `Owned` means you created the project.
- `Shared` means another user granted you access.

### Project Control

This is the main working area for a selected project.

You will see:

- Current phase
- Project status
- Gate status
- Owner
- Project brief

Available actions:

- `Run Current Phase`: runs the current step immediately
- `Queue Current Phase`: places the step into the background worker
- `Run V1 Package`: runs a larger bundled workflow
- `Run Full Cycle`: runs the full workflow through measurement
- `Approve Gate`: advances the project when review is complete
- `Reject Gate`: stops progress and records a rejection decision

## How The Workflow Works

The platform moves through a structured sequence of phases:

1. EMPATHIZE
2. IDEATE
3. EVALUATE
4. REALIZE
5. MEASURE

After a phase runs, the project usually pauses at a human gate.

That means:

- the system has produced outputs
- a human should inspect them
- the next phase will not begin until someone approves or rejects the gate

## Reading Outputs

Inside a project, review:

- `Agent Outputs`: structured work products from the specialist agents
- `Message Log`: workflow and execution history
- `Jobs`: queued and completed background tasks
- `Events`: audit trail of important actions

Use these sections together. The output cards show content. The jobs and events show what happened operationally.

## Collaboration

If you own a project, you can invite collaborators:

- `Viewer`: can inspect the project
- `Editor`: can inspect and run workflow actions

If you receive an invitation token:

1. Log in
2. Paste the token into `Accept Invitation Token`
3. Submit it
4. The shared project should appear in your project list

## Feedback

Each project includes an `Alpha Feedback` section.

Use it to report:

- `GENERAL`: broad product impressions
- `BUG`: broken behavior
- `UX`: confusing or frustrating interactions
- `OUTPUT_QUALITY`: weak or unhelpful outputs

Please be specific. Good feedback includes:

- what you were trying to do
- what happened
- what you expected instead

## Recommended First Test

1. Log in
2. Create a project using the sample brief from [TEST_PRODUCT_BRIEF.md](/Users/stuartnixdorff/Documents/New%20project/docs/TEST_PRODUCT_BRIEF.md)
3. Run `V1 Package`
4. Review the outputs
5. Submit one feedback item

## Known Alpha Limits

- The platform is not yet a full production release
- Some agent paths are still deterministic rather than fully integrated
- Invitation delivery is token-based, not email-based
- Password reset is not yet implemented
- Admins create user accounts directly

## When To Contact The Team

Report to the GhostStrike team if:

- you cannot log in
- a project disappears
- a queued job never finishes
- outputs are empty or obviously broken
- the app becomes inaccessible
