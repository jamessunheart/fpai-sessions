# "Pending Edits" view — one-time AppFlowy setup (60 seconds)

This creates a bookmarked filter in the Master List that shows only the
edit requests Claude has filed, so you can process them in one batch
instead of scanning the whole list.

## Steps

1. Open `https://brain.zenvillagecr.com` and sign in.

2. Navigate: **General → 01 · Master List**.

3. At the top-right of the grid, click **+ New View** → **Grid**.
   (Using a *new view* rather than filtering the main grid so everyone
   else's view of the Master List stays untouched.)

4. Name the new view: **Pending Edits**.

5. Click **Filter** (funnel icon, top-right of the grid):
   - Add filter: **Title** → *contains* → `[Edit Request]`
   - Add filter: **Status** → *is not* → `🟢 Done`

   (Title prefix is used as the distinguisher rather than the Type field
   because Type had no pre-defined options — this was the path of least
   friction. If you'd rather use Type, add an "Edit Request" option to the
   Type field first, then swap the filter.)

6. Click **Sort** (next to Filter):
   - Sort by **Priority** → *Ascending* (P0 → P1 → P2)
   - Secondary sort: **Created** → *Oldest first*

7. Optional polish: click the three-dot menu → **Settings** → hide
   fields you don't need. Keep these visible: **Title**, **Priority**,
   **Notes**. Hide everything else — less visual noise during batch
   processing.

8. Copy the URL from your browser's address bar. **Bookmark it.**
   (It'll look like
   `https://brain.zenvillagecr.com/app/3ca578c1-.../<new-view-id>`.)

## Daily flow

Once this exists, your edit-processing loop is:

```
1. Open your "Pending Edits" bookmark
2. Top of the list = highest priority, oldest → click it
3. In the row detail, read the Notes field. It contains:
      - A deep link to the exact target database
      - The field → value changes to make
4. Open the deep link in a new tab, apply the edits to the target row
5. Come back to the Master List row, set Status = Done
6. Repeat until the Pending Edits view is empty
```

Typical time per edit: 30-60 seconds once you're in the groove.

## On your phone

Same bookmark works in mobile browsers. For fast mobile processing,
message `@zenvillagebot` with `/edits` instead — you get the same list
with one-tap links, formatted for small screens.

## When nothing shows up

- `/edits` says "No pending edits" → Claude hasn't filed any edit
  requests yet; the queue is empty. Good.
- The view is empty but you *expected* changes → the filter might have
  drift. Check that `Type=Edit Request` matches Claude's output; schema
  drift on that field name will quietly hide requests.

## Delegating to Jiji / Atlas

Same flow for them. Three things to set up (all one-time):

1. Share the "Pending Edits" bookmark URL with them.
2. Add them as an AppFlowy workspace member so they can edit rows.
   (Currently on the free tier, this is capped at 1 — needs either a
   paid upgrade or a second service-account trick. See the onboarding
   docs in `runbook/` for the workaround options.)
3. Agree on who owns the queue on which days. A shared Telegram channel
   where `/edits` is run every morning works well.
