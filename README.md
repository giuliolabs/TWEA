# TWEA Flywheel: GitHub starter kit (v1.0)

TWEA Flywheel is the automation tool for Tech-West England Advocates. It does four things:

- **Finds funding:** a curated, filterable list of funding routes worldwide, plus a weekly automatic scan for new ones.
- **Collects stories:** gathers TWEA news and drafts social posts from it.
- **Builds the quarterly newsletter** from that quarter's stories.
- **Keeps a person in charge:** nothing is published, posted or submitted without a person's approval.

This kit lets TWEA run the automations from **its own GitHub account and its own Claude API key**. Anyone who manages the project can then run, change or hand it on, without depending on one person's Claude account.

> Status: built and tested with simulated Claude replies on 4 Nov 2026. It **has not yet been run against the live Claude API**, so watch the first run of each job.

---

## How it works

| Job | When (UK time, GMT) | What it does | Where the result goes |
|---|---|---|---|
| Weekly funding scan | Mondays 07:45 | Claude searches funders, governments, foundations, companies and directories worldwide, adds new funding routes, and drafts up to 3 bid outlines | A **pull request** for review |
| Weekly news gatherer | Thursdays 17:40 | Claude finds public TWEA news (web only, no email), adds it as internal-only stories, and drafts posts for stories marked OK to share | A **pull request** for review |
| Quarter-end reminder | 1 Mar / Jun / Sep / Dec, 09:12 | Lists the quarter's stories and what's missing (no AI needed) | A GitHub **issue** |
| Quarterly newsletter | 20 Mar / Jun / Sep / Dec, 10:23 | Claude drafts the full newsletter from the quarter's stories and funding news for founders | A **pull request** for review |

GitHub schedules run in UTC. In British Summer Time they run one hour later in UK time.

**Human oversight:** every AI result arrives as a pull request labelled `needs-review`. A TWEA reviewer reads it, edits it if needed, and **merges** it (approve) or **closes** it (reject). Only merged content appears on the site. Nothing is ever posted to social media, emailed, or submitted to a funder.

## What's in the folder

```
index.html                 the TWEA Flywheel app (works on GitHub Pages)
data/                      opps.json, stories.json, queue.json, runs.json, profile.json
drafts/                    bids/, posts/, newsletters/ as plain markdown files
prompts/                   the instructions Claude follows for each job (edit freely)
scripts/run_job.py         runs one job: scan | news | newsletter | reminder
.github/workflows/         the four schedules
```

## Open it on any computer or phone

Once GitHub Pages is on (step 5 below), the app lives at

**https://giuliolabs.github.io/TWEA/**

(or `https://<account>.github.io/<repo>/` for a copy under another account). Anyone can open that link in any browser on any computer, tablet or phone, with nothing to install. On a phone, use *Share → Add to Home Screen* to get an app icon.

- The GitHub version shows the funding list, the stories and every draft that has been merged into `data/`. Filters, search and the funding map all work. Stamps and edits made in the browser are not saved; the saved record is the repository.
- Live Claude drafting (the "Draft a bid", "Draft posts" and "Build this issue" buttons) works in the Claude version published from Giulio's account. In the GitHub version, drafting happens through the scheduled jobs instead.
- To try it on a computer without the internet: download the repository (*Code → Download ZIP*), unzip it, and in that folder run `python -m http.server 8000`. Then open http://localhost:8000. Opening `index.html` directly by double-clicking also works, but it won't load the `data/` files.

## Set-up (about 30 minutes)

1. **Create the repository** (e.g. `giuliolabs/TWEA` for testing, then a TWEA-owned account or organisation for real use). Upload all the files in this folder, including the `.github` folder. Without a Claude API key the AI jobs simply skip themselves, so nothing breaks while you test.
2. **Add the Claude API key.** In the Claude Console, create a key for TWEA and set a monthly spending limit. In GitHub, go to *Settings → Secrets and variables → Actions → New repository secret*, name it `ANTHROPIC_API_KEY`, and paste the key.
3. **(Optional) Choose the model.** Under *Variables*, add `CLAUDE_MODEL` (default: `claude-sonnet-5-5`). Check the current model names at platform.claude.com/docs/en/models/overview.
4. **Let the jobs open pull requests.** Go to *Settings → Actions → General → Workflow permissions*, choose "Read and write permissions", and tick **"Allow GitHub Actions to create and approve pull requests"**.
5. **Publish the app.** Go to *Settings → Pages → Deploy from a branch → main / (root)*. The site appears at `https://<account>.github.io/<repo>/`.
6. **Edit `data/profile.json`** with TWEA's real details, especially its legal structure and income, because they decide which funds TWEA can apply to.
7. **Try each job once.** Go to *Actions*, pick a workflow, then *Run workflow*. Check the pull request it opens.
8. **Add reviewers.** Under *Settings → Collaborators*, add the comms team so they can review and merge.

## Day to day

- **Monday:** open the "Weekly funding scan – please review" pull request. Remove anything wrong, then merge.
- **Thursday:** review the news and post drafts. Post approved posts by hand, or through Metricool if TWEA chooses that option.
- **1st of the quarter's last month:** read the reminder issue and add any missing stories to `data/stories.json`.
- **20th:** review the newsletter draft in `drafts/newsletters/`, polish it with the comms team, merge, then send it from TWEA's email tool.
- **Bids:** once a bid outline is approved, a named TWEA person rewrites it in their own words and submits it on the funder's site, using the checklist in the app.

## The app on GitHub Pages vs. Claude

- **On GitHub Pages**, the app shows the merged data from `data/`. The live "Draft with Claude" buttons need a Claude account, so they show as unavailable. Use the published Claude version for live drafting.
- **On Claude** (the version Giulio publishes), everything works live and is saved in Claude's shared storage.

## Costs and safety

- GitHub Actions is free for public repositories and has a free monthly allowance for private ones.
- The Claude API is paid per use, and web searches are charged on top. Set a monthly limit in the Claude Console and check usage after the first month.
- The jobs never read anyone's email, never post and never submit. Remove the `ANTHROPIC_API_KEY` secret at any time to stop all AI jobs.

Prepared by Giulio Dajani (TWEA AI Automation Ambassador) for the TWEA meeting in Bristol, 2 December 2026.
