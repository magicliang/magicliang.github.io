# Chapter 31 rerun
Status: LAB_VERIFIED. Scala3.3.7 / CLI1.9.1 / JDK21.0.11.
```bash
python3 examples/scala-lab/run.py chapter 31 --run-id local-ch31
```
Set SCALA_LAB_JAVA_HOME to JDK21. Source: examples/scala-lab/snippets/31/Chapter31.scala.
Evidence: examples/scala-lab/evidence/20261002-ch31/31.json and 31.log.
Assertions distinguish two tasks started before release, delayed second creation in flatMap, ordinary failure propagation/recovery, callback pool prefix, and executor termination. Concrete worker numbering is nondeterministic. Gate timeouts prevent hangs and are not a latency benchmark.

