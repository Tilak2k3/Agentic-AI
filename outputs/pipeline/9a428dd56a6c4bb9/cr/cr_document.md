# Change Request Document

## Scope Baseline
- Project: User Authentication System
- Deliverables: Login module, dashboard UI, and API integration.
- Timeline: 2 weeks.
- Constraints: Limited API access.
- Dependencies: Third-party authentication services.

## Meeting Findings
- Login functionality must support both email and Google authentication.
- The dashboard must be capable of tracking user activity and analytics.
- Backend API design is estimated to take 3 days.
- Frontend UI design is estimated to take 2 days.
- Client is responsible for providing API keys.

## Change Summary
Formalization of specific authentication methods (Email, Google) and dashboard requirements (Activity and Analytics tracking) based on the kick-off meeting.

## Impact
- Development: Backend must implement dual authentication logic.
- Integration: Dependency on Google authentication API.
- Timeline: Remains at 2 weeks, provided API keys are delivered on time.

## Proposed Work
- Design and implement API for email and Google login.
- Develop a dashboard UI featuring activity and analytics tracking.
- Integrate third-party authentication services.

## Acceptance Criteria
- Users can successfully log in via email.
- Users can successfully log in via Google authentication.
- Dashboard displays user activity and analytics data correctly.