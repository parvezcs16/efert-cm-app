# Billing and Ledger

## Accounts
Support:
1. Employee personal account
2. Private guest responsibility through host employee
3. Official guest billing account/category

## Posting
Only validated served consumption creates the normal food charge.

Private guest:
- Post to host employee's ledger.
- Mark source as PRIVATE_GUEST.
- Preserve guest identity/reference for reporting.

Official:
- Post to official billing.
- Mark source as OFFICIAL_GUEST.
- Never post to host employee personal deduction.

## Views
Employee can see:
- Personal consumption
- Private guest consumption
- Official guest consumption where permitted
- Consolidated personal + private guest total

## Adjustments
Financial corrections are append-only.
Use reversal/adjustment entries.

Never:
- delete ledger entries
- silently overwrite amounts
- recalculate historical transactions from current menu prices

## Statements
Employee chooses:
- Daily
- Weekly
- Biweekly
- Monthly

Statement generation should be based on ledger transactions, not mutable order
state.
