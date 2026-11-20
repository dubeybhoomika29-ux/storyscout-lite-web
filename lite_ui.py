"""StoryScout Lite public Gradio application.

No synthetic mode. Research CSV uploads are SESSION-ONLY to avoid exposing other
visitors' data or incorrectly claiming free Render storage is permanent.
"""
from datetime import datetime, timezone
from pathlib import Path
import os
import tempfile
import zipfile
import uuid

import gradio as gr
import numpy as np
import pandas as pd
import lite_core as sc

BASE = None

REVIEW_COLS = ['video_id','title','source_type','reviewer','review_date',
               *sc.ICI_WEIGHTS,'overall_score','notes']
TREND_COLS = ['search_term','volume_band','started','status','snapshot_date','category','source']


def _clone(research):
    return {k: v.copy(deep=True) for k,v in research.items()}


def _clean_reviews(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=REVIEW_COLS)
    d = df.copy()
    d = d.rename(columns={'video_title':'title', 'rater':'reviewer',
                           'evidence_notes':'notes'})
    d = d.loc[:, ~d.columns.duplicated()]
    if 'video_id' not in d:
        raise ValueError('Review file must contain a video_id column.')
    for c in REVIEW_COLS:
        if c not in d:
            d[c] = np.nan if c in sc.ICI_WEIGHTS else ''
    d['source_type'] = d['source_type'].fillna('').astype(str).str.strip().str.lower()
    for c in sc.ICI_WEIGHTS:
        d[c] = pd.to_numeric(d[c], errors='coerce')
        d.loc[~d[c].between(0,5),c]=np.nan
    d['video_id'] = d['video_id'].fillna('').astype(str).str.strip()
    return d[REVIEW_COLS].loc[d['video_id'].ne('')].reset_index(drop=True)


def _load_initial():
    return {
        'reels':sc.load_reels(BASE,False),
        'trends':sc.load_trends(BASE,False),
        'reviews':_clean_reviews(sc._load_reviews(BASE,False)),
    }


def _benchmark(reviews):
    d = _clean_reviews(reviews)
    if len(d):
        complete = d[d['source_type'].eq('competitor')].copy()
        complete = complete[complete[list(sc.ICI_WEIGHTS)].notna().all(axis=1)]
        per_video = complete.groupby('video_id')[list(sc.ICI_WEIGHTS)].median(numeric_only=True)
    else:
        per_video = pd.DataFrame(columns=list(sc.ICI_WEIGHTS))
    count=len(per_video)
    if count >= 5:
        factors={k:round(float(per_video[k].median()),2) for k in sc.ICI_WEIGHTS}
        label=('Preliminary benchmark from '+str(count)+' reviewed competitor reels'
               +(' — small sample' if count<15 else ''))
        evidence=True
    else:
        factors={k:4.0 for k in sc.ICI_WEIGHTS}
        label=('Provisional editorial target (4/5 per factor), NOT measured industry data. '
               f'Only {count} complete competitor reviews; at least 5 are required for a pilot comparison.')
        evidence=False
    return {'factors':factors,'score':sc.score_index(factors,sc.ICI_WEIGHTS,5),
            'count':count,'label':label,'empirical':evidence}


def _summary(data):
    r=data['reels']; t=data['trends']; b=_benchmark(data['reviews'])
    return (f'**Research loaded:** {len(r)} public reel records · {len(t)} Google Trends records · '
            f'{b["count"]} completed distinct competitor video reviews.  \n'
            f'**ICI comparison:** {b["score"]:.1f}/100 — {b["label"]}  \n'
            '**Method:** Human ratings + transparent calculations; no automatic video interpretation or performance prediction.')


def _preview_reels(d):
    cols=['reel_id','creator','category','caption','metric','metric_basis','likes','comments']
    return d.reindex(columns=cols).head(15)


