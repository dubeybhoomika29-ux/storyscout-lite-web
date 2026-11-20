# StoryScout Lite — Live Website Fix (no synthetic data)

This is a replacement for the earlier GitHub + Render release. It adds user-facing CSV upload controls and removes the synthetic-demo toggle from the website. It uses Python, pandas and Gradio; no Gemini API is needed.

## Update your EXISTING website (keep its URL)

1. Extract `StoryScout_Lite_Real_Data_Uploads_Fix.zip` on your computer.
2. Open the **existing** GitHub repository linked to your Render Web Service. Do not create a new repository or new Render service.
3. Click **Add file > Upload files** (if necessary use the edit/pencil control for individual files).
4. Upload the **contents** of the extracted folder to the repository's root, including `app.py`, `lite_core.py`, `lite_ui.py`, `requirements.txt`, and `.python-version`. Do not upload the ZIP itself, and do not put these files inside another subfolder.
5. Commit the changes to `main` with a message such as `Add real dataset uploads and remove demo toggle`.
6. In Render, choose the existing service; open **Events** or **Deploys** and check its latest deployment. With Auto-Deploy enabled, Render starts redeployment from the GitHub commit. Otherwise click **Manual Deploy > Deploy latest commit**.
7. Reload the **same** website URL. The first tab should be `1 · Upload Research` and no synthetic checkbox should appear.

If you still see the old page, verify that Render deployed the correct repository and commit. Hard-refresh your browser (Ctrl+Shift+R).

## First working session

1. Open **1 · Upload Research**.
2. Upload your Apify `competitor_reels.csv` or original Apify `.csv`/`.json`; press **Import public reels**. It should show the reel count and a preview.
3. Upload the original Google Trends Trending Now `.csv`; optionally enter the collection date; press **Import Google Trends**. Google Trends files with a short preamble are handled by the importer.
4. Open **2 · Competitor Market** and press **Analyse competitors**.
5. Open **3 · StoryScout Topic Finder**, select a category (or All) and press **Suggest topics from loaded research**. The suggested titles are from a fixed editorial library and the displayed evidence is from uploaded data.
6. Open **4 · Reel Quality Index**. Upload/play a reel, watch it, score all eight factors, tick the confirmation box, and press **Calculate complete ICI comparison**. **The video is not analysed automatically.**
7. For a *data-derived* ICI comparison, score at least five distinct **competitor** reels and use **Add reviewed competitor reel to session benchmark**, or import a completed review CSV. Before that, the 80/100 comparison is an explicitly provisional editorial target, not an industry finding.
8. For VicharDesk performance rates, use **5 · Performance Feedback** and enter verified Insights counts; these numbers are not automatically obtained from screenshots.

## Keeping your data after a restart

CSV uploads on the public site are **per browser session**. They are not permanently stored on Render or shared with other visitors.

To preload *approved public research* for every future visitor:

1. On the first tab, click **Download loaded research CSVs**.
2. Save the ZIP. Extract its `data/` folder.
3. Inspect and sanitize the exported files before sharing. Remove confidential observations and any personal or nonpublic information.
4. In GitHub, open your repository's `data/` directory, upload:
   - `lite_competitor_reels.csv`
   - `lite_trends.csv`
   - `lite_ici_reviews.csv`
5. Commit the files. Render will redeploy; when the website restarts it reads these CSVs automatically. Visitors can still upload their own independent files without overwriting the shared data.

Do not upload VicharDesk private Insights, API tokens, respondent records, or unlicensed video files to a public GitHub repository.

## The minimal ICI CSV format

`video_id,source_type,reviewer,review_date,hook,narrative,clarity,visuals,pacing,relevance,shareability,brand_cta`

Use `competitor` in `source_type` and integers from 0–5 for each factor. Blank scores are not counted. At least five **different** competitor video IDs with all factors present are required for a preliminary empirical reference. The template in `templates/ici_reviews_blank.csv` is empty on purpose.

## Expected differences versus the old site

- The first tab contains Apify, Google Trends and ICI review CSV inputs.
- The top shows counts from real imported research only.
- Synthetic demo mode and the demo checkbox are absent.
- Comparisons and topic research refresh from the files that you upload *in your current session*.
- Nothing on the site requires Gemini, an API key, or background scraping.

## Troubleshooting

- **Still showing synthetic mode:** Render is running the old commit. Check the connected repository, `main` branch, and deploy logs. Refresh the page after the deployment finishes.
- **No reels detected:** Check the CSV header and original Apify field names. The import accepts common Apify exports and previous StoryScout normalized CSVs.
- **No trends detected:** Export **CSV from Google Trends > Trending Now** (India), rather than copying the HTML page or uploading an Excel file.
- **ICI stays provisional:** Blank placeholder reviews do not count; complete all eight ratings for at least five distinct competitor reels.
- **My data disappeared on refresh:** Use the download-and-publish steps above; free Render has ephemeral storage.
- **Upload is too large:** Reduce the MP4 size; the app imposes an 80 MB per-file limit.

This is an accessible research prototype, not an AI video scorer or a predictor of future Instagram views.
