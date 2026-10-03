"""Teaching capacity arithmetic; this script does not perform timed sessions."""
import json
import platform

agenda = [5, 8, 12, 15, 5]
assert sum(agenda) == 45
cases = [
    dict(name='shortlink', base_requests_per_sec=2000, peak_requests_per_sec=20000,
         work_per_request=1, capacity_per_sec=5000, capacity_unit='authoritative reads'),
    dict(name='dispatch', base_requests_per_sec=100, peak_requests_per_sec=1000,
         work_per_request=1, capacity_per_sec=300, capacity_unit='matching decisions'),
    dict(name='tickets', base_requests_per_sec=500, peak_requests_per_sec=5000,
         work_per_request=4, capacity_per_sec=800, capacity_unit='local commits',
         conversion_fraction=1, protocol='hold, authorization intent, pin/capture intent, sale ledger'),
]
for case in cases:
    case['base_work_per_sec'] = case['base_requests_per_sec'] * case['work_per_request']
    case['peak_work_per_sec'] = case['peak_requests_per_sec'] * case['work_per_request']
    case['baseline_capacity_exceeded'] = case['base_work_per_sec'] > case['capacity_per_sec']
    case['unchanged_peak_utilization'] = case['peak_work_per_sec'] / case['capacity_per_sec']
    assert case['peak_requests_per_sec'] == 10 * case['base_requests_per_sec']
    assert case['peak_work_per_sec'] > case['capacity_per_sec']

ticket_budget = dict(
    previous_two_commit_protocol_base_work=500 * 2,
    safety_fraction=0.8, admitted_holds_per_sec=int(800 * 0.8 / 4),
    admitted_commits_per_sec=int(800 * 0.8),
    reserved_commits_per_sec=800 - int(800 * 0.8),
    boundary='all admitted holds convert; four local commits; rejection, retries and recovery consume separate resources',
)
assert ticket_budget['admitted_holds_per_sec'] * 4 == ticket_budget['admitted_commits_per_sec']
print(json.dumps(dict(
    python=platform.python_version(), agenda_minutes=agenda,
    script_performs_actual_45min_sessions=False,
    capacities_are_teaching_assumptions=True, performance_slo_measured=False,
    cases=cases, ticket_budget=ticket_budget, pass_checks=True), indent=2))
