import argparse
from collections import Counter
import hashlib
import json


def shard(owner, hashed):
    return int.from_bytes(hashlib.sha256(str(owner).encode()).digest()[:8], "big") % 4 if hashed else owner // 25


def place(objects, hashed):
    result = [{} for _ in range(4)]
    for key, payload in objects.items():
        result[shard(key, hashed)][key] = payload
    return result


def migrate_collection(old, fault=None):
    current = [dict(content) for content in old]
    injected = False
    for origin, content in enumerate(old):
        for key, payload in content.items():
            target = shard(key, True)
            if origin == target:
                continue
            problem = fault if not injected else None
            injected = injected or problem is not None
            if problem != 'drop':
                current[target][key] = payload
            if problem != 'duplicate':
                del current[origin][key]
    return current


def verify_collection(current, original):
    seen = Counter(key for content in current for key in content)
    assert set(seen) == set(original), 'missing or unexpected migrated key'
    assert all(count == 1 for count in seen.values()), 'duplicate migrated key'
    for number, content in enumerate(current):
        for key, payload in content.items():
            assert shard(key, True) == number, 'wrong destination'
            assert original[key] == payload, 'payload changed'


def run(expect_hotspot_removed, migration_fault=None):
    owners = list(range(100))
    loads = {}
    for hashed in (False, True):
        counts = [0] * 4
        for owner in owners:
            counts[shard(owner, hashed)] += 1
        hot_counts = list(counts)
        hot_counts[shard(42, hashed)] += 700
        loads["hash" if hashed else "range"] = {"objects": counts, "requests": hot_counts}
        assert sum(counts) == 100 and sum(hot_counts) == 800
        assert max(hot_counts) >= 700
    moved = [owner for owner in owners if shard(owner, False) != shard(owner, True)]
    original = {owner: f'payload-{owner}' for owner in owners}
    current = migrate_collection(place(original, False), migration_fault)
    verify_collection(current, original)
    print(json.dumps({"shards": loads, "migration_owner_count": len(moved),
                      "migrated_objects": sum(map(len, current)), "migration_complete": True,
                      "hot_owner_requests": 701, "owner_is_routing_unit": True}, sort_keys=True))
    if expect_hotspot_removed:
        assert max(loads["hash"]["requests"]) <= 200, "hashing owners does not split one hot owner"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fixed range/hash assignment and indivisible-owner hotspot model")
    parser.add_argument("--expect-hotspot-removed", action="store_true")
    parser.add_argument("--migration-fault", choices=('drop', 'duplicate'))
    args = parser.parse_args()
    try:
        run(args.expect_hotspot_removed, args.migration_fault)
    except AssertionError as error:
        print(f"INVARIANT_FAILED: {error}")
        raise SystemExit(2)
