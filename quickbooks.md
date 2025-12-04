1. The Problem We Are Solving
Your local community (Bellingham Cohousing) wants a centralized financial dashboard that:
Gives high-level visibility into:
Cash and investment balances
Year-to-date (YTD) spending vs. budget
Committee-level spending progress
Allows residents and committee leaders to drill down into:
Sub-categories
Individual line items
Detail as deep as the QuickBooks reports themselves
Reduces the manual work the treasurer currently does to share monthly/quarterly reports.
The core goal is transparent, self-service access to financial information while keeping QuickBooks as the single source of truth.
2. Functional Requirements Identified
A. Dashboard Structure
Two main sections:
Cash & Investments Summary
Three-line summary (bank accounts, investments/CDs, total cash+investments)
Drillable into individual accounts and sub-accounts
Mirrors the Balance Sheet detail
YTD Budget vs Actual
Community-wide summary
Clickable committee list
Drilldown from committee → category → sub-category → line items
Uses same structure as the management report
B. User Experience
High-level summaries visible immediately
Expandable sections enabling deeper visibility
Uses Q1 2025 report data (from the PDF) for the mock
Later: replaces static data with live QuickBooks data
3. Technical Approaches Discussed
We explored several ways to get the dashboard connected to QuickBooks data.
Approach 1 — Full QuickBooks API Integration (OAuth 2.0)
You originally aimed to build:
A secure, read-only app connecting directly to QuickBooks Online
Using OAuth 2.0 authorization flow
With a “Connect to QuickBooks” link sent to the treasurer (Kelly)
After authorization, your server stores access + refresh tokens
Dashboard automatically fetches real-time accounting data
We outlined the required steps:
Creating an Intuit Developer account
Creating an app (with accounting scope)
Setting up redirect URIs
Generating an authorization URL
Handling the authorization callback
Exchanging the authorization code for tokens
Calling the QuickBooks Accounting APIs
Pros
Fully automated
Always up to date
No manual reporting work for Kelly
Cons
Requires technical setup
Requires Kelly to authorize the app correctly
OAuth can be confusing for non-technical users
This approach remains the long-term solution, but may not be the easiest starting point.
Approach 2 — Kelly Creates a QuickBooks User for You (Simpler)
We discussed how onboarding friction could be removed:
If Kelly simply creates a QuickBooks login for you, then:
Option A — Report-only access
You download reports manually
Feed them into the dashboard prototype
No OAuth setup needed at first
Good for initial development
Low burden for Kelly
Option B — User with permission to “Connect Apps”
You log in as yourself
You click the “Connect to QuickBooks” link
You authorize the dashboard app directly
Kelly does nothing technical
You have full control of setup
Still allows eventual live QuickBooks integration
Pros
Removes technical load from Kelly
Streamlines testing and development
Lets you control the entire authorization process
Cons
Requires Kelly to add a user in Manage Users
Not yet “official automation” unless you use OAuth afterward
This approach simplifies everything and accelerates progress.
4. UI/UX Development Progress
We built a full HTML prototype with:
Cash & Investments Section
Three summary cards
Drilldown tree for:
WECU CDs
Checking/savings accounts
Vanguard/CD investments
Change vs prior period displayed
Budget vs Actual Section
Committee sidebar with percentage chips
Summary metrics for the selected committee
Drilldown tree with expandable rows for:
Categories
Sub-categories
Individual line items
A fully populated summary table for all committees
The mock uses exact structuring and data extracted from the Q1 2025 management report PDF.
This mock will later be replaced with live data from QuickBooks via the API.
5. The Approach We Are Currently Exploring
We pivoted from requiring Kelly to perform a technical OAuth authorization toward a simpler, more user-friendly workflow:
Current direction:
Kelly creates a QuickBooks user for you.
Either report-only
Or with permission to connect apps
You use that account to:
Access all reports directly
Build the dashboard with accurate data
Perform the OAuth flow yourself when ready
Avoid asking Kelly to handle developer workflows
The dashboard will:
Use mock data initially
Transition to real QBO API data once OAuth is wired up
Support both high-level summaries and deep drilldowns
Why this is the best current path
Fastest progress toward real data
Least overhead for Kelly
You maintain full control of the technical process
Nothing prevents later automation