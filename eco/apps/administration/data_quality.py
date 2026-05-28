"""
Межмодульные проверки качества данных для администратора предприятия.
"""

from __future__ import annotations

from collections import defaultdict

SEVERITY_RANK = {"ok": 0, "warning": 1, "problem": 2}


def load_cross_module_indexes(service):
    movements = service.movements_list()
    measurements = service.measurements_list()
    batches = service.batches_list()

    movement_count_by_org_waste = defaultdict(int)
    movement_volume_by_org_waste = defaultdict(float)
    movement_count_by_org = defaultdict(int)
    for row in movements:
        key = (row.organization.pk, row.waste_type.pk)
        movement_count_by_org_waste[key] += 1
        movement_volume_by_org_waste[key] += float(row.volume)
        movement_count_by_org[row.organization.pk] += 1

    measurement_count_by_org = defaultdict(int)
    for row in measurements:
        measurement_count_by_org[row.organization.pk] += 1

    batches_by_org = defaultdict(list)
    for batch in batches:
        org_id = batch.organization.pk if batch.organization else 0
        batches_by_org[org_id].append(batch)

    return {
        "movements": movements,
        "measurements": measurements,
        "batches": batches,
        "movement_count_by_org_waste": movement_count_by_org_waste,
        "movement_volume_by_org_waste": movement_volume_by_org_waste,
        "movement_count_by_org": movement_count_by_org,
        "measurement_count_by_org": measurement_count_by_org,
        "batches_by_org": batches_by_org,
    }


def compute_batch_integrity(batch, indexes):
    org_id = batch.organization.pk if batch.organization else 0
    waste_id = batch.waste_type.pk if batch.waste_type else 0

    ops_count = indexes["movement_count_by_org_waste"][(org_id, waste_id)]
    measures_count = indexes["measurement_count_by_org"][org_id]
    ops_volume = indexes["movement_volume_by_org_waste"][(org_id, waste_id)]
    batch_volume = float(batch.volume_tons)

    issues = []
    if ops_count == 0:
        issues.append("нет операций по этой партии отходов")
    if measures_count == 0:
        issues.append("нет измерений по организации")
    if batch_volume > 0 and ops_volume < batch_volume * 0.5:
        issues.append("объём операций заметно ниже объёма партии")

    passed = 3 - len(issues)
    score = int((passed / 3) * 100)

    severity = "ok"
    if len(issues) >= 2:
        severity = "problem"
    elif len(issues) == 1:
        severity = "warning"

    return {
        "severity": severity,
        "score": score,
        "issues": issues,
        "ops_count": ops_count,
        "measures_count": measures_count,
    }


def attach_batch_integrity_checks(batches, indexes):
    totals = {"ok": 0, "warning": 0, "problem": 0}
    for batch in batches:
        check = compute_batch_integrity(batch, indexes)
        batch.integrity_check = check
        totals[check["severity"]] += 1
    return totals


def compute_organization_summary(org, indexes):
    org_id = org.pk
    org_batches = indexes["batches_by_org"][org_id]
    batch_count = len(org_batches)
    total_volume = sum((float(b.volume_tons) for b in org_batches), 0.0)
    ops_count = indexes["movement_count_by_org"][org_id]
    measures_count = indexes["measurement_count_by_org"][org_id]

    batch_problems = 0
    batch_warnings = 0
    for batch in org_batches:
        check = compute_batch_integrity(batch, indexes)
        batch.integrity_check = check
        if check["severity"] == "problem":
            batch_problems += 1
        elif check["severity"] == "warning":
            batch_warnings += 1

    issues = []
    if batch_count == 0:
        issues.append("нет партий отходов")
    if measures_count == 0:
        issues.append("нет измерений")
    if ops_count == 0:
        issues.append("нет операций")
    if not (org.address.strip() and org.email.strip() and org.phone.strip()):
        issues.append("неполные реквизиты")
    if batch_problems > 0:
        issues.append(f"проблемных партий: {batch_problems}")

    severity = "ok"
    if batch_problems > 0 or len(issues) >= 3:
        severity = "problem"
    elif batch_warnings > 0 or len(issues) >= 1:
        severity = "warning"

    score = max(0, min(100, 100 - len(issues) * 20 - batch_problems * 15))

    return {
        "batch_count": batch_count,
        "total_volume": total_volume,
        "ops_count": ops_count,
        "measures_count": measures_count,
        "batch_problems": batch_problems,
        "batch_warnings": batch_warnings,
        "severity": severity,
        "score": score,
        "issues": issues,
        "requisites_complete": bool(
            org.address.strip() and org.email.strip() and org.phone.strip()
        ),
    }


def organization_matches_filter(summary, filter_key: str) -> bool:
    if not filter_key:
        return True
    if filter_key == "problems":
        return summary["severity"] != "ok"
    if filter_key == "no_batches":
        return summary["batch_count"] == 0
    if filter_key == "no_measurements":
        return summary["measures_count"] == 0
    if filter_key == "incomplete_requisites":
        return not summary["requisites_complete"]
    return True