def _upload_reels(path,data):
    if not path:
        return data,'Please choose an Apify CSV or JSON file.',pd.DataFrame(),_summary(data)
    try:
        incoming=sc.normalize_reels(sc._raw_file(path))
        if incoming.empty:
            raise ValueError('No recognised reel IDs or URLs. Check the file format.')
        updated=_clone(data)
        updated['reels']=pd.concat([data['reels'],incoming],ignore_index=True).drop_duplicates('reel_id',keep='first')
        nmetric=int(updated['reels']['metric'].notna().sum())
        message=(f'**Loaded {len(incoming)} reel rows.** You now have {len(updated["reels"])} distinct reels; '
                 f'{nmetric} contain public views or plays. Data are available to all tabs **in this browser session**. '
                 'Use the Download button to keep a copy; the web server does not save your upload permanently.')
        return updated,message,_preview_reels(updated['reels']),_summary(updated)
    except Exception as e:
        return data,f'**Import error:** {e}',pd.DataFrame(),_summary(data)


def _upload_trends(path, collection_date, data):
    if not path:
        return data,'Please choose a Google Trends CSV.',pd.DataFrame(),_summary(data)
    try:
        # Try canonical research CSVs first; raw Google Trends exports can have
        # multiple header/preamble lines and must use normalize_trends() instead.
        try:
            raw=sc._raw_file(path)
        except (ValueError, pd.errors.ParserError, UnicodeError):
            raw=pd.DataFrame()
        if 'search_term' in raw.columns and 'snapshot_date' in raw.columns:
            incoming=raw.copy()
            for c in TREND_COLS:
                if c not in incoming:
                    incoming[c]=''
            incoming=incoming[TREND_COLS]
            incoming['category']=incoming.apply(
                lambda row: row['category'] if str(row['category']) in sc.CATEGORIES
                else sc.category_for(row['search_term']),axis=1)
        else:
            incoming=sc.normalize_trends(path,collection_date or None)
        if incoming.empty:
            raise ValueError('No recognizable trend rows. Please export CSV from Google Trends Trending Now.')
        updated=_clone(data)
        updated['trends']=pd.concat([data['trends'],incoming],ignore_index=True).drop_duplicates(
            ['search_term','snapshot_date'],keep='last')
        found=int(updated['trends']['category'].isin(sc.CATEGORIES).sum())
        return (updated,
                f'**Loaded {len(incoming)} trend records.** Total: {len(updated["trends"])}; '
                f'{found} have a keyword-matched VicharDesk content category. '
                'These are historical searches, not live trends.',
                updated['trends'].head(15),_summary(updated))
    except Exception as e:
        return data,f'**Trends import error:** {e}',pd.DataFrame(),_summary(data)


def _upload_reviews(path,data):
    if not path:
        return data,'Please choose a CSV of completed ICI reviews.',pd.DataFrame(),_summary(data)
    try:
        incoming=_clean_reviews(sc._raw_file(path))
        if incoming.empty:raise ValueError('No video_id values detected.')
        updated=_clone(data)
        updated['reviews']=pd.concat([data['reviews'],incoming],ignore_index=True).drop_duplicates(
            ['video_id','reviewer','review_date'],keep='last')
        b=_benchmark(updated['reviews'])
        return (updated,
            f'Loaded {len(incoming)} review rows; **{b["count"]} distinct completed competitor video reviews** '
            f'are usable for the ICI comparison. Incomplete placeholders do not count. {b["label"]}',
            updated['reviews'].head(15),_summary(updated))
    except Exception as e:
        return data,f'**Review import error:** {e}',pd.DataFrame(),_summary(data)


def _competitors(data):
    d=data['reels']
    if d.empty:
        return ('No public reel records yet. Open **1 · Upload Research** and upload your Apify export.',
                pd.DataFrame(),pd.DataFrame())
    x=sc.competitor_metrics(d)
    metric_counts=d['metric_basis'].fillna('unavailable').value_counts().to_dict()
    table=sc.market_table(d)
    top=x.sort_values('relative_performance',ascending=False).reindex(columns=[
        'creator','category','caption','metric','metric_basis','relative_performance','engagement_proxy','reel_url']).head(20)
    description=(f'**{len(d)} reels from {d["creator"].nunique()} creators.** Count types: {metric_counts}. '
                 'Relative performance = reel public views/plays ÷ that creator’s median of the *same metric type* '
                 '(requires at least two comparable reels). Likes and comments / public count is only a proxy; '
                 'it is not engagement per reach. Categories are keyword-assigned where not manually labelled.')
    return description,table,top.round(3)


