# Change Request Document

## Scope Baseline
The original scope involves developing a User Authentication System consisting of a login module, dashboard UI, and API integration, with a timeline of 2 weeks. Constraints include limited API access and dependencies on third-party authentication services.

## Meeting Findings
- The client requires login functionality supporting both email and Google authentication.
- The dashboard must be capable of tracking user activity and analytics.
- The estimated timeline remains 2 weeks.
- Action items include API design (3 days) and UI design (2 days).
- The client is responsible for providing API keys.
- A primary risk identified is the potential delay in third-party API integration.

## Change Summary
Formalization of specific authentication methods (Email and Google) and the addition of activity/analytics tracking requirements for the dashboard.

## Impact
- Technical: Requires integration with Google OAuth API.
- Schedule: No change to the 2-week timeline, but critical path depends on timely receipt of API keys.

## Proposed Work
1. Implement backend API for email and Google authentication.
2. Develop frontend UI for login and user dashboard.
3. Integrate analytics tracking into the dashboard.

## Acceptance Criteria
- Users can successfully log in via email.
- Users can successfully log in via Google authentication.
- Dashboard correctly displays user activity and analytics data.