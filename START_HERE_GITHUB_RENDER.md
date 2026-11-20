# From zero to a live StoryScout website (Windows beginner guide)

**Goal:** Upload a working Python/Gradio website to GitHub, then have Render put it online at an `https://...onrender.com` link. **No Gemini, API keys, Git commands, or Google Colab session required.**

## What you already have

This ZIP contains everything required to launch the working **public demonstration version**. It creates synthetic sample data at runtime. It does *not* contain private VicharDesk Insights or your actual Colab Drive research CSVs.

- `app.py` — starts the website. Don't change it initially.
- `lite_ui.py` — layout, tabs, button actions, explanations.
- `lite_core.py` — calculations, fixed topic bank, data loading, indices.
- `requirements.txt` — Python packages Render installs.
- `.python-version` — requests Python 3.11.11.
- `data/` — location for future public research CSVs; initially only a text instruction file.
- `README.md` — overview.
- `START_HERE_GITHUB_RENDER.md`, `EDIT_AFTER_LAUNCH.md` — your instructions.
- `.gitignore` — discourages committing some local secret/private files.

## A. Download and extract

1. Download the ZIP supplied in ChatGPT.
2. On Windows, open File Explorer -> Downloads. Right-click the ZIP -> **Extract All**.
3. Open the extracted folder; check you see `app.py`, `lite_core.py`, and `lite_ui.py` immediately in that folder. Do **not** upload the unopened ZIP to GitHub.
4. If `.python-version` seems missing, in File Explorer select **View -> Show -> Hidden items**. (You can alternatively set the `PYTHON_VERSION=3.11.11` environment variable in Render.)

## B. Set up GitHub

1. Go to https://github.com/signup and create/verify an account, or log in.
2. Go to https://github.com/new.
3. Enter repository name `storyscout-lite-web` (or another name you prefer).
4. Select **Public** for a shareable source-code portfolio. **Private** is also possible if you authorize Render to access it. Never upload confidential research files to either by mistake.
5. You can leave **Add README**, **Add .gitignore** and **Choose a license** unchecked, because the ZIP already includes a README and .gitignore.
6. Click **Create repository**. Your new repository is initially empty.
7. On the empty repository page, click **uploading an existing file**. If GitHub instead shows your new repo's file list, use **Add file -> Upload files**.
8. From the extracted project folder, drag the actual **files and `data/` folder** into the GitHub upload area. Check that `app.py`, `lite_core.py`, `lite_ui.py`, `requirements.txt` all appear. The Python files must be at the repository **root**, not nested in a ZIP-named folder.
9. At the bottom, enter a message like `Initial StoryScout Lite website` and click **Commit changes** (or the current GitHub commit confirmation wording).
10. Back on the repo homepage, check these files are visible:

    app.py
    lite_core.py
    lite_ui.py
    requirements.txt
    .python-version
    README.md
    data/README_PUBLIC_CSV_FILES.txt

If `.python-version` wasn't uploaded, don't panic: you'll be able to set the Python version in Render.

## C. Connect Render

1. Visit https://dashboard.render.com/register; log in or sign up (the GitHub sign-in option is convenient).
2. In the Render dashboard select **New -> Web Service**.
3. Choose **Git Provider / GitHub**, authorize Render to access your GitHub repositories, then choose `storyscout-lite-web`.
4. Enter the following settings (labels can vary slightly):

| Render setting | Value |
| --- | --- |
| Name | `storyscout-lite` (or a unique name Render accepts) |
| Language / Runtime | `Python` |
| Branch | `main` |
| Root Directory | leave blank |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |
| Instance | `Free` |
| Auto-Deploy | `On Commit` (usually the default) |

5. **Python-version safety:** The included `.python-version` normally tells Render to use `3.11.11`. If it is not in GitHub, go to your Render service's **Environment** settings and add `PYTHON_VERSION` with value `3.11.11`. Do not set two conflicting version values.
6. Click **Deploy Web Service** / **Create Web Service**.
7. View the **Events / Logs** tab while Render installs packages and starts Python. Wait for `Live` / `Your service is live` or equivalent.
8. Click the displayed `https://<your-service>.onrender.com` URL. Your website is now public. Copy that actual address for your presentation.