def _topic_finder(category,data):
    t=sc.topics_with_evidence(data['reels'],data['trends'])
    if category!='All':t=t[t['Category']==category]
    note=('These are **editorially curated video ideas**. Research priority /5 is an evidence triage score, '
          '**not a predicted view count or a Story Potential Index**. If evidence is missing, a topic is '
          'marked research pending. Uploaded trend records are dated, not real-time.')
    return note,t.head(18)


def _score_spi(title,category,angle,*values):
    try:
        s=dict(zip(sc.SPI_WEIGHTS,values)); value=sc.score_spi(s)
        table=pd.DataFrame([{'Factor':sc.SPI_LABELS[k],'Your rating /100':s[k],
                             'Weight':f'{w}%','Weighted contribution':round(s[k]*w/100,1)}
                            for k,w in sc.SPI_WEIGHTS.items()])
        return (f'### {title or "Untitled topic"}: {value:.1f}/100\n'
                f'Category: **{category}**. Proposed angle: {angle or "Not specified"}.  \n'
                '**This is a structured human assessment; it is not a forecast of viral success.**'),table
    except Exception as e:
        return f'Rating issue: {e}',pd.DataFrame()


def _benchmark_display(data):
    b=_benchmark(data['reviews'])
    table=pd.DataFrame([{'Factor':sc.ICI_LABELS[k], 'Reference /5':v,
                         'Weight':f'{sc.ICI_WEIGHTS[k]}%'} for k,v in b['factors'].items()])
    return f'**ICI reference: {b["score"]:.1f}/100.** {b["label"]}',table


def _ici(video,title,source_type,video_id,reviewer,notes,confirmed,data,*values):
    if not confirmed:
        return 'Please review the actual video and confirm all eight factor ratings before calculating.',pd.DataFrame()
    try:
        ratings=dict(zip(sc.ICI_WEIGHTS,values)); total=sc.score_index(ratings,sc.ICI_WEIGHTS,5)
        b=_benchmark(data['reviews']); below=[]; rows=[]
        for k,w in sc.ICI_WEIGHTS.items():
            actual=float(ratings[k]); ref=b['factors'][k]
            if actual<ref:below.append(k)
            rows.append({'Factor':sc.ICI_LABELS[k],'Weight':f'{w}%',
                         'Your score /5':actual,'Reference /5':ref,
                         'Difference':round(actual-ref,2),
                         'Weighted points /100':round(actual*w/5,1),
                         'Meets reference?':'Yes' if actual>=ref else 'No'})
        suggestions='\n'.join(f'- {sc.ICI_TIPS[k]}' for k in below[:4]) if below else 'All factors meet or exceed the current reference.'
        desc=(f'### {title or "Draft reel"}: {total:.1f}/100  ·  Reference: {b["score"]:.1f}/100\n\n'
              f'**Factor match:** {8-len(below)}/8 · **Weighted difference:** {total-b["score"]:+.1f} points.  \n'
              f'**Benchmark:** {b["label"]}\n\n'
              f'**Changes to consider**\n{suggestions}\n\n'
              '*Ratings are supplied by a human reviewer. Uploading a video alone does not analyse its content. '
              'Your draft and this evaluation are not saved to a public database.*')
        return desc,pd.DataFrame(rows)
    except Exception as e:
        return f'ICI scoring problem: {e}',pd.DataFrame()


