"""Consolidated approved Wave 2 analysis. All effects that are rates use fractions."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT.parent/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"))
from shared_feature_diagnostics_v1 import read_master, CORE, G, KEY, FUNCTIONAL
LENS_NAMES=("01_nutritional_composition","02_nutrient_density",
            "03_claims_composition_and_ingredients","04_positioning_tradeoffs",
            "05_unsupervised_control")
LENS=[ROOT/name for name in LENS_NAMES]
B=399
rng=np.random.default_rng(4211)
rows=[]
mode="primary"

def emit(h,key,test,n,**values):
    rows.append(dict(h=h,variant=mode,**dict(zip(G,key)),test=test,n=n,**values))

def interval(values):
    x=np.asarray(values,float); x=x[np.isfinite(x)]
    if not len(x): return {}
    lo,hi=np.quantile(x,[.025,.975])
    return dict(lo=lo,hi=hi)

def ratio(a,b):
    return a/b if b else np.nan

def boot_prop(success,n):
    return interval(rng.binomial(n,success/n,B)/n) if n else {}

def centered_tail(boot,point):
    valid=np.asarray(boot)[np.isfinite(boot)]
    return (1+np.sum(np.abs(valid-point)>=abs(point)))/(1+len(valid))

class Values:
    """Integer value indices allow exact tied ranks and interpolated quantiles in each bootstrap."""
    def __init__(self,x):
        self.x=np.asarray(x)
        self.values,self.idx=np.unique(self.x,return_inverse=True)
    def distribution(self,w):
        return np.cumsum(np.bincount(self.idx,weights=w,minlength=len(self.values)))
    def quant(self,c,q):
        p=q*(c[-1]-1)
        a,b=np.searchsorted(c,[np.floor(p),np.ceil(p)],side="right")
        return self.values[a]+(self.values[b]-self.values[a])*(p%1)
    def ranks(self,c):
        return ((c+np.r_[0,c[:-1]]+1)/(2*c[-1]))[self.idx]

def weights(n):
    return np.bincount(rng.integers(n,size=n),minlength=n)

def profile_flags(x,y,w,low):
    a=x.quant(x.distribution(w),.75)
    b=y.quant(y.distribution(w),.25 if low else .75)
    left=x.x>a; right=y.x<b if low else y.x>b
    return left,right,a,b

def h1(g,key):
    ref=g.dropna(subset=CORE); n=len(ref)
    if n<30: return
    for a,b,low in [('protein','sugars',True),('fat','salt',False)]:
        x,y=Values(ref[a]),Values(ref[b])
        u,v,q1,q2=profile_flags(x,y,np.ones(n),low); both=u&v
        expect=u.mean()*v.mean(); obs=both.mean()
        if not u.any() or not v.any():
            emit("H1",key,a+"_"+b,n,status="tied/empty arm",cut_a=q1,cut_b=q2)
            continue
        draws=[]
        for _ in range(B if mode=="primary" else 0):
            w=weights(n); z,t,_,_=profile_flags(x,y,w,low)
            draws.append(np.dot(w,z&t)/n-np.dot(w,z)*np.dot(w,t)/n**2)
        emit("H1",key,a+"_"+b,n,effect=obs-expect,observed=obs,expected=expect,
             cut_a=q1,cut_b=q2,success_n=both.sum(),p=stats.hypergeom.sf(both.sum()-1,n,u.sum(),v.sum()),
             profile_fibre=ref.loc[both,'fibre'].median(),profile_satfat=ref.loc[both,'saturated_fat'].median(),
             **{m+"_median":ref.loc[both,m].median() for m in CORE},**interval(draws))

def h2(g,key):
    if key[1]!='cereal' or key[2] not in ['GRANOLA','FLAKES']: return
    v=g.dropna(subset=['energy','sugars']).sort_values(['energy','barcode'])
    for tol in [5,10,20]:
        for direction in ['forward','reverse']:
            a=v if direction=='forward' else v.iloc[::-1]
            e=a.energy.to_numpy(); s=a.sugars.to_numpy(); gaps=[]; egaps=[]; i=0
            while i+1<len(e):
                if abs(e[i+1]-e[i])<=tol:
                    gaps.append(abs(s[i+1]-s[i])); egaps.append(abs(e[i+1]-e[i])); i+=2
                else: i+=1
            hits=int((np.asarray(gaps)>=5).sum())
            if gaps:
                emit('H2',key,'sugar gap >=5g',len(v),pairs=len(gaps),tol=tol,direction=direction,
                     effect=hits/len(gaps),median_gap=np.median(gaps),median_energy_gap=np.median(egaps),
                     max_energy_gap=max(egaps),success_n=hits,**boot_prop(hits,len(gaps)))

def density(g,key):
    for m in ['protein','fibre']:
        base=g.dropna(subset=[m,m+'_density'])
        for floor in [10,0,5,20]:
            d=base[base.energy.ge(floor)]; n=len(d)
            if n<30: continue
            x,y,e=[Values(d[col]) for col in [m,m+'_density','energy']]
            def measure(w):
                cx,cy,ce=[v.distribution(w) for v in (x,y,e)]
                rx=x.ranks(cx); ry=y.ranks(cy)
                high=x.x>=x.quant(cx,.75); high_e=e.x>=e.quant(ce,.75)
                below=y.x<=y.quant(cy,.5)
                informative=(x.quant(cx,.25)<x.quant(cx,.75) and e.quant(ce,.25)<e.quant(ce,.75)
                             and y.quant(cy,.25)<y.quant(cy,.75))
                upper=np.dot(w,high)
                return (np.dot(w,np.abs(rx-ry)>=.25)/w.sum(),ratio(np.dot(w,high&high_e&below),upper)
                        if informative else np.nan,upper,rx,ry)
            w=np.ones(n); a,b,upper,rx,ry=measure(w)
            count=B if floor==10 and mode=="primary" else 0
            draws=[measure(weights(n))[:2] for _ in range(count)]
            rho=np.corrcoef(rx,ry)[0,1] if np.ptp(rx)>0 and np.ptp(ry)>0 else np.nan
            emit('H3',key,m,n,energy_floor=floor,effect=a,spearman=rho,observed_zeros=(x.x==0).sum(),
                 **interval([v[0] for v in draws]))
            emit('H4',key,m,n,energy_floor=floor,effect=b,upper_n=upper,
                 converse=np.mean((x.x<=np.median(x.x))&(y.x>=np.quantile(y.x,.75))),
                 ties_q3=int((x.x==np.quantile(x.x,.75)).sum()),**interval([v[1] for v in draws]))

def state(g,claim):
    flag=g["claims_claim_"+claim]
    locked=g["claims_state_"+claim]
    valid=g.assessed_layer & g.claims_source_market_limitation.fillna('').eq('')
    return np.select([valid & flag.eq(True).fillna(False),
                      valid & locked.eq('DOCUMENTED_NOT_DETECTED').fillna(False)],
                     [1,0],default=-1)

def median_contrast(x,y):
    point=np.median(x)-np.median(y)
    reps=np.median(rng.choice(x,(B,len(x))),axis=1)-np.median(rng.choice(y,(B,len(y))),axis=1)
    p=stats.median_test(x,y,correction=False)[1] if np.unique(np.r_[x,y]).size>1 and np.any(np.r_[x,y]>np.median(np.r_[x,y])) else 1.
    return dict(effect=point,median_pos=np.median(x),median_neg=np.median(y),p=p,**interval(reps))

def h5_h6(g,key):
    for c,m in [('protein_claim','protein'),('fibre_claim','fibre'),('reduced_sugar','sugars'),
                ('sugar_free_claim','sugars'),('reduced_fat_claim','fat')]:
        a=g.dropna(subset=[m]); s=state(a,c)
        for source in (['all','direct','rule'] if c=='protein_claim' else ['all']):
            pos=s==1
            if source!='all':
                pos &= a.claims_basis_protein_claim.fillna('').eq('DIRECT_OCR_WORDING' if source=='direct' else 'APPROVED_EXISTING_RULE').to_numpy()
            x=a.loc[pos,m].to_numpy(); y=a.loc[s==0,m].to_numpy()
            out=median_contrast(x,y) if min(len(x),len(y))>=20 else {}
            emit('H5',key,c,len(a),provenance=source,pos=len(x),neg=len(y),**out)
    a=g.dropna(subset=CORE)
    if len(a)<30: return
    iqr=(a[CORE].quantile(.75)-a[CORE].quantile(.25)).to_numpy()
    eligible=a[a.assessed_layer & a.claims_nutrition_qa_hold.fillna('').eq('')].sort_values('barcode')
    for c in ['organic_claim','plant_based_claim','gluten_free_claim','natural_claim','heritage_claim','protein_claim']:
        s=state(eligible,c); known=s>=0; z=eligible.loc[known,CORE].to_numpy(); s=s[known]
        pos=(s==1).sum(); neg=(s==0).sum()
        if min(pos,neg)<20:
            emit('H6',key,c,len(a),pos=pos,neg=neg,status='small arm');continue
        used=np.zeros(len(z),bool); hits=0; gaps=[]
        for i in range(len(z)):
            if used[i]: continue
            cand=np.flatnonzero(~used & (np.arange(len(z))>i))
            d=np.abs(z[cand]-z[i]); keep=np.all(d<=.25*iqr,axis=1)
            if not keep.any(): continue
            dist=d[keep]/np.where(iqr>0,iqr,1)
            j=cand[keep][np.argmin(np.sum(dist**2,axis=1))]
            used[[i,j]]=True; hits+=int(s[i]!=s[j]);gaps.append(np.abs(z[j]-z[i]))
        n=len(gaps)
        emit('H6',key,c,len(a),pos=pos,neg=neg,pairs=n,success_n=hits,effect=ratio(hits,n),
             **({m+'_max_gap':v for m,v in zip(CORE,np.max(gaps,axis=0))} if n else {}),**boot_prop(hits,n))

def h7(g,key):
    a=g[g.ingredient_ok]; cue=a.pea_soy_text_cue.eq(True).to_numpy()
    for c in ['protein_claim','plant_based_claim','no_artificial']:
        s=state(a,c); pos=s==1; neg=s==0; x=cue[pos]; y=cue[neg]
        res={}
        if min(len(x),len(y))>=20:
            draws=rng.binomial(len(x),x.mean(),B)/len(x)-rng.binomial(len(y),y.mean(),B)/len(y)
            res=dict(effect=x.mean()-y.mean(),p=stats.fisher_exact([[x.sum(),len(x)-x.sum()],[y.sum(),len(y)-y.sum()]])[1],**interval(draws))
        emit('H7',key,c,len(a),pos=len(x),neg=len(y),hit_pos=x.sum(),hit_neg=y.sum(),**res)

def tradeoffs(g,key):
    for h,c,m in [('H9','protein_claim','salt'),('H9','fibre_claim','sugars'),
                  ('H9','reduced_fat_claim','sugars'),('H11','protein_claim','protein_density'),
                  ('H11','fibre_claim','fibre_density'),('H10','organic_claim','sugars')]:
        if h=='H10' and key[:3]!=('US-CA','cereal','GRANOLA'): continue
        a=g.dropna(subset=[m])
        if h=='H11': a=a[a.energy.ge(10)]
        if len(a)<30: continue
        s=state(a,c)
        if m=='salt':
            s[a.claims_nutrition_qa_hold.fillna('').ne('').to_numpy()]=-1
        pos=s==1; neg=s==0; extra={}
        if h=='H10':
            second=state(a,'protein_claim')
            pos=(s==1)&(second==0); neg=(s==0)&(second==1)
            extra=dict(both=((s==1)&(second==1)).sum(),neither=((s==0)&(second==0)).sum(),
                       unknown_panel=((s<0)|(second<0)).sum())
        x=Values(a[m]); w=np.ones(len(a))
        q=x.quant(x.distribution(w),.75); high=x.x>q
        if h=='H11':
            den=(high&(pos|neg)).sum(); effect=ratio((high&neg).sum(),den)
            supported=den>=30
            extra.update(unknown_high=(high & (s<0) & a.assessed_layer.to_numpy()).sum(),
                         unmatched_high=(high & ~a.claims_matched.eq(True).fillna(False).to_numpy()).sum(),
                         adjudicated_high=(high & a['claims_state_'+c].eq('HUMAN_CONFIRMED_NEGATIVE').fillna(False).to_numpy()).sum())
        else:
            den=pos.sum()+neg.sum(); effect=ratio((high&pos).sum(),pos.sum())-ratio((high&neg).sum(),neg.sum())
            supported=min(pos.sum(),neg.sum())>=20
        draws=[]
        if supported and mode=='primary':
            for _ in range(B):
                w=weights(len(a)); high_b=x.x>x.quant(x.distribution(w),.75)
                hp=np.dot(w,high_b&pos); hn=np.dot(w,high_b&neg)
                draws.append(ratio(hn,hn+hp) if h=='H11' else ratio(hp,w[pos].sum())-ratio(hn,w[neg].sum()))
        if h!='H11' and supported:
            extra['p']=stats.fisher_exact([[(high&pos).sum(),(~high&pos).sum()],[(high&neg).sum(),(~high&neg).sum()]])[1]
        emit(h,key,c,len(a),pos=pos.sum(),neg=neg.sum(),hit_pos=(high&pos).sum(),hit_neg=(high&neg).sum(),
             threshold=q,ties_q3=(x.x==q).sum(),known_n=den,effect=effect,supported=supported,**interval(draws),**extra)

def h8(df):
    layer=df[df.assessed_layer & df.category.eq('beverages') & df.claims_source_market_limitation.fillna('').eq('')]
    for key,g in layer[layer.peer & layer.basis_group.eq('per_100ml_liquid')].groupby(G):
        valid=g.dropna(subset=['energy','sugars'])
        for name in FUNCTIONAL:
            s=valid['claims_'+name]
            for label,group in [('positive',valid[s.eq(True).fillna(False)]),('documented non-detection',valid[s.eq(False).fillna(False)]),('unknown',valid[s.isna()])]:
                emit('H8',key,name,len(g),state=label,valid_n=len(valid),state_n=len(group),
                     energy_median=group.energy.median(),sugars_median=group.sugars.median())
        for name in FUNCTIONAL[1:]:
            a=valid.claims_energy_positioning;b=valid['claims_'+name]
            for aa in [True,False,None]:
                for bb in [True,False,None]:
                    mask=(a.isna() if aa is None else a.eq(aa).fillna(False)) & (b.isna() if bb is None else b.eq(bb).fillna(False))
                    emit('H8',key,'joint '+name,len(valid),state=str(aa)+'/'+str(bb),state_n=mask.sum())
    reg=layer[layer.claims_energy_positioning.eq(True).fillna(False)&layer.claims_energy_drink_format.fillna('').ne('')]
    for (region,fmt),g in reg.groupby(['region','claims_energy_drink_format']):
        emit('H8',(region,'beverages',fmt,'registry as reported'),'registry',len(g),valid_n=len(g.dropna(subset=['energy','sugars'])))

def geography(df):
    # Deterministic Poisson(1) bootstrap weight shared by each GTIN across strata and regions.
    edges=stats.poisson.cdf(np.arange(15),1)
    def blockweights(ids,rep):
        z=ids+np.uint64(rep+1)*np.uint64(0x9E3779B1)
        z=(z^(z>>30))*np.uint64(0xbf58476d1ce4e5b9)
        z=(z^(z>>27))*np.uint64(0x94d049bb133111eb)
        return np.searchsorted(edges,((z^(z>>31))>>11).astype(float)/2**53)
    for market in ['UK-IE','US-CA']:
        common=set(df.loc[df.region.eq('FR'),'barcode']) & set(df.loc[df.region.eq(market),'barcode'])
        records={}
        for key,g in df[df.region.isin(['FR',market])].groupby(G[1:]):
            for name,xcol,ycol in [('protein_sugars','protein','sugars'),('fat_salt','fat','salt'),('protein_claim','protein',None)]:
                for exclude in [False,True]:
                    cells=[]; base=[]
                    for reg in ['FR',market]:
                        raw=g[g.region.eq(reg)]
                        if exclude: raw=raw[~raw.barcode.isin(common)]
                        base.append(len(raw))
                        a=raw.dropna(subset=CORE if ycol else ['protein'])
                        if not ycol:
                            s=state(a,'protein_claim'); a=a[s>=0].copy();a['observed']=s[s>=0]
                        cells.append(a)
                    left,right=cells; ns=[len(z) for z in cells]
                    if min(ns)<30 or (not ycol and any(min(z.observed.sum(),len(z)-z.observed.sum())<20 for z in cells)):
                        emit('H12',(market,*key),name,sum(ns),reference_n=ns[0],comparison_n=ns[1],
                             reference_base=base[0],comparison_base=base[1],exclude_shared=exclude,status='small cell')
                        continue
                    ids=[pd.util.hash_pandas_object(z.barcode,index=False).to_numpy('uint64') for z in cells]
                    if ycol: x,y=Values(left[xcol]),Values(left[ycol])
                    def measure(ws):
                        if not min(w.sum() for w in ws): return np.nan
                        if ycol:
                            _,_,qx,qy=profile_flags(x,y,ws[0],name=='protein_sugars')
                            flags=[(z[xcol].to_numpy()>qx)&((z[ycol].to_numpy()<qy) if name=='protein_sugars' else (z[ycol].to_numpy()>qy)) for z in cells]
                        else: flags=[z.observed.to_numpy() for z in cells]
                        rates=[np.dot(w,flag)/w.sum() for w,flag in zip(ws,flags)]
                        return rates[1]-rates[0]
                    point=measure([np.ones(n) for n in ns])
                    boot=np.array([measure([blockweights(v,i) for v in ids]) for i in range(B)])
                    emit('H12',(market,*key),name,sum(ns),reference_n=ns[0],comparison_n=ns[1],reference_base=base[0],
                         comparison_base=base[1],exclude_shared=exclude,effect=point,
                         p=centered_tail(boot,point) if mode=='primary' and not exclude else np.nan,**interval(boot))
                    records.setdefault((name,exclude),[]).append((point,boot,ns[0]))
        for (name,exclude),items in records.items():
            for scheme in ['equal cells','reference observation weights']:
                w=np.array([1 if scheme=='equal cells' else t[2] for t in items])
                point=np.average([t[0] for t in items],weights=w)
                boots=np.average([t[1] for t in items],weights=w,axis=0)
                emit('H12',(market,'ALL','common supported cells','within basis'),name,len(items),
                     weighting=scheme,exclude_shared=exclude,effect=np.average([t[0] for t in items],weights=w),
                     p=centered_tail(boots,point) if mode=='primary' and not exclude and scheme=='equal cells' else np.nan,
                     **interval(boots))

def sensitivities(peers):
    global mode,rng
    rng=np.random.default_rng(4211)
    audited=pd.read_csv(LENS[2]/"ingredient_validation_v1.csv",dtype={"barcode":str})
    unavailable=audited.loc[audited.review_label.eq("unassessable"),KEY]
    keys=pd.MultiIndex.from_frame(unavailable)
    for key,g in peers.groupby(G):
        reviewed_bad=pd.MultiIndex.from_frame(g[KEY]).isin(keys)
        if reviewed_bad.any():
            mode="exclude audited language mismatches"
            h7(g[~reviewed_bad],key)
        for lang in ["EN","FR","BOTH"]:
            mode="ingredient language "+lang
            h7(g[g.ingredients_lang.eq(lang) & ~reviewed_bad],key)
    mode="exclude LOW"
    geography(peers[peers.confidence.ne("LOW")])
    mode="primary"

def adjust(result):
    primary=result.variant.eq("primary")
    for h,mask,column,denominator,null in [
            ("H2",result.tol.eq(10)&result.direction.eq("forward"),"success_n","pairs",.15),
            ("H6",result.pairs.ge(30),"success_n","pairs",.10),
            ("H11",result.known_n.ge(30),"hit_neg","known_n",.10)]:
        for i,row in result[primary & result.h.eq(h) & mask].iterrows():
            result.loc[i,"p"]=stats.binomtest(int(row[column]),int(row[denominator]),null,alternative="greater").pvalue
    for h,g in result[primary & result.p.notna()].groupby("h"):
        g=g[g.provenance.fillna("all").eq("all")]
        if len(g): result.loc[g.index,"q"]=stats.false_discovery_control(g.p.to_numpy())
    return result

def main():
    global mode
    df,_=read_master()
    peers=df[df.peer]
    assert len(peers)==292302
    h8(df)
    for key,g in peers.groupby(G):
        mode='primary'
        for label,cell in [('primary',g),('exclude LOW',g[g.confidence.ne('LOW')])]:
            if label!='primary' and len(cell)==len(g): continue
            mode=label
            h1(cell,key); h2(cell,key); density(cell,key); h5_h6(cell,key); h7(cell,key); tradeoffs(cell,key)
        qa=g.claims_population_qa_note.fillna('').ne('') | g.claims_evidence_cohort.eq('historical_dairy_reuse').fillna(False)
        if qa.any():
            mode='exclude QA and historical'; sensitivity=g[~qa]
            h5_h6(sensitivity,key);h7(sensitivity,key);tradeoffs(sensitivity,key)
    mode='primary'; geography(peers)
    sensitivities(peers)
    result=adjust(pd.DataFrame(rows))
    for i,tests in enumerate([['H1','H2','H12'],['H3','H4'],['H5','H6','H7','H8'],['H9','H10','H11']]):
        table=result[result.h.isin(tests)].dropna(axis=1,how='all')
        table.to_csv(LENS[i]/'hypothesis_results_v1.csv',index=False,float_format='%.9g')
    print(result.groupby('h').size(),flush=True)

if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        main()
