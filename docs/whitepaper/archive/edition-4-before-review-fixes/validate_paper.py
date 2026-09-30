"""Check published claims and the revised permutation method against independent arithmetic.

Runs offline. Writes validation.json beside the paper. No production data are changed.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from evaluate_backtest import permutation_test

HERE = Path(__file__).resolve().parent


def main() -> None:
    results = json.loads((HERE / 'evaluation/results.json').read_text())
    trades = pd.read_csv(HERE / 'evaluation/trades.csv')
    origin = json.loads((HERE / 'evaluation/origin-ledger/results.json').read_text())
    ledger = pd.read_csv(HERE / 'evaluation/origin-ledger/trades.csv')
    evidence = json.loads((HERE / 'figure-data/evidence.json').read_text())
    checks: dict[str, object] = {}
    assert set(trades.model) == {'gemini-2.5-flash'}
    assert not trades.duplicated(['ticker', 'fiscal_year']).any()
    checks['evaluation_scope'] = {'readings': len(trades), 'model': 'gemini-2.5-flash', 'unique_company_years': True}
    assert results['counts']['deduped_all_models'] == 6653
    assert results['counts']['excluded_model_mismatch'] == 2
    assert results['counts']['unique_company_years'] == 6651
    for name, spec in results['primary'].items():
        horizon = spec['horizon']
        sample = trades[trades[f'exit_{horizon}'] < '2025-01-31'] if name == 'historical' else trades[trades.filing_date > '2025-01-31']
        sample = sample.dropna(subset=[f'excess_{horizon}'])
        buys = sample.verdict.isin(['BUY', 'STRONG BUY'])
        sells = sample.verdict.isin(['SELL', 'STRONG SELL'])
        spread = sample.loc[buys, f'excess_{horizon}'].mean() - sample.loc[sells, f'excess_{horizon}'].mean()
        assert abs(spread - spec['summary']['spread']) < 1e-12
        assert buys.sum() == spec['summary']['n_long']
        assert sells.sum() == spec['summary']['n_short']
        checks[name] = {'n_buy': int(buys.sum()), 'n_sell': int(sells.sum()), 'spread': spread}
        sizes = sample.groupby(['fiscal_year', 'industry']).ticker.transform('size')
        restricted = sample[sizes >= 2]
        rank = restricted.groupby('fiscal_year')[f'excess_{horizon}'].rank(pct=True)
        observed = rank[restricted.verdict.isin(['BUY', 'STRONG BUY'])].mean() - rank[restricted.verdict.isin(['SELL', 'STRONG SELL'])].mean()
        assert abs(observed - spec['rank_within_vintage_industry']['observed_spread']) < 1e-12
        assert spec == evidence['backtest']['primary'][name]
    for kind in ['compounder', 'alpha']:
        sample = ledger[ledger.score == kind].copy()
        sizes = sample.groupby('industry').ticker.transform('size')
        sample = sample[sizes >= 2]
        rho = float(spearmanr(sample.value, sample.excess).statistic)
        assert abs(rho - origin['scores'][kind]['spearman']['observed']) < 1e-12
        checks[kind] = {'n': len(sample), 'spearman': rho}
    # Exact enumeration of a small blocked null with a large NONZERO centre.
    # Independent combinatorial reference: choose which A item is SELL and B item is BUY.
    fixture = pd.DataFrame({'fiscal_year': [2020]*3+[2021]*3, 'verdict': ['BUY','BUY','SELL','BUY','SELL','SELL'], 'r': [100.,101.,105.,0.,1.,8.]})
    v = fixture.r.to_numpy()
    exact = []
    for sell_a, buy_b in itertools.product(range(3), range(3,6)):
        b = [i for i in range(3) if i != sell_a] + [buy_b]
        s = [sell_a] + [i for i in range(3,6) if i != buy_b]
        exact.append(float(v[b].mean()-v[s].mean()))
    null = np.array(exact)
    obs = v[[0,1,3]].mean()-v[[2,4,5]].mean()
    # Equality tolerance includes exactly tied extremes in the discrete distribution.
    exact_p = float(np.mean(np.abs(null-null.mean()) >= abs(obs-null.mean())-1e-10))
    cfg = {'long_verdicts':['BUY'], 'short_verdicts':['SELL'], 'min_block_size':2, 'permutations':10000}
    test = permutation_test(fixture, 'r', ['fiscal_year'], cfg, np.random.default_rng(731))
    assert abs(test['p_two_sided']-exact_p) < .04
    old_zero_p = float(np.mean(np.abs(null) >= abs(obs)-1e-10))
    assert abs(old_zero_p-exact_p) > .2
    checks['permutation_nonzero_null_fixture'] = {'exact_p':exact_p, 'sampled_p':test['p_two_sided'], 'incorrect_zero_centre_p':old_zero_p, 'null_mean':float(null.mean())}
    paper = (HERE/'eon-whitepaper.md').read_text()
    assert 'p = 0.0059' in paper and 'SIX_' not in paper
    assert paper.count('*Figure ') == 17
    assert 'preregistered clean test' not in paper
    inputs = ['eon-whitepaper.md','evaluate_backtest.py','evaluate_origin_ledger.py','evaluation/results.json','evaluation/trades.csv','evaluation/origin-ledger/results.json','evaluation/origin-ledger/trades.csv','figure-data/evidence.json']
    report = {'timestamp':datetime.now(UTC).isoformat(), 'status':'passed', 'checks':checks, 'inputs':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in inputs}}
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'passed','checks':len(checks),'permutation_fixture':checks['permutation_nonzero_null_fixture']},indent=2))

if __name__ == '__main__':
    main()