def _save_review(video_id,title,source_type,reviewer,notes,confirmed,data,*values):
    if not confirmed:
        return data,'Review the video and confirm the eight ratings first.',*_benchmark_display(data),_summary(data)
    if source_type!='competitor':
        return data,'Only reviewed **competitor** videos belong in the competitor benchmark. Your own draft is not added.',*_benchmark_display(data),_summary(data)
    try:
        rating=dict(zip(sc.ICI_WEIGHTS,values)); total=sc.score_index(rating,sc.ICI_WEIGHTS,5)
        row={'video_id':video_id.strip() or f'REVIEW_{uuid.uuid4().hex[:12]}',
             'title':title or 'Untitled competitor reel', 'source_type':'competitor',
             'reviewer':reviewer or 'Visitor', 'review_date':datetime.now(timezone.utc).date().isoformat(),
             'overall_score':total,'notes':notes or '',**rating}
        updated=_clone(data)
        updated['reviews']=pd.concat([data['reviews'],pd.DataFrame([row])],ignore_index=True)
        updated['reviews']=_clean_reviews(updated['reviews']).drop_duplicates(
            ['video_id','reviewer','review_date'],keep='last')
        b=_benchmark(updated['reviews'])
        return (updated,
                f'**Added completed competitor review to this browser session.** '
                f'{b["count"]} distinct competitor reels now rated. '
                'Download the research CSV bundle to keep this review.',
                *_benchmark_display(updated),_summary(updated))
    except Exception as e:
        return data,f'Could not add review: {e}',*_benchmark_display(data),_summary(data)


def _rule_answer(question,history,data):
    q=(question or '').strip().lower()
    if not q:return 'Ask about competitor patterns, topic ideas, trends or the quality index.'
    if any(w in q for w in ['trend','search']):
        t=data['trends']
        if t.empty:return 'No trends have been loaded. Open Upload Research and choose your Google Trends CSV.'
        first=t[t['category'].isin(sc.CATEGORIES)]
        return f'The dataset contains {len(t)} dated trends. Relevant examples: '+(', '.join(first['search_term'].astype(str).head(6)) or 'No keyword matches')+'. They may not be trending today.'
    if any(w in q for w in ['suggest','topic','idea','make next','create next']):
        tab=sc.topics_with_evidence(data['reels'],data['trends'])
        texts=[]
        for _,r in tab.head(5).iterrows():
            value=r['Research priority (/5)']
            signal=f'{int(value)}/5' if pd.notna(value) else 'research pending'
            texts.append(f'- **{r["Topic"]}** ({r["Category"]}) — {signal}; angle: {r["Proposed angle"]}')
        return 'Curated topic ideas (not forecasts):\n\n'+'\n'.join(texts)
    if any(w in q for w in ['compet','view','market','engagement','perform']):
        d=data['reels']
        if d.empty:return 'No competitor reels yet. Upload an Apify CSV or JSON to start.'
        return f'The dataset includes {len(d)} reels across {d["creator"].nunique()} accounts.\n\n'+sc.market_table(d).head(6).to_markdown(index=False)+'\n\nThese are descriptive indicators.'
    if any(w in q for w in ['ici','index','benchmark','rate','quality']):
        b=_benchmark(data['reviews'])
        return f'The ICI reference is {b["score"]:.1f}/100. {b["label"]} Use Reel Quality Index for the complete eight-factor breakdown.'
    return 'I am a rule-based guide, not an LLM. Try “Suggest topics”, “What trends were uploaded?”, “Analyse competitors” or “Explain ICI benchmark”.'


def _export_bundle(data):
    target=Path(tempfile.mkdtemp(prefix='storyscout_session_'))
    zipname=target/'StoryScout_Research_Export.zip'
    with zipfile.ZipFile(zipname,'w',zipfile.ZIP_DEFLATED) as z:
        for key,filename in [('reels','lite_competitor_reels.csv'),('trends','lite_trends.csv'),
                             ('reviews','lite_ici_reviews.csv')]:
            csv=target/filename
            data[key].to_csv(csv,index=False)
            z.write(csv,arcname=f'data/{filename}')
        z.writestr('README.txt',
          'StoryScout Lite research export. The data are provided by the session user and may include private information.\n'
          'Review carefully before publishing CSVs to GitHub.\n'
          'For permanent public research, upload sanitized CSV files to repository data/ and commit.\n')
    return str(zipname)


