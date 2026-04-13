# Change Request Document

## Scope Baseline
The original scope involves developing a User Authentication System including a login module, dashboard UI, and API integration, with a timeline of 2 weeks. Constraints include limited API access and dependencies on third-party authentication services.

## Meeting Findings
- The client requires login functionality supporting both email and Google authentication.
- The dashboard must track user activity and analytics.
- The estimated timeline is confirmed as 2 weeks.
- Action items include API design (3 days) and UI design (2 days).
- The client is responsible for providing API keys.
- A primary risk identified is the potential delay in third-party API integration.

## Change Summary
Formalization of specific authentication methods (Email and Google) and the addition of activity/analytics tracking to the dashboard requirements.

## Impact
- Backend: Requires implementation of two authentication flows and analytics data endpoints.
- Frontend: Requires UI for Google OAuth and analytics visualization.
- Timeline: Remains at 2 weeks, but requires tight coordination on API key delivery.

## Proposed Work
1. Design and implement Backend APIs for email and Google authentication.
2. Develop a Dashboard UI capable of displaying user activity and analytics.
3. Integrate Google Authentication API.
4. Set up analytics tracking logic.

## Acceptance Criteria
- Users can successfully log in via email.
- Users can successfully log in via Google authentication.
- Dashboard correctly displays user activity and analytics data.