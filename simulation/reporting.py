"""Read-only daily company/process reporting, separate from material-flow math.

The mean is an equal-company mean within each registered process. It is neither
market-weighted fulfillment nor industry production. Missing company/process
pairs remain None and are never imputed as zero or normal supply.
"""
from copy import deepcopy


class ProcessReporter:
    def __init__(self, network, scopes):
        self.processes = list(network['process_outputs'])
        self.unscored_operations = {key for key,node in network['nodes'].items()
            if network.get('scoring_policy') and node.get('kind')=='operation' and not any(
                network['nodes'][dep].get('scope','core') in scopes for dep in node.get('requires',[]))}
        owners = {operation: company for (company, _), operation in network.get('operations', {}).items()}
        self.outputs = {}
        self.companies = []
        for process, outputs in network['process_outputs'].items():
            mapping = {}
            for key in outputs:
                company = owners.get(key, 'node:' + key)
                if company in mapping:
                    raise ValueError('기업·공정별 출력은 하나여야 합니다.')
                mapping[company] = key
                if company not in self.companies:
                    self.companies.append(company)
            self.outputs[process] = mapping
        self.company_names = {company: network['nodes'].get(company.removeprefix('node:'), {}).get('name', company.removeprefix('node:')) for company in self.companies}
        self.company_processes = {company: [p for p, mapping in self.outputs.items() if company in mapping] for company in self.companies}
        self.coverage = {}
        for company in self.companies:
            self.coverage[company] = {}
            for process, mapping in self.outputs.items():
                if company not in mapping:
                    continue
                todo = [mapping[company]]
                seen = set()
                gaps = set()
                while todo:
                    key = todo.pop()
                    if key in seen:
                        continue
                    seen.add(key)
                    node = network['nodes'][key]
                    if node.get('scope', 'core') not in scopes:
                        continue
                    gaps.update(node.get('coverage_gap_ids', []))
                    todo.extend(node.get('requires', []))
                    if node.get('alt_vendor'):
                        todo.append(node['alt_vendor'])
                if gaps:
                    self.coverage[company][process] = sorted(gaps)
        self.keys = ['worst', 'mean', *self.companies]
        self.timelines = {key: [] for key in self.keys}
        self.first_hits = {key: {} for key in self.keys}

    def observe(self, day, daily, worst):
        per_company = {company: {} for company in self.companies}
        means = {}
        for process, mapping in self.outputs.items():
            values = {company: daily[node]['effective'] * 100 for company, node in mapping.items() if node not in self.unscored_operations}
            means[process] = sum(values.values()) / len(values) if values else None
            for company in self.companies:
                per_company[company][process] = values.get(company)
        views = dict(worst=worst, mean=means, **per_company)
        for key, scores in views.items():
            self.timelines[key].append(dict(day=day, **scores))
            for process, value in scores.items():
                if value is not None and value < 100 - 1e-7:
                    self.first_hits[key].setdefault(process, day)

    def finish(self):
        combined_gaps = {}
        for company in self.companies:
            for process, gaps in self.coverage[company].items():
                combined_gaps.setdefault(process, set()).update(gaps)
        combined_gaps = {p: sorted(gaps) for p, gaps in combined_gaps.items()}
        views = {}
        for key in self.keys:
            timeline = self.timelines[key]
            scores = {p: timeline[-1][p] for p in self.processes}
            supported = [p for p, value in scores.items() if value is not None]
            average_scores = {p: sum(row[p] for row in timeline) / len(timeline) if p in supported else None for p in self.processes}
            views[key] = dict(
                scores=scores, overall=min((scores[p] for p in supported), default=None),
                timeline=timeline, first_hit=self.first_hits[key],
                average_scores=average_scores,
                incomplete_processes=deepcopy(combined_gaps if key in ('worst', 'mean') else self.coverage[key]),
                registered_processes=supported,
            )
        return dict(
            process_views=views, company_names=self.company_names,
            company_processes=self.company_processes,
            unscored_operations=sorted(self.unscored_operations),
            aggregation_note='각 공정의 등록 기업 동일 비중 단순평균 · 생산량/시장점유율 가중평균 아님',
        )


def score_view(result, key='worst'):
    if key not in result['process_views']:
        raise ValueError('등록되지 않은 점수 보기입니다.')
    return result['process_views'][key]


def period_bottleneck(view):
    values = [min((value for p,value in row.items() if p!='day' and value is not None), default=None) for row in view['timeline']]
    return sum(values)/len(values) if values and all(v is not None for v in values) else None