def _export_report(data):
    reels=data['reels']; trends=data['trends']; bm=_benchmark(data['reviews'])
    parts=[
      '# StoryScout Lite — Research Summary',
      'Generated on '+datetime.now(timezone.utc).date().isoformat(),
      '', '## Data coverage',
      f'- Reel records: {len(reels)}', f'- Creators: {reels["creator"].nunique() if len(reels) else 0}',
      f'- Historical trend records: {len(trends)}',f'- Completed competitor ICI reviews: {bm["count"]}',
      '', '## Competitive content supply and engagement (descriptive)']
    if len(reels):parts.append(sc.market_table(reels).to_markdown(index=False))
    else:parts.append('No public reels loaded.')
    parts+=['','## Candidate topics (curated)',
             sc.topics_with_evidence(reels,trends).head(12).reindex(columns=[
              'Topic','Category','Matched trends','Matching competitor reels','Evidence status']).to_markdown(index=False),
             '', '## Industry Content Index',
             f'Reference: {bm["score"]:.1f}/100. {bm["label"]}',
             '', '## Interpretation',
             'Views and searches are imperfect proxies for consumer interest; the sample is not representative.',
             'Topic research scores and human ICI ratings are not forecasts, causal evidence, or automatic AI analysis.',
             'Stored trends are snapshots and must not be presented as current when outdated.'
           ]
    path=Path(tempfile.mkdtemp(prefix='storyscout_report_'))/'StoryScout_Research_Summary.md'
    path.write_text('\n'.join(parts),encoding='utf-8')
    return str(path)


