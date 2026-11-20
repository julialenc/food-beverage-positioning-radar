"""Build the reproducible EN/FR ingredient validation sample from the approved population."""
import hashlib
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/"02_shared_preprocessing_and_eda/02_eda/00_shared_baseline_and_feature_diagnostics"))
from shared_feature_diagnostics_v1 import read_master, MASTER, KEY

def sample(df):
    eligible=df[df.peer & df.assessed_layer & df.ingredient_ok & df.claims_source_market_limitation.fillna("").eq("")]
    raw=pq.read_table(MASTER,columns=KEY+["ingredients_text"]).to_pandas()
    g=eligible[KEY+["ingredients_lang","pea_soy_text_cue"]].merge(raw,on=KEY,validate="one_to_one")
    near=g.ingredients_text.str.contains(r"(?:pea|pois|so[jy]|soya)",case=False,regex=True)
    g["stratum"]=np.select([g.pea_soy_text_cue.eq(True),near],["hit","near"],default="other")
    parts=[]
    for key,frame in g.groupby(["ingredients_lang","stratum"]):
        part=frame.sort_values(KEY).sample(n=min(8,len(frame)),random_state=42).copy()
        part["stratum_n"]=len(frame)
        parts.append(part)
    return pd.concat(parts).sort_values(KEY).reset_index(drop=True)

if __name__=="__main__":
    frame=sample(read_master()[0])
    identity=frame[KEY].to_csv(index=False,lineterminator="\n").encode()
    if hashlib.sha256(identity).hexdigest()!="2241d2245791d166bc41cb5156963bd3db39124cf161e1376dec7f248633cfa1":
        raise ValueError("Validation sample differs from the reviewed keys")
    # Codex text review, independent of the detector output at labelling time.
    # Unsupported-language passages remain unassessable; keep them in the audit.
    positives={0,2,3,8,14,16,18,19,26,27,28,29,30,31,38,43,51,55,62,63,64,65,68,70}
    unsupported={50,52,53,60,69,71}
    frame["review_label"]=["unassessable" if i in unsupported else "present" if i in positives else "not observed"
                           for i in frame.index]
    frame.to_csv(HERE/"ingredient_validation_v1.csv",index=False,encoding="utf-8-sig")
    print(frame.groupby(["stratum","review_label"]).size())
