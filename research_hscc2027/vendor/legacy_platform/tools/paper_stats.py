"""Shared, finite statistical summaries for the final paper analysis."""
import math
import warnings
import numpy as np
from scipy import stats

def finite(x):
    return x is not None and math.isfinite(float(x))

def holm(ps):
    vals = [float(p) if finite(p) else 1.0 for p in ps]
    out = [1.0] * len(vals)
    running = 0.0
    for rank, i in enumerate(sorted(range(len(vals)), key=vals.__getitem__)):
        running = max(running, min(1.0, vals[i] * (len(vals)-rank)))
        out[i] = running
    return out

def summary(values, binary=False):
    a = np.asarray([float(v) for v in values if finite(v)])
    n = len(a)
    if not n: return {'n':0,'mean':None,'sd':None,'ci95':[None,None]}
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if n>1 else 0.0
    if binary:
        # Wilson interval remains informative at rates 0 and 1.
        z = float(stats.norm.ppf(.975)); den = 1+z*z/n
        center = (mean+z*z/(2*n))/den
        half = z*math.sqrt(mean*(1-mean)/n+z*z/(4*n*n))/den
        ci = [max(0.,center-half),min(1.,center+half)]
    else:
        half = float(stats.t.ppf(.975,n-1))*sd/math.sqrt(n) if n>1 else 0.
        ci = [mean-half,mean+half]
    return {'n':n,'mean':mean,'sd':sd,'ci95':ci}

def paired(a_vals,b_vals):
    """Difference = other minus baseline; exact constant differences explicit."""
    if len(a_vals)!=len(b_vals): raise ValueError('Unaligned paired inputs')
    xy=[(float(a),float(b)) for a,b in zip(a_vals,b_vals) if finite(a) and finite(b)]
    if len(xy)<2: return None
    a,b=np.asarray(xy).T; delta=b-a
    s=summary(delta)
    constant=bool(np.all(delta==delta[0]))
    if np.all(delta==0): p=wp=1.0; t=0.0
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            test=stats.ttest_rel(b,a)
            p=float(test.pvalue); t=float(test.statistic)
            wp=float(stats.wilcoxon(b,a).pvalue)
        if not finite(t): t=None
    p_test='paired_t'
    if constant and delta[0]!=0:
        # A t statistic is undefined with zero difference variance. Use the
        # reported paired signed-rank test, keeping the exact raw difference.
        p=wp; t=None; p_test='wilcoxon_constant_difference'
    pooled=math.sqrt((float(a.var(ddof=1))+float(b.var(ddof=1)))/2)
    effect=float(delta.mean()/pooled) if pooled>0 else (0.0 if np.all(delta==0) else None)
    return {'n':len(xy),'diff_mean':s['mean'],'diff_sd':s['sd'],'diff_ci95':s['ci95'],
            'ci95':s['ci95'],'p':p,'t':t,'wilcoxon_p':wp,'cohens_d':effect,
            'constant_paired_difference':constant,'p_test':p_test}

def mcnemar(a_vals,b_vals):
    if len(a_vals)!=len(b_vals): raise ValueError('Unaligned paired inputs')
    xy=[(bool(a),bool(b)) for a,b in zip(a_vals,b_vals) if finite(a) and finite(b)]
    if not xy: return None
    b=sum(not x and y for x,y in xy); c=sum(x and not y for x,y in xy)
    p=float(stats.binomtest(b,b+c,.5).pvalue) if b+c else 1.0
    delta=[int(y)-int(x) for x,y in xy]
    return {'n':len(xy),'b':b,'c':c,'p':p,'diff_mean':sum(delta)/len(delta),
            'ci95':summary(delta)['ci95'],'ci_method':'paired risk-difference t interval; descriptive',
            'kind':'mcnemar'}