def init_app(base, theme=None, css=None):
    global BASE
    BASE=sc.choose_paths(base)
    initial=_load_initial()
    # Gradio 5 accepts theme and CSS in Blocks; Gradio 6 moves them to launch().
    blocks_kwargs = {'title': 'StoryScout Lite | VicharDesk Content Intelligence'}
    if int(gr.__version__.split('.')[0]) < 6:
        blocks_kwargs.update(theme=theme, css=css)
    with gr.Blocks(**blocks_kwargs) as app:
        research=gr.State(value=_load_initial)
        gr.HTML("""
        <section class="ss-hero" aria-label="StoryScout introduction">
            <div class="ss-hero-main">
                <div class="ss-eyebrow"><span class="ss-dot"></span> VICHARDESK / CONTENT INTELLIGENCE</div>
                <h1>StoryScout <span>Lite.</span></h1>
                <p class="ss-hero-summary">Find stronger stories. Understand your competition. Check every reel before publishing.</p>
                <div class="ss-feature-pills">
                    <span>01 &nbsp; Research</span><span>02 &nbsp; Discover</span><span>03 &nbsp; Evaluate</span>
                </div>
            </div>
            <div class="ss-hero-mark" aria-hidden="true">S<span>↗</span></div>
        </section>
        """, elem_id='ss-hero')
        status=gr.Markdown(value=_summary(initial),elem_id='ss-research-status',elem_classes=['ss-status-card'])
        with gr.Tabs(elem_id='ss-tabs'):
            with gr.Tab('1 · Upload Research'):
                gr.Markdown('### Upload your research\n'
                    'Choose files here — they will work in **all tabs for this session**. '
                    'Uploads are not shared with other visitors and do not permanently update GitHub. '
                    'If you want public research available on every visit, see **How to publish datasets** below.')
                with gr.Row():
                    with gr.Column():
                        apify=gr.File(label='Upload Apify reels (CSV or JSON)',file_types=['.csv','.json'],type='filepath')
                        apify_button=gr.Button('Import public reels',variant='primary',elem_classes=['ss-primary-action'])
                    with gr.Column():
                        trendfile=gr.File(label='Upload Google Trends export (CSV)',file_types=['.csv'],type='filepath')
                        trenddate=gr.Textbox(label='Snapshot date (YYYY-MM-DD; leave blank for today)',value='')
                        trends_button=gr.Button('Import Google Trends',variant='primary',elem_classes=['ss-primary-action'])
                import_msg=gr.Markdown()
                preview=gr.Dataframe(label='Latest imported data preview',interactive=False)
                apify_button.click(_upload_reels,[apify,research],[research,import_msg,preview,status])
                trends_button.click(_upload_trends,[trendfile,trenddate,research],[research,import_msg,preview,status])
                gr.Markdown('### Add benchmark reviews (optional)\n'
                    'If you have a CSV with `video_id`, `source_type=competitor`, and eight factor columns '
                    '(`hook`, `narrative`, `clarity`, `visuals`, `pacing`, `relevance`, `shareability`, `brand_cta`), '
                    'import it here. Rows with missing ratings are ignored by the benchmark.')
                with gr.Row():
                    reviewfile=gr.File(label='ICI reviews CSV',file_types=['.csv'],type='filepath')
                    reviewbutton=gr.Button('Import completed ICI reviews')
                reviewbutton.click(_upload_reviews,[reviewfile,research],[research,import_msg,preview,status])
                gr.Markdown('### Export your research\n'
                    'This ZIP contains the *currently loaded* research tables so you can save them. '
                    'Remove private data before putting them in a public GitHub repository.')
                export_btn=gr.Button('Download loaded research CSVs')
                exported=gr.File(label='Research data ZIP')
                export_btn.click(_export_bundle,[research],[exported])
                gr.Markdown('**How to publish datasets permanently:** Download the ZIP, extract the three CSVs, '
                            'upload the cleaned files to your GitHub repository under `data/`, and commit. '
                            'Render will redeploy automatically. Your website link stays the same.')
            with gr.Tab('2 · Competitor Market'):
                gr.Markdown('### Competitor overview\nExplore observed views, plays and engagement. Relative performance is normalised within each creator, so large accounts do not automatically dominate.',elem_classes=['ss-intro'])
                cb=gr.Button('Analyse competitors',variant='primary',elem_classes=['ss-primary-action'])
                ct=gr.Markdown(); market=gr.Dataframe(label='Category summary',interactive=False,elem_classes=['ss-data-table'])
                top=gr.Dataframe(label='Relative performance by reel',interactive=False,elem_classes=['ss-data-table'])
                cb.click(_competitors,[research],[ct,market,top])
                report_btn=gr.Button('Export presentation research summary')
                report_download=gr.File(label='Download report (.md)')
                report_btn.click(_export_report,[research],[report_download])
            with gr.Tab('3 · StoryScout Topic Finder'):
                gr.Markdown('### Find your next story\nDiscover ideas suited to VicharDesk, with supporting signals from your uploaded research. Suggestions are curated, not guaranteed to go viral.',elem_classes=['ss-intro'])
                category=gr.Dropdown(['All',*sc.CATEGORIES],value='All',label='Category')
                topic_btn=gr.Button('Suggest topics from loaded research',variant='primary',elem_classes=['ss-primary-action'])
                tn=gr.Markdown(); tt=gr.Dataframe(label='Suggested topics and supporting evidence',interactive=False,elem_classes=['ss-data-table'])
                topic_btn.click(_topic_finder,[category,research],[tn,tt])
                gr.Markdown('### Optional — Score a proposed topic (SPI)')
                title=gr.Textbox(label='Proposed title',placeholder='e.g. Why gold prices change in India')
                tc=gr.Dropdown(list(sc.CATEGORIES),value='Economics',label='Category')
                angle=gr.Textbox(label='Unique angle',placeholder='What will make this explainer different?')
                spi_sliders=[]
                with gr.Row():
                    for k in list(sc.SPI_WEIGHTS)[:3]:
                        spi_sliders.append(gr.Slider(0,100,step=5,value=50,label=f'{sc.SPI_LABELS[k]} ({sc.SPI_WEIGHTS[k]}%)'))
                with gr.Row():
                    for k in list(sc.SPI_WEIGHTS)[3:]:
                        spi_sliders.append(gr.Slider(0,100,step=5,value=50,label=f'{sc.SPI_LABELS[k]} ({sc.SPI_WEIGHTS[k]}%)'))
                spi_btn=gr.Button('Calculate Story Potential Index',variant='primary',elem_classes=['ss-primary-action'])
                spi_text=gr.Markdown(); spi_table=gr.Dataframe(label='SPI factor breakdown',interactive=False)
                spi_btn.click(_score_spi,[title,tc,angle,*spi_sliders],[spi_text,spi_table])
            with gr.Tab('4 · Reel Quality Index'):
                gr.Markdown('### Check your reel before publishing\n'
                    'Watch the actual reel and choose the eight factor ratings. '
                    '**An MP4 upload is for playback only**; there is no automatic AI review.')
                bench_btn=gr.Button('Show benchmark')
                bench_text=gr.Markdown(value=_benchmark_display(initial)[0])
                bench_table=gr.Dataframe(label='Benchmark for each factor',interactive=False,
                                         value=_benchmark_display(initial)[1])
                bench_btn.click(_benchmark_display,[research],[bench_text,bench_table])
                with gr.Row():
                    vidfile=gr.Video(label='Upload / play reel MP4',sources=['upload'])
                    with gr.Column():
                        reel_title=gr.Textbox(label='Video title',placeholder='New VicharDesk draft')
                        source_type=gr.Dropdown(['VicharDesk draft','competitor'],value='VicharDesk draft',label='Video type')
                        video_id=gr.Textbox(label='Reel ID (helps group ratings of the same competitor reel)')
                        reviewer=gr.Textbox(label='Reviewer',value='Student reviewer')
                        note=gr.Textbox(label='Supporting observations',lines=3)
                ici_sliders=[]
                with gr.Row():
                    for k in list(sc.ICI_WEIGHTS)[:4]:
                        ici_sliders.append(gr.Slider(0,5,step=1,value=3,label=f'{sc.ICI_LABELS[k]} ({sc.ICI_WEIGHTS[k]}%)'))
                with gr.Row():
                    for k in list(sc.ICI_WEIGHTS)[4:]:
                        ici_sliders.append(gr.Slider(0,5,step=1,value=3,label=f'{sc.ICI_LABELS[k]} ({sc.ICI_WEIGHTS[k]}%)'))
                confirmed=gr.Checkbox(value=False,label='I watched the reel (or independently reviewed it) and consciously rated all eight factors.')
                ici_btn=gr.Button('Calculate complete ICI comparison',variant='primary',elem_classes=['ss-primary-action'])
                ici_desc=gr.Markdown(); ici_table=gr.Dataframe(label='Factor-by-factor index match',interactive=False,elem_classes=['ss-data-table'])
                ici_btn.click(_ici,[vidfile,reel_title,source_type,video_id,reviewer,note,confirmed,research,*ici_sliders],
                              [ici_desc,ici_table])
                gr.Markdown('### Build a competitor benchmark\n'
                    'If this was a competitor reel, you can add the reviewed scores to your **session** benchmark. '
                    'At least 5 distinct complete competitor reviews are required before the app uses a pilot industry comparison.')
                save_btn=gr.Button('Add reviewed competitor reel to session benchmark')
                save_note=gr.Markdown()
                save_btn.click(_save_review,[video_id,reel_title,source_type,reviewer,note,confirmed,research,*ici_sliders],
                               [research,save_note,bench_text,bench_table,status])
            with gr.Tab('5 · Ask StoryScout'):
                gr.Markdown('### Ask StoryScout\nA lightweight research assistant for common questions about your imported data. It uses fixed rules, not generative AI.',elem_classes=['ss-intro'])
                gr.ChatInterface(fn=_rule_answer,additional_inputs=[research])
        gr.Markdown('**Research note:** StoryScout supports evidence-informed decisions. It does not predict views, establish causality, or automatically analyse uploaded video content.',elem_id='ss-footer-note')
    return app
