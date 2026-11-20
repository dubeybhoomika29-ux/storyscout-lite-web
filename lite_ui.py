"""Gradio interface for the offline StoryScout Lite prototype."""
import pandas as pd
import gradio as gr
import lite_core as sc

BASE = None

def init_app(base):
    global BASE
    BASE=sc.choose_paths(base)
    sc.make_demo(BASE)

    def summary(demo):
        reels=sc.load_reels(BASE,demo); trends=sc.load_trends(BASE,demo); bm=sc.industry_benchmark(BASE,demo)
        label='**SYNTHETIC DEMONSTRATION** — all sample metrics are invented for interface testing.' if demo else '**REAL RESEARCH MODE** — only uploaded / existing records are used.'
        return (f'{label}\n\n'
            f'**Public reels:** {len(reels)} · **Google Trends records:** {len(trends)} · '
            f'**Completed distinct competitor reviews:** {bm["count"]}\n\n'
            f'**ICI reference:** {bm["score"]:.0f}/100 — {bm["status"]}.\n\n'
            'No external API, automatic video analysis or prediction model is running.')

    def add_apify(path,demo):
        if not path:return 'Please upload a CSV or JSON file first.',pd.DataFrame()
        try:
            result=sc.import_reels_file(BASE,path)
            d=sc.load_reels(BASE,False)
            msg=(f'Imported {result["imported_rows"]} records. Research database now has '
                 f'{result["unique_rows"]} unique reels and {result["valid_metric_rows"]} with a public count. '
                 'Switch **Synthetic demo** OFF to inspect your real data.')
            cols=['creator','caption','metric','metric_basis','category']
            return msg,d[cols].head(12)
        except Exception as e:return f'Import problem: {e}',pd.DataFrame()

    def add_trends(path,date_text):
        if not path:return 'Please upload the exported CSV file first.',pd.DataFrame()
        try:
            result=sc.import_trends_file(BASE,path,date_text.strip() or None)
            data=sc.load_trends(BASE,False)
            return (f'Imported {result["new_rows"]} trends; {result["total_rows"]} now stored. '
                    f'{result["relevant_by_keyword"]} received a relevant topic classification via keyword matching. '
                    'Others remain available but are not automatically recommended.'),data.head(12)
        except Exception as e:return f'Trends import problem: {e}',pd.DataFrame()

    def report_file(demo):
        return sc.export_research_report(BASE,demo)

    def competitors(demo):
        d=sc.load_reels(BASE,demo)
        if d.empty:return 'No competitor records yet. Import Apify CSV/JSON under **Load Data**, or enable synthetic demo.',pd.DataFrame(),pd.DataFrame()
        kinds=d['metric_basis'].value_counts().to_dict()
        cover=int(sc.competitor_metrics(d)['relative_performance'].notna().sum())
        warning=('**SYNTHETIC DEMO:** This is fictional data. ' if demo else '')
        desc=(f'{warning}**{len(d)} reels across {d["creator"].nunique()} accounts.** '
              f'Metric types: {kinds}. Relative performance is calculated against each creator’s own median, '
              f'using the *same* count type; {cover} rows have a usable baseline. '
              'Likes+comments divided by public count is an engagement proxy, not engagement per reach. '
              'Categories are keyword-classified when the source did not provide them.')
        table=sc.market_table(d)
        top=sc.competitor_metrics(d).sort_values('relative_performance',ascending=False)
        fields=['creator','category','caption','metric','metric_basis','relative_performance','engagement_proxy','reel_url']
        return desc,table,top[fields].head(15).round(3)

    def find_topics(cat,demo):
        reels=sc.load_reels(BASE,demo);trends=sc.load_trends(BASE,demo)
        t=sc.topics_with_evidence(reels,trends)
        if cat!='All':t=t[t['Category'].eq(cat)]
        status=('**SYNTHETIC DEMO.** ' if demo else '')
        status+='Each topic is a **curated editorial idea**. Research priority (0–4) is a transparent triage indicator, **not** a prediction or SPI score. Missing supporting evidence means “Research pending.” Google Trends figures are a dated snapshot.'
        return status,t.head(18)

    def score_topic(title,category,angle,*values):
        try:
            factor=dict(zip(sc.SPI_WEIGHTS,values))
            score=sc.score_spi(factor)
            table=pd.DataFrame([{'Factor':sc.SPI_LABELS[k], 'Your assessment /100':factor[k],
                   'Weight':f'{w}%', 'Contribution':round(factor[k]*w/100,1)} for k,w in sc.SPI_WEIGHTS.items()])
            return (f'### Topic evaluation: {title or "Untitled idea"}\n'
                    f'**SPI: {score:.1f}/100** — **editor-rated, not data-calibrated**.  '
                    f'Category: {category}; angle: {angle or "not specified"}.\n\n'
                    'This is a structured comparison of your assumptions. The Topic Finder lists the actual evidence separately. '
                    'A high subjective SPI does not guarantee good performance.'),table
        except Exception as e:return f'Unable to score: {e}',pd.DataFrame()

    def do_ici(video,title,source_type,video_id,reviewer,notes,confirmed,demo,*ratings):
        if not confirmed:return 'Watch the reel (or review it independently) and confirm you assessed all eight factors before scoring.',pd.DataFrame()
        try:
            scores=dict(zip(sc.ICI_WEIGHTS,ratings))
            status,table=sc.review_report(BASE,title,source_type,reviewer,notes,scores,demo=demo,save=False,video_id=video_id)
            status=('**SYNTHETIC DEMO — this review will not be saved.**\n\n' if demo else '**Preview evaluation only — your ratings are not saved.**\n\n')+status
            return status,table
        except Exception as e:return f'Cannot calculate the index: {e}',pd.DataFrame()

    def review_benchmark(demo):
        b=sc.industry_benchmark(BASE,demo)
        factors=pd.DataFrame([{'Factor':sc.ICI_LABELS[k],'Reference /5':v,'Weight':f'{sc.ICI_WEIGHTS[k]}%'} for k,v in b['factors'].items()])
        return f'**Reference: {b["score"]:.1f}/100.** {b["status"]}; {b["count"]} completed competitor videos.',factors

    def store_insights(reel_id,views,reach,shares,saves,follows,notes,demo):
        if demo:return 'Switch off synthetic mode before recording real private Insights.',pd.DataFrame()
        try:
            count=sc.add_insights(BASE,reel_id,views,reach,shares,saves,follows,notes)
            return f'Saved verified-by-you record. Total records: {count}. The application does not extract data from screenshots.',sc.performance_feedback(BASE)
        except Exception as e:return f'Could not save: {e}',pd.DataFrame()

    def see_insights(demo):
        if demo:return 'No real Insights are shown in synthetic mode.',pd.DataFrame()
        data=sc.performance_feedback(BASE)
        return ('Internal Insights are not available in this public demonstration. Share/save/follow rates are only calculated when reach is present; no missing values are invented.' if len(data) else 'No private Insights entered yet.'),data

    def fixed_answer(q,history,demo):
        text=(q or '').lower().strip()
        if not text:return 'Ask about topics, trends, competitors, the quality index, or getting started.'
        if 'trend' in text:
            t=sc.load_trends(BASE,demo)
            if t.empty:return 'There are no trends imported yet. Open **Load Data** and upload the Google Trends CSV.'
            relevant=t[t['category'].isin(sc.CATEGORIES)]
            names='; '.join(relevant['search_term'].head(5).astype(str)) or 'No channel-relevant terms detected yet'
            return f'Loaded {len(t)} frozen trends. First channel-relevant queries: {names}. These were trending at collection, not necessarily now.'
        if any(x in text for x in ['suggest','idea','topic','what to make','next video']):
            t=sc.topics_with_evidence(sc.load_reels(BASE,demo),sc.load_trends(BASE,demo))
            lines=[]
            for _,r in t.head(5).iterrows():
                val=r['Research priority (/4)']
                evidence=f'{int(val)}/4 research priority' if pd.notna(val) else 'research pending'
                lines.append(f'- **{r["Topic"]}** ({r["Category"]}) — {evidence}. Angle: {r["Proposed angle"]}')
            return '**Candidate stories (curated, not AI predictions):**\n\n'+'\n'.join(lines)+'\n\nUse **Topic Finder** for the source signals and full list.'
        if any(x in text for x in ['competitor','view','engagement','performance','market']):
            d=sc.load_reels(BASE,demo)
            if d.empty:return 'No public reels yet. Import your Apify CSV under **Load Data**.'
            tab=sc.market_table(d)
            if tab.empty:return 'Not enough public engagement data to compare.'
            return f'Analysed {len(d)} reels across {d["creator"].nunique()} accounts.\n\n'+tab.head(5).to_markdown(index=False)+'\n\nThis is descriptive evidence, not a causal finding.'
        if any(x in text for x in ['index','ici','benchmark','evaluate','reel','score']):
            bm=sc.industry_benchmark(BASE,demo)
            return f'The eight-factor ICI reference is **{bm["score"]:.1f}/100**: {bm["status"]}. Upload and watch a reel under **Reel Quality Index**, then give eight ratings to see every comparison.'
        if any(x in text for x in ['insight','reach','save','follow']):
            return 'Private VicharDesk Insights are intentionally excluded from the public app.'
        return 'I am a **rule-based guide, not an LLM**. Ask: “Suggest topics”, “Show competitor patterns”, “What trends were imported?”, or “Explain the ICI benchmark”. For full actions, use the tabs.'

    with gr.Blocks(title='StoryScout Lite | Content research and quality index') as app:
        gr.Markdown('# StoryScout Lite · Content Research & Quality Index\nA public microeconomics-based content decision demo for VicharDesk. **No Gemini or AI video inference.**')
        demo=gr.Checkbox(value=(sc.load_reels(BASE,False).empty),label='Use SYNTHETIC sample data for demonstration (never mixed with real research)')
        status=gr.Markdown(value=summary(False))
        demo.change(fn=summary,inputs=demo,outputs=status)
        with gr.Tabs():
            with gr.Tab('1 · Data & Method'):
                gr.Markdown("""### Public research demo
This public application is **read-only**: visitors can analyse the published research and
score their own videos without changing the shared benchmark. It does not connect to Google Drive.

**Two modes:** Public research (if the owner has supplied public Apify / Google Trends CSVs)
and **SYNTHETIC demo** (fictional values, clearly labelled).

The app measures descriptive public counts, uses a curated topic bank, and scores video quality from
**eight human ratings**. It does **not** automatically analyse the video or predict views.

**To update the public research:** the owner uploads sanitized public CSVs into the repository's
`data/` folder and redeploys. Never publish private Instagram Insights or unlicensed video files.
""")
            with gr.Tab('2 · Competitor Market'):
                gr.Markdown('**Demand proxies:** relative public counts and likes/comments. **Supply:** number of comparable reels and creators. All conclusions apply only to the selected sample.')
                competition_btn=gr.Button('Analyse competitor market',variant='primary')
                competition_note=gr.Markdown()
                market_df=gr.Dataframe(label='Category comparisons',interactive=False)
                top_df=gr.Dataframe(label='Top relative performers',interactive=False)
                competition_btn.click(competitors,[demo],[competition_note,market_df,top_df])
                report_btn=gr.Button("Export research summary for presentation")
                report_download=gr.File(label="Download research summary (.md)")
                report_btn.click(report_file,[demo],[report_download])
            with gr.Tab('3 · StoryScout Topic Finder'):
                gr.Markdown('The topic library is editorially prepared for VicharDesk. Search terms and competitor data are matched using explicit keywords—not LLM guesses.')
                cat=gr.Dropdown(['All',*sc.CATEGORIES],value='All',label='Content category')
                topics_btn=gr.Button('Suggest and rank topics',variant='primary')
                topics_note=gr.Markdown()
                topic_table=gr.Dataframe(label='Suggested story ideas and evidence',interactive=False)
                topics_btn.click(find_topics,[cat,demo],[topics_note,topic_table])
                gr.Markdown('### Optional: score a topic using the six-factor Story Potential Index\nThese are your **editorial assessments** (0–100). This does not generate an automatic prediction.')
                title=gr.Textbox(label='Proposed title',value='Why India wants semiconductor factories')
                topic_category=gr.Dropdown(list(sc.CATEGORIES),value='Economics',label='Category')
                angle=gr.Textbox(label='Story angle',value='Explain why chips need a complex supply chain')
                spi_widgets=[]
                with gr.Row():
                    for k in list(sc.SPI_WEIGHTS)[:3]:spi_widgets.append(gr.Slider(0,100,value=50,step=5,label=f'{sc.SPI_LABELS[k]} · {sc.SPI_WEIGHTS[k]}%'))
                with gr.Row():
                    for k in list(sc.SPI_WEIGHTS)[3:]:spi_widgets.append(gr.Slider(0,100,value=50,step=5,label=f'{sc.SPI_LABELS[k]} · {sc.SPI_WEIGHTS[k]}%'))
                spi_btn=gr.Button('Calculate topic SPI')
                spi_out=gr.Markdown()
                spi_table=gr.Dataframe(label='SPI factor breakdown',interactive=False)
                spi_btn.click(score_topic,[title,topic_category,angle,*spi_widgets],[spi_out,spi_table])
            with gr.Tab('4 · Reel Quality Index'):
                gr.Markdown('Upload a draft MP4 for playback, **watch it**, and score the eight factors below. This is a human-assisted review. The tool calculates the full breakdown and compares it with the published reference. Uploaded drafts and ratings are not saved as research records.')
                bm_btn=gr.Button('Show current reference benchmark')
                bm_note=gr.Markdown()
                bm_table=gr.Dataframe(label='ICI reference factor scores',interactive=False)
                bm_btn.click(review_benchmark,[demo],[bm_note,bm_table])
                with gr.Row():
                    video=gr.Video(label='Upload / preview MP4 (optional if you already watched the reel)',sources=['upload'])
                    with gr.Column():
                        reel_title=gr.Textbox(label='Video title',value='New VicharDesk draft')
                        source=gr.Dropdown(['VicharDesk draft','competitor'],value='VicharDesk draft',label='Video type')
                        vid=gr.Textbox(label='Reel ID (use matching Apify ID for competitor reviews)',placeholder='e.g. ABC123')
                        reviewer=gr.Textbox(label='Reviewer',value='Student reviewer')
                        notes=gr.Textbox(label='Observations / source notes',lines=3)
                sliders=[]
                with gr.Row():
                    for k in list(sc.ICI_WEIGHTS)[:4]:sliders.append(gr.Slider(0,5,value=3,step=1,label=f'{sc.ICI_LABELS[k]} ({sc.ICI_WEIGHTS[k]}%)'))
                with gr.Row():
                    for k in list(sc.ICI_WEIGHTS)[4:]:sliders.append(gr.Slider(0,5,value=3,step=1,label=f'{sc.ICI_LABELS[k]} ({sc.ICI_WEIGHTS[k]}%)'))
                check=gr.Checkbox(value=False,label='I have watched/reviewed the reel and deliberately chosen all eight scores.')
                ici_btn=gr.Button('Calculate full ICI report',variant='primary')
                ici_note=gr.Markdown()
                ici_df=gr.Dataframe(label='Complete factor-by-factor index match',interactive=False)
                ici_btn.click(do_ici,[video,reel_title,source,vid,reviewer,notes,check,demo,*sliders],[ici_note,ici_df]).then(summary,[demo],[status])
            with gr.Tab('5 · Performance Feedback'):
                gr.Markdown("""### Private performance evaluation (offline only)
Verified VicharDesk Insights are intentionally **not hosted on this public website**.
The team's Colab version supports entering private reach, saves, shares and follows.
The publicly displayed industry benchmark uses only the published, completed competitor reviews,
or a clearly marked provisional reference when none are available.
""")
            with gr.Tab('6 · Ask StoryScout (rule-based)'):
                gr.Markdown('A simple command-based helper. It is deliberately **not a generative AI chatbot** and responds only to supported questions.')
                gr.ChatInterface(fn=fixed_answer,additional_inputs=[demo],examples=[['Suggest 5 video topics',False],['What are our competitor patterns?',False],['Explain the ICI benchmark',False],['What trends are imported?',False]])
        gr.Markdown('**Research note:** Topic research priorities and index scores guide editorial decisions; they are neither calibrated forecasts nor causal estimates of Instagram performance.')
    return app
