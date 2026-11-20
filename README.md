# StoryScout Lite — public demo website

A no-API microeconomics-based research and content-quality prototype developed for VicharDesk.

**What it does**
- Compares selected public Instagram reels using relative public views/plays and engagement proxies.
- Suggests ideas from a curated VicharDesk topic bank, with supporting keywords from imported datasets.
- Calculates a six-factor editor-rated Story Potential Index (SPI).
- Allows a human reviewer to inspect an uploaded MP4, rate eight content-quality factors, and compare results against an explicitly labelled reference.
- Provides a small rule-based question helper, *not* a generative AI model.

**What it does not do**
- Automatically watch/understand videos or predict viral views.
- Access Instagram's private retention or follower data.
- Guarantee that topic suggestions will succeed.
- Permanently store public visitor ratings or uploaded drafts.

**This project contains synthetic example data.** Use the "SYNTHETIC sample data" checkbox for a reproducible demonstration. Don't present fictional statistics as real observations.

## Publish this on Render

Follow **`START_HERE_GITHUB_RENDER.md`**. It covers GitHub upload, Render configuration, going live, and troubleshooting for a complete beginner.

## Updating after publishing

Follow **`EDIT_AFTER_LAUNCH.md`**. Normally you edit files in GitHub, commit the changes to the `main` branch, and Render automatically deploys the new version to the same URL.

## Publish genuine research (optional)

See **`data/README_PUBLIC_CSV_FILES.txt`**. Only publish anonymized / permissible public research. Do **not** place private VicharDesk Insights, credentials, confidential drafts, or screenshots in a public repository.

## Test locally (optional)

Run `pip install -r requirements.txt` and then `python app.py`. Open `http://localhost:7860`. You do not need to do this to deploy via GitHub + Render.

**Hosting notes:** Render's free web service sleeps after approximately 15 idle minutes, and local files are not permanently saved. This demo uses its own bundled code and synthetic sample generation. Real public research is only available on the website when the owner commits sanitized public CSVs in the `data/` directory.
