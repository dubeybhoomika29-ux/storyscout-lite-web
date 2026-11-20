"""StoryScout Lite — offline, deterministic, auditable microeconomic content prototype.
No Gemini, API key, or network access needed after Python package installation.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, re, math
import numpy as np
import pandas as pd

CATEGORIES = ('Economics','History','Geopolitics','Current affairs','UPSC')
ICI_WEIGHTS = {'hook':20,'narrative':20,'clarity':15,'visuals':15,'pacing':10,'relevance':10,'shareability':5,'brand_cta':5}
ICI_LABELS = {'hook':'Hook strength','narrative':'Narrative structure','clarity':'Clarity & sourcing','visuals':'Visual storytelling','pacing':'Pacing','relevance':'Audience relevance','shareability':'Shareability','brand_cta':'Brand fit & CTA'}
ICI_TIPS = {
 'hook':'Start with a specific question, surprise or tension in the first few seconds.',
 'narrative':'Add a clear beginning, problem, development and satisfying conclusion.',
 'clarity':'Explain unfamiliar terms simply and verify factual claims against credible sources.',
 'visuals':'Use visuals that explain relationships, geography, change or scale—not decoration alone.',
 'pacing':'Remove repetitive lines and give complex explanations enough time to register.',
 'relevance':'Explain early why this topic matters to your intended Indian audience.',
 'shareability':'Add a memorable, useful takeaway viewers may want to share.',
 'brand_cta':'Connect the explanation to the channel identity and use a natural call to action.'
}
SPI_WEIGHTS = {'audience_demand':25,'india_relevance':20,'storytelling_potential':20,'content_gap':15,'timeliness':10,'brand_alignment':10}
SPI_LABELS = {'audience_demand':'Audience demand','india_relevance':'India relevance','storytelling_potential':'Storytelling potential','content_gap':'Underserved angle','timeliness':'Timeliness','brand_alignment':'Channel fit'}

# Deliberately a curated library, not machine-generated 'viral trends'.
TOPIC_BANK = [
('The real economics of IPL teams','Economics','ipl,cricket,franchise,auction','Why a cricket franchise can be valuable even when winning is uncertain','Can a cricket team make money even when it loses?',8),
('Why gold prices change in India','Economics','gold,gold rate,bullion,precious metal','Trace global prices, rupee movement and household demand','Why did your jewellery suddenly become more expensive?',6),
('Why India wants semiconductor factories','Economics','semiconductor,chip,chipmaking,microchip','Explain the full supply chain beyond a factory announcement','Why is building a chip factory only the beginning?',10),
('Why countries borrow money','Economics','debt,government borrowing,sovereign bond,public finance','Compare public borrowing with the infrastructure it finances','Why would a country borrow money if it can collect taxes?',6),
('Why the rupee moves against the dollar','Economics','rupee,dollar,exchange rate,forex','Use imports and demand for foreign currency to explain movements','Who decides what one rupee is worth?',6),
('The economics of food inflation','Economics','food inflation,vegetable prices,tomato,onion,food price','Follow a crop shock from farm to retail price','How can a shortage in one crop affect an entire family budget?',7),
('Why oil prices affect ordinary households','Economics','crude oil,oil price,petrol,fuel,energy import','Connect imported energy with transport and consumer prices','Why can oil prices change the price of almost everything?',7),
('How Bangladesh trade affects Northeast India','Geopolitics','bangladesh,northeast,india-bangladesh,border trade','Explain the role of trade routes, ports and distance','Why can a border change the cost of delivering goods?',9),
('Why shipping chokepoints matter','Geopolitics','red sea,suez,strait,shipping,trade route','Trace a shipping interruption into product costs','What happens when one narrow sea route is blocked?',9),
('India and China: the supply chain link','Geopolitics','china,india china,imports,trade deficit,supply chain','Show how trade dependence interacts with geopolitical tension','Can two rival countries also depend on each other?',9),
('How the Indian rupee changed over time','History','rupee,currency,coinage,monetary history','Explain the historical shifts behind everyday money','Who decided what money would look like in India?',8),
('How the Mughal revenue system worked','History','mughal,land revenue,akbar,zabt,mansabdari','Use maps and farms to explain a complex administration','How did a vast empire collect revenue?',10),
('Why historical trade routes shaped cities','History','silk road,trade route,port,ancient trade','Explain how trade and transport shaped settlement','Why did some cities become wealthy while others faded?',8),
('What a budget deficit really means','UPSC','budget,fiscal deficit,government spending,tax revenue','Explain revenue, spending and financing through a simple example','If the government spends more than it earns, what happens next?',6),
('What the demographic dividend means','UPSC','population,youth,demographic dividend,employment','Connect working-age population with jobs and productivity','Can having more young people make a country richer?',7),
('Why elections change economic expectations','Current affairs','election,policy,market,manifesto,economic policy','Explain how expectations alter consumer and investor choices','Why do markets react before a policy even changes?',7),
('How AI changes jobs and skills','Current affairs','ai jobs,automation,layoffs,employment,artificial intelligence','Compare labour substitution with creation of new tasks','Does automation always mean fewer jobs?',8),
('Why trade tariffs change prices','Current affairs','tariff,trade war,import duty,customs,trade restrictions','Show who pays when imported products face duties','Who actually pays for a tariff?',7),
]

def topic_bank():
    return pd.DataFrame(TOPIC_BANK,columns=['title','category','keywords','angle','hook','estimated_hours'])

def _clean(s):
    return str(s).strip() if s is not None and not (isinstance(s,float) and pd.isna(s)) else ''

def _number(x):
    if x is None or (isinstance(x,float) and pd.isna(x)):return np.nan
    try:
        s=str(x).replace(',','').strip()
        if not s or s.lower() in ('none','nan','-','n/a'):return np.nan
        v=float(s)
        return v if v>=0 else np.nan
    except (ValueError,TypeError):return np.nan

def _select(row,names):
    for n in names:
        if n in row:
            val=row[n]
            if isinstance(val,(dict,list)): return val
            if _clean(val):return val
    return None

def _raw_file(path):
    path=Path(path)
    if path.suffix.lower()=='.json':
        data=json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data,dict):data=data.get('items',data.get('data',[data]))
        return pd.json_normalize(data)
    for enc in ('utf-8-sig','utf-8','cp1252'):
        try:return pd.read_csv(path,encoding=enc,low_memory=False)
        except UnicodeDecodeError:continue
    return pd.read_csv(path,low_memory=False)

def category_for(text):
    text=_clean(text).lower()
    if not text:return 'Unclassified'
    votes={c:0 for c in CATEGORIES}
    # Specific expressions avoid mislabelling everything that says "India".
    rules={
      'Economics':['inflation','economy','economics','gdp','rupee','dollar','budget','interest rate','stock market','semiconductor','gold price','gold rate','fuel price','crude oil','job market','tax','trade deficit','unemployment','ipl auction'],
      'History':['history','historical','mughal','empire','ancient','medieval','dynasty','civilization','colonial','independence movement','ashoka'],
      'Geopolitics':['geopolitics','border','diplomacy','china','bangladesh','pakistan','foreign policy','united nations','war','red sea','suez'],
      'Current affairs':['breaking news','election','today','latest news','policy announcement','layoffs','tariff','ai jobs','government decision'],
      'UPSC':['upsc','civil services','constitution','parliament','polity','prelims','mains','demographic dividend']}
    for cat,terms in rules.items():votes[cat]=sum(int(term in text) for term in terms)
    top=max(votes.values())
    return next(c for c in CATEGORIES if votes[c]==top) if top else 'Unclassified'

REEL_COLS=['reel_id','creator','reel_url','published_at','caption','transcript','topic','category','story_angle','duration_s','views','plays','likes','comments','metric','metric_basis','source']

def normalize_reels(df):
    out=[]
    for j,row in df.iterrows():
        z=row.to_dict(); url=_clean(_select(z,['reel_url','url','reelUrl','inputUrl','shortCodeUrl']))
        rid=_clean(_select(z,['reel_id','id','reelId','shortCode','shortcode']))
        if not rid and url:rid=url.rstrip('/').split('/')[-1]
        creator=_clean(_select(z,['creator','ownerUsername','owner.username','username','ownerUsername.0']))
        if not creator and isinstance(z.get('owner'),dict):creator=_clean(z['owner'].get('username'))
        if not rid and not url:continue
        plays=_number(_select(z,['plays','videoPlayCount','playCount']))
        views=_number(_select(z,['views','videoViewCount','viewCount']))
        metric=plays if pd.notna(plays) else views
        basis='public plays' if pd.notna(plays) else ('public views' if pd.notna(views) else 'unavailable')
        caption=_clean(_select(z,['caption','text','description']))
        # In older converted files, category/topic/angle are often blank. Preserve explicit labels.
        existing_cat=_clean(z.get('category'))
        cat=existing_cat if existing_cat and existing_cat.lower()!='nan' else category_for(caption)
        out.append({'reel_id':rid,'creator':creator or 'Unknown creator','reel_url':url,'published_at':_clean(_select(z,['published_at','timestamp','takenAt','publishedAt'])),
         'caption':caption,'transcript':_clean(_select(z,['transcript','videoTranscript','transcriptText'])),
         'topic':_clean(z.get('topic')),'category':cat,'story_angle':_clean(z.get('story_angle')),
         'duration_s':_number(_select(z,['duration_s','videoDuration','duration','durationSeconds'])),
         'views':views,'plays':plays,'likes':_number(_select(z,['likes','likesCount','likeCount'])),
         'comments':_number(_select(z,['comments','commentsCount','commentCount'])),
         'metric':metric,'metric_basis':basis,'source':'APIFY_PUBLIC'})
    return pd.DataFrame(out,columns=REEL_COLS).drop_duplicates(['reel_id'],keep='last')

def _standard_trends(raw, snapshot_date=None):
    terms=_fields(raw,['search_term','trends','trending search','search trend','trend','query','term','title'])
    vols=_fields(raw,['volume_band','search volume','searchvolume','approx. searches','traffic','volume'])
    started=_fields(raw,['started','started at','startedat','trend started'])
    status=_fields(raw,['ended','ended at','endedat','status'])
    if terms is None:raise ValueError('Could not identify a trend term column. Expected "Trends" or "Trending search". Columns: '+str(list(raw.columns)[:12]))
    out=pd.DataFrame({'search_term':raw[terms].map(_clean)})
    out['volume_band']=raw[vols].map(_clean) if vols else ''
    out['started']=raw[started].map(_clean) if started else ''
    out['status']=raw[status].map(_clean) if status else ''
    out['snapshot_date']=str(snapshot_date or datetime.now(timezone.utc).date())
    out['category']=out['search_term'].map(category_for)
    out['source']='GOOGLE_TRENDS_INDIA_EXPORT'
    return out.loc[out['search_term'].ne('')].drop_duplicates(['search_term','snapshot_date']).reset_index(drop=True)

def _fields(df,names):
    names={re.sub(r'[^a-z0-9]','',n.lower()) for n in names}
    for col in df.columns:
        if re.sub(r'[^a-z0-9]','',str(col).lower()) in names:return col
    return None

def normalize_trends(path,snapshot_date=None):
    path=Path(path)
    if path.suffix.lower()=='.json':return _standard_trends(_raw_file(path),snapshot_date)
    # Raw Google Trends files can begin with a preamble above the header.
    last_error=None
    for skip in range(7):
        try:
            raw=pd.read_csv(path,skiprows=skip,encoding='utf-8-sig',engine='python')
            if _fields(raw,['search_term','trends','trending search','search trend','trend','query','term','title']):
                return _standard_trends(raw,snapshot_date)
        except Exception as e:last_error=e
    raise ValueError('No recognisable Google Trends header in first seven rows. '+str(last_error or ''))

def choose_paths(base):
    base=Path(base); (base/'data').mkdir(parents=True,exist_ok=True); (base/'lite_demo').mkdir(parents=True,exist_ok=True)
    return base

def _read(path,cols):
    if not Path(path).exists():return pd.DataFrame(columns=cols)
    try:return pd.read_csv(path)
    except pd.errors.EmptyDataError:return pd.DataFrame(columns=cols)

def _existing_reels(base):
    original=Path(base)/'data'/'competitor_reels.csv'
    lite=Path(base)/'data'/'lite_competitor_reels.csv'
    existing=_read(lite,REEL_COLS)
    if not original.exists():return existing
    older=normalize_reels(_raw_file(original))
    return pd.concat([older,existing],ignore_index=True).drop_duplicates(['reel_id'],keep='last')

def load_reels(base,demo=False):
    if demo:return _read(Path(base)/'lite_demo'/'lite_competitor_reels.csv',REEL_COLS)
    return _existing_reels(base)

def load_trends(base,demo=False):
    if demo:return _read(Path(base)/'lite_demo'/'lite_trends.csv',['search_term','volume_band','started','status','snapshot_date','category','source'])
    lite=Path(base)/'data'/'lite_trends.csv'
    if lite.exists():return _read(lite,['search_term','volume_band','started','status','snapshot_date','category','source'])
    older=Path(base)/'data'/'trends_snapshot.csv'
    if older.exists():
        t=_read(older,[])
        if 'search_term' in t and len(t):
            t=t.copy()
            if 'volume_band' not in t:t['volume_band']=''
            if 'category' not in t:t['category']=t['search_term'].map(category_for)
            if 'snapshot_date' not in t:t['snapshot_date']='Not recorded'
            return t
    return pd.DataFrame(columns=['search_term','volume_band','started','status','snapshot_date','category','source'])

def import_reels_file(base,path):
    incoming=normalize_reels(_raw_file(path))
    if incoming.empty:raise ValueError('No reel records recognised. Check CSV columns and reel IDs.')
    dst=Path(base)/'data'/'lite_competitor_reels.csv'
    before=load_reels(base,False)
    # Preserve manual classifications in existing rows; never overwrite the old CSV.
    latest=pd.concat([before,incoming],ignore_index=True).drop_duplicates(['reel_id'],keep='first')
    latest.to_csv(dst,index=False)
    return {'imported_rows':len(incoming),'unique_rows':len(latest),'valid_metric_rows':int(latest['metric'].notna().sum())}

def import_trends_file(base,path,snapshot_date=None):
    t=normalize_trends(path,snapshot_date)
    if t.empty:raise ValueError('No trends were found in this export.')
    dst=Path(base)/'data'/'lite_trends.csv'
    old=load_trends(base,False)
    combined=pd.concat([old,t],ignore_index=True).drop_duplicates(['search_term','snapshot_date'],keep='last')
    combined.to_csv(dst,index=False)
    return {'new_rows':len(t),'total_rows':len(combined),'relevant_by_keyword':int(combined['category'].isin(CATEGORIES).sum())}

def competitor_metrics(df):
    if df.empty:return df.copy()
    d=df.copy()
    for col in ['metric','likes','comments']:
        d[col]=pd.to_numeric(d[col],errors='coerce').mask(lambda x:x<0)
    grp=['creator','metric_basis']
    d['creator_n']=d.groupby(grp)['metric'].transform('count')
    d['creator_median']=d.groupby(grp)['metric'].transform('median')
    d['relative_performance']=(d['metric']/d['creator_median'].replace(0,np.nan)).where(d['creator_n']>=2)
    d['engagement_proxy']=(d['likes']+d['comments'])/d['metric'].replace(0,np.nan)
    d['engagement_proxy']=d['engagement_proxy'].where(d['likes'].notna() & d['comments'].notna())
    return d

def market_table(reels):
    if reels.empty:return pd.DataFrame(columns=['Category','Reels','Creators','Median public count','Median vs creator','Median likes+comments / count'])
    d=competitor_metrics(reels)
    a=d.groupby('category',dropna=False).agg(
        Reels=('reel_id','count'),Creators=('creator','nunique'),
        **{'Median public count':('metric','median'),'Median vs creator':('relative_performance','median'),
           'Median likes+comments / count':('engagement_proxy','median')}).reset_index().rename(columns={'category':'Category'})
    return a.sort_values('Reels',ascending=False).round(3)

def _hits(text,keywords):
    s=' '+re.sub(r'[^a-z0-9]+',' ',_clean(text).lower())+' '
    matched=[]
    for k in keywords:
        v=' '+re.sub(r'[^a-z0-9]+',' ',str(k).lower()).strip()+' '
        if len(v.strip())>2 and v in s:matched.append(k)
    return matched

def topics_with_evidence(reels,trends):
    bank=topic_bank(); d=competitor_metrics(reels)
    results=[]
    for _,r in bank.iterrows():
        kws=[x.strip().lower() for x in r['keywords'].split(',') if x.strip()]
        matches=d[d['caption'].fillna('').map(lambda s:bool(_hits(s,kws)))].copy() if not d.empty else pd.DataFrame()
        ts=trends[trends['search_term'].fillna('').map(lambda s:bool(_hits(s,kws)))].copy() if not trends.empty else pd.DataFrame()
        cm=int(len(matches)); cmr=int(matches['creator'].nunique()) if cm else 0
        rv=matches['relative_performance'].median() if cm else np.nan
        sufficient=int(matches['relative_performance'].notna().sum())>=3 if cm else False
        trends_n=len(ts)
        demand_seen=(trends_n>0) or (sufficient and pd.notna(rv) and rv>=1.2)
        priority=(2 if trends_n else 0)+(2 if sufficient and pd.notna(rv) and rv>=1.2 else 0)+(1 if demand_seen and cm<=2 else 0)
        if priority>=4:label='Review first'
        elif priority>=2:label='Worth investigating'
        else:label='Research pending'
        results.append({
            'Topic':r['title'],'Category':r['category'],'Proposed angle':r['angle'],
            'Opening hook':r['hook'],'Est. hours':r['estimated_hours'],
            'Matched trends':trends_n,'Matching competitor reels':cm,'Competitor creators':cmr,
            'Median relative public count':round(float(rv),2) if pd.notna(rv) else np.nan,
            'Research priority (/5)':priority if demand_seen else np.nan,
            'Evidence status':label,
            'Matched trend terms':', '.join(ts['search_term'].head(3)) if trends_n else '',
            'Reel URLs':', '.join(matches['reel_url'].dropna().head(3)) if cm else ''})
    return pd.DataFrame(results).sort_values(['Research priority (/5)','Matched trends','Matching competitor reels','Topic'],ascending=[False,False,False,True],na_position='last').reset_index(drop=True)

def score_index(scores,weights,max_value):
    if any(k not in scores or scores[k] is None or (isinstance(scores[k],float) and pd.isna(scores[k])) for k in weights):
        raise ValueError('All factor scores must be entered to calculate a complete index.')
    for k in weights:
        n=float(scores[k])
        if n<0 or n>max_value:raise ValueError(f'{k} rating must be 0–{max_value}.')
    return round(sum(float(scores[k])*w/max_value for k,w in weights.items()),1)

def scores_from_review(row):
    vals={k:_number(row.get(k)) for k in ICI_WEIGHTS}
    if any(pd.isna(v) or v>5 for v in vals.values()):return None
    return vals

def _load_reviews(base,demo=False):
    p=Path(base)/('lite_demo' if demo else 'data')/'lite_ici_reviews.csv'
    old=_read(p,['video_id','title','source_type','reviewer','review_date',*ICI_WEIGHTS,'overall_score','notes'])
    if demo:return old
    orig=Path(base)/'data'/'ici_ratings.csv'
    if orig.exists():
        r=_read(orig,[])
        if 'video_id' in r and len(r):
            r=r.copy()
            if 'source_type' not in r:r['source_type']='unknown'
            if 'video_title' in r and 'title' not in r:r['title']=r['video_title']
            if 'rater' in r and 'reviewer' not in r:r['reviewer']=r['rater']
            if 'review_date' not in r:r['review_date']=''
            if 'notes' not in r:r['notes']=r.get('evidence_notes','')
            if 'overall_score' not in r:r['overall_score']=np.nan
            old=pd.concat([old,r],ignore_index=True)
    return old

def industry_benchmark(base,demo=False):
    reviews=_load_reviews(base,demo)
    if reviews.empty:complete=pd.DataFrame(columns=reviews.columns)
    else:
        complete=reviews[reviews.apply(lambda r:scores_from_review(r) is not None,axis=1)]
        complete=complete[complete['source_type'].astype(str).str.lower().eq('competitor')]
    # Reduce multiple raters to one median per video before computing the industry reference.
    per_video=complete.groupby('video_id')[list(ICI_WEIGHTS)].median(numeric_only=True) if len(complete) else pd.DataFrame()
    unique=len(per_video)
    if unique>=5:
        factor_medians={k:round(float(per_video[k].median()),2) for k in ICI_WEIGHTS}
        status=('SYNTHETIC reference — demonstration only' if demo else ('Small reviewed competitor sample' if unique<15 else 'Reviewed competitor sample'))
        empirical=True
    else:
        factor_medians={k:4.0 for k in ICI_WEIGHTS}
        status='Provisional editorial reference (4/5 each) — NOT industry data'
        empirical=False
    return {'factors':factor_medians,'score':score_index(factor_medians,ICI_WEIGHTS,5),
            'count':unique,'status':status,'empirical':empirical}

def review_report(base,title,source_type,reviewer,notes,scores,demo=False,save=True,video_id=''):
    total=score_index(scores,ICI_WEIGHTS,5); bm=industry_benchmark(base,demo)
    compare=[]
    for key,w in ICI_WEIGHTS.items():
        x=float(scores[key]); b=bm['factors'][key]
        compare.append({'Factor':ICI_LABELS[key],'Weight':f'{w}%', 'Your score /5':x,'Reference /5':b,'Difference':round(x-b,2),'Contribution /100':round(x*w/5,1),'Meets reference?':'Yes' if x>=b else 'No'})
    table=pd.DataFrame(compare)
    gaps=[key for key in ICI_WEIGHTS if float(scores[key])<bm['factors'][key]]
    matched=len(ICI_WEIGHTS)-len(gaps)
    feedback=[ICI_TIPS[k] for k in gaps][:4]
    if save and not demo:
        p=Path(base)/'data'/'lite_ici_reviews.csv'
        d=_read(p,['video_id','title','source_type','reviewer','review_date',*ICI_WEIGHTS,'overall_score','notes'])
        row={'video_id':video_id or ('MANUAL_'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')),
             'title':title or 'Untitled','source_type':source_type,'reviewer':reviewer or 'Anonymous',
             'review_date':datetime.now(timezone.utc).date().isoformat(),'overall_score':total,'notes':notes or '',**scores}
        d=pd.concat([d,pd.DataFrame([row])],ignore_index=True)
        d.to_csv(p,index=False)
    summary=(f'### Reel score: {total:.1f}/100  |  Reference: {bm["score"]:.1f}/100\n\n'
        f'**Factor match:** {matched}/8 · **Overall difference:** {total-bm["score"]:+.1f} points\n\n'
        f'**Reference source:** {bm["status"]} ({bm["count"]} distinct reviewed competitor videos).\n\n'
        + ('**Main changes to consider:**\n'+'\n'.join(' - '+a for a in feedback) if feedback else '**All eight factors meet or exceed the current reference.**')
        +'\n\n*These are guided reviewer ratings, not automatic video analysis or predictions of virality.*')
    return summary,table

def score_spi(scores):
    return score_index(scores,SPI_WEIGHTS,100)

def performance_feedback(base):
    path=Path(base)/'data'/'lite_insights.csv'
    df=_read(path,['reel_id','views','reach','shares','saves','follows','observed_date','notes'])
    if df.empty:return pd.DataFrame(columns=['Reel ID','Views','Reach','Shares / reach','Saves / reach','Follows / reach'])
    for c in ['views','reach','shares','saves','follows']:df[c]=pd.to_numeric(df[c],errors='coerce')
    out=pd.DataFrame({'Reel ID':df['reel_id'],'Views':df['views'],'Reach':df['reach'],
       'Shares / reach':(df['shares']/df['reach'].replace(0,np.nan)).round(4),
       'Saves / reach':(df['saves']/df['reach'].replace(0,np.nan)).round(4),
       'Follows / reach':(df['follows']/df['reach'].replace(0,np.nan)).round(4)})
    return out

def add_insights(base,reel_id,views,reach,shares,saves,follows,notes):
    if not _clean(reel_id):raise ValueError('A reel ID is required.')
    p=Path(base)/'data'/'lite_insights.csv'; d=_read(p,['reel_id','views','reach','shares','saves','follows','observed_date','notes'])
    row={'reel_id':str(reel_id),'views':_number(views),'reach':_number(reach),'shares':_number(shares),'saves':_number(saves),'follows':_number(follows),
         'observed_date':datetime.now(timezone.utc).date().isoformat(),'notes':_clean(notes)}
    d=pd.concat([d,pd.DataFrame([row])],ignore_index=True)
    d.to_csv(p,index=False);return len(d)

def make_demo(base):
    folder=Path(base)/'lite_demo';folder.mkdir(parents=True,exist_ok=True)
    demo_rows=[]
    raw_topics=topic_bank().iloc[:12].reset_index(drop=True)
    for a in range(6):
        for j in range(5):
            t=raw_topics.iloc[(a*5+j)%len(raw_topics)]
            plays=round((7000+a*1400)*[0.75,1.1,2.1,0.9,1.25][j])
            demo_rows.append({'reel_id':f'SYN{a+1:02d}{j+1:02d}','creator':f'fictional_creator_{a+1}',
             'reel_url':'','published_at':'2026-10-10','caption':f'{t["title"]}. {t["angle"]}', 'transcript':'',
             'topic':t['title'],'category':t['category'],'story_angle':t['angle'],'duration_s':55+j*4,
             'views':np.nan,'plays':plays,'likes':round(plays*.045),'comments':round(plays*.003),
             'metric':plays,'metric_basis':'public plays','source':'SYNTHETIC_DEMO'})
    pd.DataFrame(demo_rows,columns=REEL_COLS).to_csv(folder/'lite_competitor_reels.csv',index=False)
    pd.DataFrame([
      {'search_term':'gold prices in India','volume_band':'50K+','started':'','status':'','snapshot_date':'2026-11-01','category':'Economics','source':'SYNTHETIC_DEMO'},
      {'search_term':'semiconductor chip factories','volume_band':'10K+','started':'','status':'','snapshot_date':'2026-11-01','category':'Economics','source':'SYNTHETIC_DEMO'},
      {'search_term':'government budget and deficit','volume_band':'5K+','started':'','status':'','snapshot_date':'2026-11-01','category':'UPSC','source':'SYNTHETIC_DEMO'},
    ]).to_csv(folder/'lite_trends.csv',index=False)
    review_rows=[]
    for a in range(6):
        row={'video_id':f'SYN{a+1:02d}01','title':f'Fictional example video {a+1}',
             'source_type':'competitor','reviewer':'Synthetic reviewer','review_date':'2026-11-01',
             'notes':'FICTIONAL: used only to test the interface'}
        for i,k in enumerate(ICI_WEIGHTS):row[k]=[4,3,5,4,4,3][(a+i)%6]
        row['overall_score']=score_index(row,ICI_WEIGHTS,5)
        review_rows.append(row)
    pd.DataFrame(review_rows).to_csv(folder/'lite_ici_reviews.csv',index=False)
    return folder

if __name__=='__main__':
    print('StoryScout Lite: functions loaded')

def export_research_report(base,demo=False):
    """Export a clearly provenance-labelled Markdown report; no invented findings."""
    base=Path(base); folder=base/'lite_exports';folder.mkdir(parents=True,exist_ok=True)
    reels=load_reels(base,demo);trends=load_trends(base,demo); bm=industry_benchmark(base,demo)
    market=market_table(reels); topics=topics_with_evidence(reels,trends)
    label='FICTIONAL / SYNTHETIC DEMONSTRATION' if demo else 'ACTUAL IMPORTED RESEARCH RECORDS'
    lines=[
      '# StoryScout Lite — Microeconomic Content Research Summary',
      f'Generated: {datetime.now(timezone.utc).date().isoformat()}  |  Dataset: **{label}**',
      '', '## Research question',
      'How can VicharDesk use limited production time to choose topics supported by audience-interest proxies and to compare draft quality against a consistent rubric?',
      '', '## Dataset coverage',
      f'- Public reel records: **{len(reels)}** across **{reels["creator"].nunique() if len(reels) else 0}** creators.',
      f'- Google Trends records: **{len(trends)}**; the trends dataset is a historical snapshot.',
      f'- Fully scored distinct competitor videos for ICI reference: **{bm["count"]}**.',
      '', '## Observed competitor sample (descriptive, not causal)',
    ]
    if market.empty:lines.append('No public competitor reels have been imported.')
    else:lines.append(market.to_markdown(index=False))
    lines+=['', '## Candidate topics (editorially curated)', 'Candidates come from a fixed topic library. Keywords locate possible supporting public signals; they are not evidence of future viral performance.']
    if len(topics):
        preview=topics[['Topic','Category','Matched trends','Matching competitor reels','Evidence status']].head(10)
        lines.append(preview.to_markdown(index=False))
    else:lines.append('No candidate topics available.')
    lines+=['','## Industry Content Index','The eight dimensions are rated by a human reviewer on a 0–5 scale. The weighted maximum is 100.']
    lines.append('| Quality factor | Weight | Reference /5 |')
    lines.append('|---|---:|---:|')
    for k,w in ICI_WEIGHTS.items():lines.append(f'| {ICI_LABELS[k]} | {w}% | {bm["factors"][k]:.1f} |')
    lines.append(f'\nCurrent reference = **{bm["score"]:.1f}/100**. Status: **{bm["status"]}**. This is not a prediction model.\n')
    lines+=['## Microeconomic interpretation',
        '- **Consumer demand:** public search interest and engagement provide limited revealed-preference proxies.',
        '- **Competitive supply:** the number and categories of competitor reels describe available content.',
        '- **Differentiation:** curated alternative angles help VicharDesk offer something distinct.',
        '- **Scarcity and opportunity cost:** estimated production hours help compare feasible alternatives.',
        '- **Information gaps:** small samples, account size, upload age and Instagram distribution create uncertainty.',
        '', '## Interpretation and limitations',
        'Scores are transparent editorial or descriptive indicators, not causal proof that a topic or hook increases views.',
        'Search-volume bands from Google Trends are retained as reported, not transformed into exact searches.',
        'Category labels are keyword-based and may need correction; no audio/video semantics are automatically inferred.',
        'An uncalibrated ICI reference is explicitly marked provisional; private retention metrics require verified Insights.',
        '', '## Data sources',
        '- Apify public Instagram reel export supplied by the researcher.',
        '- Google Trends India CSV snapshot supplied by the researcher.',
        '- Manually reviewed competitor videos and/or verified VicharDesk Insights when entered.',
        '- Static, editorially curated topic bank (not a live news feed).'
    ]
    path=folder/f'StoryScout_Research_Summary_{"SYNTHETIC" if demo else "RESEARCH"}.md'
    path.write_text('\n'.join(lines),encoding='utf-8')
    return str(path)
