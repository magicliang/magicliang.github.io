"""Fixed dimension/query set; downsampling loses burst information."""
import json, platform
low={(service,region,status) for service in range(4) for region in range(3) for status in range(5)}
high={(s,r,c,u) for s,r,c in low for u in range(1000)}
values=[1]*59+[101]
avg=sum(values)/len(values)
assert (len(low),len(high))==(60,60000)
assert avg<10 and max(values)>100
raw_samples=60000*86400//15*7
raw_bytes=raw_samples*16
retained=[day for day in range(15) if day>=15-7]
assert retained==list(range(8,15))
print(json.dumps(dict(python=platform.python_version(),base_series=len(low),high_cardinality_series=len(high),
 raw_samples_7d=raw_samples,raw_GB=raw_bytes/1e9,raw_max=max(values),
 negative_average_only=avg,queries=['max over minute','sum by region','lookup request log'],
 retained_day_buckets=retained,retention_interval="[8,15)",old_raw_query_available=7 in retained,pass_checks=True),indent=2))