## D. First-visit checklist

1. The header reads **StoryScout Lite · Content Research & Quality Index**.
2. If no genuine public CSVs have been published yet, enable **Use SYNTHETIC sample data**.
3. In **Competitor Market**, click **Analyse competitor market**. You should see fictional examples clearly labelled as synthetic.
4. In **StoryScout Topic Finder**, click **Suggest and rank topics**. You should see curated content ideas and supporting test evidence.
5. In **Reel Quality Index**, click **Show current reference benchmark**. The demo reference is fictional / labelled.
6. For the reel score, rate all 8 factors and check **I have watched/reviewed the reel** before calculating. No AI video assessment takes place.
7. Test **Ask StoryScout** with `Suggest topics`. It is a rule-based guide, not Gemini.
8. Test the site on your phone or incognito browser window to verify it is publicly accessible.

**Important:** When using the synthetic sample in your presentation, label it a functionality demonstration. Don't claim those figures are real industry outcomes.

## E. Add real research *after* the website works (optional)

Do not rush this step. Real data are **not required to get the site online**.

1. Use your original Colab Lite app to export sanitized public `lite_competitor_reels.csv`, `lite_trends.csv`, and (if completed) `lite_ici_reviews.csv`.
2. Check them for private information and accurate provenance. Do not upload personal Insights screenshots or private metrics.
3. On GitHub, navigate to `data/`, then **Add file -> Upload files**. Upload the real public CSVs with those exact names and **Commit changes**.
4. Render should redeploy from the new commit. When it is live, turn **SYNTHETIC** mode off to inspect genuine research mode. If data don't appear, check file names and columns in `data/README_PUBLIC_CSV_FILES.txt`.

The website does **not** directly connect to or edit your private Google Drive. Changes to your Colab Drive CSVs do not automatically affect the public website.

## F. If you need to change the website

Use **`EDIT_AFTER_LAUNCH.md`**. Changes committed to the same GitHub repository's `main` branch will generally update the existing Render website, preserving the public URL.

## G. Common problems

| What you see | Likely cause and fix |
| --- | --- |
| `ModuleNotFoundError: lite_core` | Files are not all at repo root; re-upload `lite_core.py` beside `app.py`. |
| `requirements.txt` not found | Build command is correct but the file is in a nested folder; move files to repo root. |
| Incompatible Python version | Ensure `.python-version` contains `3.11.11` or set Render `PYTHON_VERSION=3.11.11`. |
| Service failed to bind a port | `app.py` must use `0.0.0.0` and Render's `PORT`; the supplied file already does. |
| Blank competitor research | Use SYNTHETIC demo, or commit sanitized public CSVs to `data/`. |
| ICI says provisional reference | Fewer than 5 fully scored distinct competitor videos are loaded; this is an expected research limitation. |
| Site seems stuck starting | Free Render services sleep after ~15 idle minutes and can take around a minute to wake. |
| Updated code isn't showing | Open Render Events, ensure auto-deploy is **On Commit**; or use **Manual Deploy -> Deploy latest commit**. |
| A user's saved review vanished | Public site deliberately doesn't persist visitor reviews; free Render filesystem is ephemeral. |

## H. Security rules

- Never commit API keys, passwords, .env files, private VicharDesk Insights, unreleased MP4s, or personal information.
- The public MP4 upload is for user-guided video playback. Users should only upload drafts they are allowed to share with a third-party hosting service.
- Even if the GitHub repository is private, the Render website itself is public unless you add access protection.
- GitHub stores version history. Removing an accidentally committed secret from the latest file is not the same as removing it from Git history; rotate any exposed credentials.

## Authoritative documentation

- GitHub: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- Render first deploy: https://render.com/docs/your-first-deploy
- Render automatic deploys: https://render.com/docs/deploys
- Render free limitations: https://render.com/docs/free
- Render Python version: https://render.com/docs/python-version
