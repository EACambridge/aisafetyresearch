# How aisafetyresearch.co.uk works, and how to edit it

This guide is for whoever looks after the site next. It explains every moving part in plain English and gives step-by-step instructions for the edits you're most likely to make. Last checked: 20 November 2026.

If you only read one section, read **Before you change anything** and the edit you need under **Common edits**.

---

## What the site is for

The site gets newcomers doing AI safety research. Working backwards from that:

1. Newcomers produce useful research ← small teams finish projects.
2. Teams finish projects ← teams keep meeting ← the match is workable and people get introduced quickly.
3. Good matches ← people sign up with accurate answers about topic, time and level.

So the machinery exists to: collect sign-ups, suggest teams, introduce them fast, check in weekly, notice when people go quiet, and show finished work. The weakest links are slow introductions, teams that can never find a shared time, and people drifting off. When you change something, ask which of those it helps.

---

## Before you change anything

1. **Everything runs from one Google account: ea.cambr@gmail.com.** It owns the spreadsheets, forms and scripts, and it's the only admin on the website. Sign in as it before editing anything below.
2. **Never paste a secret key into a chat, a document or the code.** Keys live only in the places listed under **Keys and where they live**. The Claude account is shared by the whole committee, so treat chats there as public.
3. **The website code is public** (it's a public GitHub repository). Spreadsheet and form IDs appearing in it is fine; keys are not.
4. **Test after every change.** Each edit below ends with a check.

---

## Where everything lives

| Part | What it does | Where to edit it |
|---|---|---|
| Website pages | Everything people see at aisafetyresearch.co.uk | GitHub repository [EACambridge/aisafetyresearch](https://github.com/EACambridge/aisafetyresearch), signed in as EACambridge. Changes go live about a minute after you commit. |
| Hosting | Serves the pages | GitHub Pages (repository Settings > Pages). Free. |
| Domain name | aisafetyresearch.co.uk | names.co.uk (DNS records). Don't touch the four GitHub A records, the www record or the `mail` records, or the site or sign-in emails will stop working. |
| Accounts | Sign-in, sign-up answers, teams, completed projects, forum threads and comments | Supabase project "EACambridge's Project" (`vidkjapmgeuomrqduycm`), hosted in Frankfurt: [dashboard](https://supabase.com/dashboard/project/vidkjapmgeuomrqduycm). Free plan. |
| Sign-in emails | Sends the "Email me a link" emails | Resend (resend.com, signed in as ea.cambr), from team@mail.aisafetyresearch.co.uk. Supabase sends through it (Supabase > Authentication > Emails > SMTP Settings). |
| Matching spreadsheet | People, proposed teams, teams, check-ins, "Needs attention" | [AI Safety Research sign-ups](https://docs.google.com/spreadsheets/d/1tOuBfJgnmWL2-pd7lLVjQfm24I6I5WYrK6dZrPT4x9Q/edit). Its **Matching** menu runs everything. |
| Matching code | Syncs sign-ups, suggests teams, writes intro emails, sends check-ins | Apps Script project ["AI Safety Research matching"](https://script.google.com/home/projects/1uBP-KoEEgbZDIFwIoK7xF7rD56N-kvpzrwUVD9-5iYS3_k5Ym9qz-Y-Y/edit) (Extensions > Apps Script from the spreadsheet). |
| Questions database | The research questions, interest counts and teams shown on the site | [AI Safety Research: questions database](https://docs.google.com/spreadsheets/d/1uB6p3rnhhEJuFfcrdDS-MK-BhIAEdJHkNzcEsbmxNt0/edit). Published to the web as CSV; the site reads that. |
| Completed projects and forum | Projects people share from their account, forum threads, and comments; all held for approval | Stored with accounts in Supabase (tables `posts`, `threads`, `comments`; set up by `supabase/forum.sql`). Reviewed on [admin.html](https://aisafetyresearch.co.uk/admin.html). The old Google research submission form was closed on 20 Nov 2026. |
| Weekly check-in form | The one-minute check-in emailed to matched people | [Form](https://docs.google.com/forms/d/1fWmtHbeLiXEDPYcVnx0fdM1X1ZMjvSfAG91lKR3VCxU/edit). Answers land in the "Check-ins" tab of the matching spreadsheet. |
| Idea checker | The "Check your idea" page | Apps Script project ["AI Safety Research idea checker"](https://script.google.com/home/projects/14q2ur1BxnEl8yZD0dx82jFOfCBtW8RUw6M66PW9ByboVacC6EI3mZDqC/edit), run as a web app. Uses Google Gemini plus arXiv and OpenAlex or Crossref. |
| Weekly research updates | Finds new papers for each question every Monday | GitHub Actions workflow `.github/workflows/research-updates.yml` running `scripts/research_updates.py`. It opens a pull request for someone to review; the research page only changes when that is merged. |
| Keep-alive | Stops the free Supabase project pausing | GitHub Actions workflow `.github/workflows/keep-accounts-awake.yml`, every three days. If it fails, GitHub emails the repository owner. |
| Old sign-up form | Retired | "AI Safety Research: find a research partner" (closed 19 Nov 2026). Its past answers stay in the "Form Responses 1" tab and are still matched. |

### The website files

| File | Page |
|---|---|
| `index.html` | Home page |
| `questions.html` | Research questions (reads the questions database) |
| `projects.html` | Current projects (typed directly into the page) |
| `research.html` | Weekly research updates (reads `data/research-updates.json`) |
| `completed.html` | Completed projects: the list, and each project's own page with comments (`completed.html?p=` number) |
| `forum.html` | The forum: thread list, starting a thread, and each thread's page with replies (`forum.html?t=` number) |
| `forum.js`, `community.css` | Shared comment code and styling for those two pages |
| `published.html` | Old address; sends visitors on to `completed.html` |
| `check.html` | Check your idea (calls the idea checker) |
| `login.html` | Sign up or sign in |
| `account.html` | The sign-up form, your team, sharing a completed project |
| `admin.html` | Organiser page: approve projects and forum posts, unlist projects, manage teams, see people. Only works for admins. |
| `privacy.html` | Privacy notice |
| `404.html` | Page not found |
| `app.css`, `auth.js`, `supabase-config.js` | Shared styling and sign-in code for the account pages |
| `sitemap.xml`, `robots.txt`, `CNAME` | Search engines and the domain name |

---

## How a person moves through the system

1. They click **Sign up to join a project** (or **Pick this question** on the questions page) and land on `login.html`. If they picked a question, the page remembers it.
2. They enter their email. Supabase sends a link through Resend. New people get the "Confirm your email address" email; returning people get "Your sign-in link".
3. The link opens `account.html`. The first time, they fill in the sign-up questions and tick the privacy box, then click **Join matching**. Answers are saved to their profile in Supabase.
4. **Every hour**, the matching script copies new sign-ups into the **People** tab as "Waiting", and updates the answers of anyone still waiting. It also emails ea.cambr about anything new waiting for review, and emails people when their project or thread goes live or gets an approved comment.
5. An organiser runs the weekly routine (below): **Suggest teams**, approves the sensible ones, and runs **Create intro emails**. This drafts one email per team in ea.cambr's Gmail, marks the people "Matched", lists the team on the questions page, and adds the team to its members' account pages.
6. Once weekly check-ins are on, matched people get a check-in every Monday. Their answers update People automatically. Asking to be rematched puts them back in the pool; choosing to leave removes them.
7. No reply for 14 days adds a nudge to the next email. After 21 days they're marked "Inactive" and left out of matching. People still waiting get one "still interested?" email at 14 days.
8. When a team finishes, someone shares the project from their account page. An organiser lists it and it appears on `completed.html`, where signed-in people can comment.
9. At any point, people can ask for feedback, find teammates or discuss questions on `forum.html`. Every thread, reply and comment is held until an organiser approves it.

People statuses in the People tab: **Waiting, Proposed, Matched, Rematch requested, Inactive, Left.**

---

## Common edits

### 1. Change wording on a page

1. Open the file on GitHub, for example [index.html](https://github.com/EACambridge/aisafetyresearch/blob/main/index.html), and click the pencil icon ("Edit this file").
2. Use Ctrl+F (Cmd+F on a Mac) in the editor to find the text. Change only the words between the tags (`<p>...</p>`, `<h2>...</h2>`); leave the parts inside `< >` alone.
3. Click **Commit changes**, write a short description, and commit to `main`.
4. **Check:** wait a minute, then reload the page on the live site (hold Shift while reloading to skip your browser's copy).

House style: plain British English, no jargon, no em dashes, warm and low-barrier for newcomers.

### 2. Add, edit or retire a research question

All questions live in the questions database. The site picks up changes within about five minutes (Google refreshes the published copy on its own schedule).

**To add a question:**
1. Add a new row at the bottom. Fill in: **ID** (next number, for example Q9), **Area**, **Question**, **Why it matters**, **Start with** (sources written as `Title (https://link); Title (https://link)`), and **Form option** (`Area: question in lower case`, which is what people pick and what the matching uses).
2. Copy the **People interested**, **Groups working** and **Status** cells (columns G, H, I) from the row above into your new row. They're formulas; don't type numbers into them.
3. **Check:** after five minutes the question appears on the questions page and in the account page's question list.

**To edit a question:** change the Question, Why it matters or Start with text freely. **Don't change the Form option once anyone has picked it**, because their sign-ups store that exact text. If you must, also change it in their People rows.

**To retire a question:** delete its row only once nobody waiting has picked it (filter People by the Question column).

### 3. Run the weekly matching (about 15 minutes)

In the matching spreadsheet, use the **Matching** menu:
1. **1. Update people from sign-ups.** Brings in any sign-ups the hourly sync hasn't yet.
2. **2. Suggest teams.** Proposals appear in "Proposed teams", each with the reasons. People who can't be placed are listed in "Needs attention" with why.
3. Read each proposal. Tick **Approve** for sensible ones. Edit or delete any you disagree with.
4. **3. Create intro emails for approved teams.** Then open ea.cambr's Gmail **Drafts**, read each intro and send it.
5. Look at **Needs attention** and follow up.

How teams are suggested: grouped by question (own questions by first area of interest); everyone must share at least one free time slot and a compatible way of meeting; anyone who asked for a similar level is only placed with the same level; whoever has waited longest is placed first; teams aim for 3 people (2 to 4); people who asked to be rematched are never put back with previous teammates.

### 4. Turn weekly check-ins on (or off)

Matching menu > **Turn on weekly check-ins (Mondays)**. They're **off** at the moment, because no teams exist yet. Turn them on once the first teams are introduced. To send a round immediately: **Send this week's check-ins now** (it shows how many people will be emailed and asks first).

### 5. Review shared projects

1. The hourly sync emails ea.cambr when something is waiting ("... waiting for review on AI Safety Research").
2. Sign in on the site as ea.cambr@gmail.com and open [admin.html](https://aisafetyresearch.co.uk/admin.html).
3. Under **Projects waiting for review**, read the summary and open the link. Click **List it** if it's real AI safety work, described honestly, with a link that opens. Otherwise click **Don't list** and email the author to say why.
4. Listed projects appear on Completed projects straight away. The author is emailed automatically within the hour.
5. To take a project down later, use **Remove from the site** under **Listed projects**. Its comments stop showing too.

### 6. Approve forum threads, replies and comments

1. Same email, same page: look under **Forum posts waiting for approval**.
2. **Approve** anything on-topic and civil. **Hide** spam, personal attacks, and anything sharing someone else's private details. Hidden posts stay visible to their author, marked "not shown".
3. When a comment on a project or a reply in a thread is approved, the project's or thread's author is emailed within the hour. People are never emailed about their own comments.
4. While signed in as an admin, you'll also see **Hide** links under every approved thread and comment on the public pages, for anything that slips through.
5. Aim to check at least every couple of days. A forum where posts sit unapproved for a week feels dead, and that is the main way it could fail.

### 7. Manage teams by hand

- Teams made through **Create intro emails** are added everywhere automatically: the Teams tab, the questions page and members' account pages. Members who signed up through the old Google Form have no account, so they won't see it there.
- **When a team finishes or breaks up:** set its Status in the Teams tab, change **Team status** (column M) in the questions database from "Active" to "Finished" so the question stops showing as being researched, and on [admin.html](https://aisafetyresearch.co.uk/admin.html) click **Mark finished**.
- To add or remove someone on the website side, use the Teams section of admin.html.

### 8. Change the sign-in emails

Supabase dashboard > Authentication > Emails > Templates. Edit **Confirm sign up** (new people) and **Magic link or OTP** (returning people). Keep the `{{ .ConfirmationURL }}` link in place. Send yourself a link from the sign-up page to check.

### 9. Add another website admin

1. The person signs in on the site once, so they have an account.
2. Supabase dashboard > SQL Editor > New query, then run (with their email):
   ```sql
   insert into public.admins (user_id)
   select id from auth.users where email = 'their.email@example.com';
   ```
3. **Check:** they can now open admin.html.

### 10. Change the matching settings

In the matching Apps Script, the `CONFIG` block near the top sets team sizes (`TEAM_MIN`, `TEAM_TARGET`, `TEAM_MAX`), when nudges and inactivity kick in (`NUDGE_AFTER_DAYS`, `INACTIVE_AFTER_DAYS`), the check-in day and hour, and the contact email. Edit, click Save (disk icon), and follow **Editing either Apps Script project** below.

### 11. Change the sign-up questions

This touches several places, so do it carefully and test with a spare email address (Gmail addresses accept a `+test` suffix, for example ea.cambr+test@gmail.com, which lands in the same inbox).
1. `account.html`: the form fields and the code that saves them.
2. Supabase: add a column to the `profiles` table (SQL Editor: `alter table public.profiles add column ...`).
3. Matching Apps Script: `syncFromAccounts_` (which columns it reads and where it writes them) and `PEOPLE_HEADERS` if People needs a new column.
4. `privacy.html`: the "What we collect" list.
5. The experience answers must keep the words the matcher looks for: "experienced", "supervised", "SPAR", "MARS" or "Pivotal" count as experienced; "some" counts as some experience; anything else counts as new.

### 12. Handle a request to delete someone's data

Work through every place their details can be:
1. **Account:** Supabase dashboard > Authentication > Users > find them > Delete user. This removes their profile, posts and activity. (They can also do it themselves from their account page.)
2. **Matching spreadsheet:** delete their rows in People, Check-ins and, if they used the old form, "Form Responses 1". Remove their name and email from any rows in Proposed teams and Teams.
3. **Questions database:** remove their name from **Members shown on site** (column O).
4. **Projects, forum threads and comments** are deleted automatically when their account is deleted in step 1. To remove one item only, use admin.html or ask them to delete it.
5. **Gmail:** delete intro or check-in threads if they ask.
6. Reply to confirm it's done.

### 13. Review the weekly research updates

1. Every Monday the workflow opens a pull request titled "Research updates: week of ...". Find it under the repository's **Pull requests** tab.
2. Open a few of the links and check each summary says what the original says. To drop an item, edit `data/research-updates.json` in the pull request and delete it.
3. Click **Merge pull request**. The research page and the "Recent related work" boxes on the questions page update a minute later.
4. If a week's run fails, GitHub emails the owner. To rerun: Actions tab > Weekly research updates > Run workflow.

### 14. Edit the idea checker

1. Edit the code in its Apps Script project and Save.
2. **Deploy > Manage deployments > edit (pencil) > Version: New version > Deploy.** Without this, the live page keeps using the old code. Keep the same deployment so the web address in `check.html` stays the same.
3. **Check:** run a test idea on the Check your idea page.
4. It allows 300 checks a day (`DAILY_LIMIT` in Script properties) to protect the free Gemini quota.

### Editing either Apps Script project

The code lives only in the Apps Script editor. Each project keeps its own history: open **Project History** (the clock icon on the left) to see or restore earlier versions. Before a big change, also make a copy of the project from its **Overview** page (the "i" icon) so you can go back. If a change needs a new kind of permission, Google asks you to approve it the first time it runs: click **Review permissions**, choose ea.cambr@gmail.com, then **Advanced > Go to ... (unsafe)** (it says that because it's our own script) and **Allow**.

---

## Keys and where they live

Never copy these anywhere else. To replace one, create a new key in the service, paste it into the same place, then delete the old one.

| Key | Used by | Kept in |
|---|---|---|
| Supabase secret key (`default`) | Matching script (reads sign-ups, adds teams) | Matching Apps Script > Project Settings > Script properties > `SUPABASE_SECRET_KEY` |
| Supabase publishable key | Website pages | `supabase-config.js`. This one is meant to be public; the database's row-level security rules protect the data. |
| Resend API key ("Supabase Integration") | Sign-in emails | Inside Supabase's SMTP settings (set up by Resend's Supabase integration) |
| Gemini API key | Weekly research updates | GitHub repository > Settings > Secrets and variables > Actions > `GEMINI_API_KEY` |
| Gemini API key | Idea checker | Idea checker Apps Script > Script properties > `GEMINI_API_KEY` |
| OpenAlex API key (optional) | Idea checker | Idea checker Script properties > `OPENALEX_API_KEY` |

Supabase is retiring its older "legacy" keys in early 2027. Nothing here uses them, so no action is needed.

---

## Limits to know about

1. **Sign-in emails:** Supabase allows 25 an hour (Authentication > Rate limits), and Resend's free plan allows 100 a day and 3,000 a month. A big publicity push could hit these; if so, raise the Supabase limit and consider Resend's paid plan.
2. **Check-in and intro emails** come from ea.cambr's Gmail, which can email about 100 people a day from scripts.
3. **Supabase free plan** pauses a project after a week without activity. The keep-alive job prevents this. If the site says accounts aren't working, open the Supabase dashboard and click **Restore**.
4. **Google's published copy** of the questions sheet refreshes every few minutes, so sheet edits take up to about five minutes to show on the site.
5. **Gemini's free tier** is sometimes overloaded. The research job now sends papers in batches of 40 and tries a second model, so one slow request no longer sinks the whole week.

---

## If something breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| Sign-in link never arrives | Spam folder, rate limit, or Resend issue | Check spam; Supabase > Authentication > Logs; Resend dashboard > Emails |
| Link says it has expired | Opened twice or after an hour | Request a new one |
| "Accounts aren't switched on yet" or account page won't load | Supabase project paused | Supabase dashboard > Restore project |
| New sign-ups not appearing in People | Hourly sync failing | Matching Apps Script > Executions; look for errors from `hourlySync`. A missing or replaced `SUPABASE_SECRET_KEY` is the usual cause. |
| Questions page shows no questions | Published CSV link broken | Questions database > File > Share > Publish to web: Sheet1 must be published as CSV |
| Research page empty or stale | Weekly pull request not merged, or the job failed | See edit 13 |
| Idea checker says "Something went wrong" | Gemini busy or daily limit reached | Wait and retry; check its Executions log |

---

## Known gaps and open decisions

1. **The first research-updates pull request (#1, from 7 November) is still waiting for review.** Until it's merged the research page is empty. The two Monday runs since then failed because Gemini was overloaded; the script has been fixed to cope.
2. **The forum starts empty.** An empty forum puts people off posting. Before promoting it, have two or three committee members start real threads (for example, feedback wanted on a current project, or "looking for a teammate on Q3"), and approve posts quickly in the first few weeks.
3. **Nobody owns matching yet.** Someone needs to run the weekly routine.
4. **The privacy notice names EA Cambridge as the data controller.** This was left to decide later.
5. **No peer rating form or measurement yet.** The "How it works" tab in the matching spreadsheet lists what to measure: days from sign-up to intro, share of teams meeting in week one, share still active after 4 and 8 weeks, share finishing a write-up.
6. **A committee test account exists** (ea.cambr@gmail.com, marked "Left" in People). It's harmless; leave it, since it's also the admin account.
