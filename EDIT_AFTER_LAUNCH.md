# How to edit StoryScout after your website is live

**Yes — you can change the live website any time.** As long as you update the same GitHub repository connected to the same Render service, the URL remains the same.

## The easiest way: edit directly on GitHub

1. Go to GitHub and open your `storyscout-lite-web` repository.
2. Click the file you want to change (see guide below).
3. Click the **pencil icon / Edit this file** in GitHub's file view.
4. Make a small change and read it over.
5. Click **Commit changes**, with a descriptive message such as `Update website introduction`.
6. Visit Render -> your service -> **Events / Deploys**. With Auto-Deploy **On Commit**, Render rebuilds your website from this new version.
7. Open **the same website URL** and refresh to see the change. On a free service, allow for a new deploy / wake-up.

### What should I edit?

| Change you want | File | How |
| --- | --- | --- |
| Main heading, instructions, explanation | `lite_ui.py` | Find the first `gr.Markdown('# StoryScout Lite ...')` near the Gradio Blocks section. |
| Topic titles or angles | `lite_core.py` | Edit the entries in `TOPIC_BANK`. Keep the same tuple structure. |
| Suggested research scoring logic | `lite_core.py` | Edit `topics_with_evidence` — test carefully; avoid claiming predictions. |
| SPI or ICI weights | `lite_core.py` | Edit `SPI_WEIGHTS` or `ICI_WEIGHTS`; weights must sum to 100. Document any methodological revision. |
| Video review suggestions | `lite_core.py` | Edit `ICI_TIPS`. |
| Look/structure of tabs | `lite_ui.py` | Edit Gradio layout and components. |
| Public competitor reels or trend terms | `data/lite_competitor_reels.csv`, `data/lite_trends.csv` | Upload an updated, checked CSV to GitHub's `data/` folder, replacing the old file. |
| A new Python dependency | `requirements.txt` | Update carefully and check Render deploy logs. |
| Launch settings / port | `app.py` | Normally leave unchanged. |

## Examples

**Example 1: change the website heading**

Open `lite_ui.py`. Find the section around `with gr.Blocks` and change the literal text after `gr.Markdown('# StoryScout Lite ...')`. Do not accidentally remove the surrounding quotes, brackets or newline escapes. Commit the change.

**Example 2: add a topic idea**

Open `lite_core.py`, find `TOPIC_BANK = [`, and insert one entry **using the same six fields**:

```python
('How food prices respond to monsoon shocks',
 'Economics',
 'monsoon,food inflation,agriculture,vegetables',
 'Explain supply disruptions and consumer price effects',
 'Why does one delayed monsoon affect the price of dinner?',
 7),
```

The last number is estimated production hours, not a predicted view count. Save/commit. StoryScout will include that editorial idea next time the app loads.

**Example 3: update the public dataset**

Upload a revised public CSV to the `data/` folder. Render redeploys. Verify the updated data using the competitor view; private Google Drive files will not sync automatically.

## Do I need to buy a domain every time?

No. Your standard `onrender.com` URL stays associated with the service. You can buy a custom domain later if you want a branded link, but it's not necessary for a college project.

## What if I break the website?

GitHub keeps commit history. Use the **History** view to examine previous changes. You can reverse or restore an earlier version, then commit that correction. Render will deploy the latest connected commit. Render may also provide rollback options depending on the service plan and settings.

A failed deployment usually leaves the last successful version serving, but this isn't a substitute for testing important code changes.

## What cannot be done just by changing GitHub?

- Automatically make an uploaded MP4 analyse itself with AI (this version is **human-rated**).
- Permanently store visitor ratings on Render Free (requires a database or external durable store).
- Automatically sync your private Google Drive folder (requires a separate authorized integration).
- Produce real topic demand evidence from fictional or missing inputs.

**Good workflow:** first get the basic website live and working. Then change one thing at a time, commit, check Render logs, and retest the affected tab.
