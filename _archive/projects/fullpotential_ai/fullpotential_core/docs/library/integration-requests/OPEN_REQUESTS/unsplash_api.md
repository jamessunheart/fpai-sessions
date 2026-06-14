# Unsplash Photo API Integration Request

## Request ID
`unsplash-001`

## Service Name
Unsplash Developers API

## Purpose
Enable the Full Potential AI dashboard to dynamically load high-quality, professional photos for:
- Team collaboration imagery
- Workspace/productivity visuals
- Tech/AI themed backgrounds
- Authentic, diverse professional photos

This makes the dashboard more personable and professional without fake stock photos.

## What the Helper Needs to Do

### Step-by-Step Instructions:

1. **Sign up as Unsplash Developer**
   - Go to: https://unsplash.com/developers
   - Click "Register as a Developer"
   - Create account (email + password)
   - Verify email

2. **Create Demo Application**
   - Go to: https://unsplash.com/oauth/applications
   - Click "New Application"
   - Accept terms
   - Application name: "Full Potential AI Dashboard"
   - Description: "Dynamic photo integration for AI coordination dashboard"

3. **Get Access Key**
   - Once created, you'll see:
     - Access Key (this is what we need!)
     - Secret Key (keep this safe too)

4. **Test the Key** (optional but recommended)
   - Try: `curl "https://api.unsplash.com/photos/random?client_id=YOUR_ACCESS_KEY"`
   - Should return JSON with photo data

## Delivery Format

Create folder: `COMPLETED/unsplash-001/`

Files needed:
- `credentials.txt` - Contains Access Key and Secret Key
- `test_response.json` - Sample API response (optional)
- `notes.md` - Any issues encountered or special notes

## Status
- [x] Open
- [ ] In Progress (Helper: ______)
- [ ] Completed
- [ ] Integrated into Dashboard

## Priority
- [ ] Critical
- [x] High
- [ ] Medium
- [ ] Low

## Estimated Time
5-10 minutes (signup + app creation)

## Notes
- Free tier allows 50 requests/hour (plenty for our dashboard)
- No credit card required
- We only need the Access Key for basic integration
- Keep Secret Key safe for future advanced features

## Integration Plan (Once Delivered)
1. Add API key to dashboard environment variables
2. Create photo service client
3. Integrate into homepage hero sections
4. Cache photos to reduce API calls

---

**Helper: When you complete this, move this file to `IN_PROGRESS/` while working, then to `COMPLETED/` with the credentials.**

**Questions? Check with the command center or leave notes in your delivery.**
