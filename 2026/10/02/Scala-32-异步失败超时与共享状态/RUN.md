# Chapter 32 rerun
Status: LAB_VERIFIED. Scala3.3.7 / CLI1.9.1 / Corretto21.0.11.
Set SCALA_LAB_JAVA_HOME to JDK21.
```bash
python3 examples/scala-lab/run.py chapter 32 --run-id local-ch32
```
Source: examples/scala-lab/snippets/32/Chapter32.scala.
Final evidence: examples/scala-lab/evidence/20261002-ch32-r2/32.json and 32.log.
Checks distinguish deadline Promise failure from Await protection using message, prove original task continues after timeout, force lost update with a barrier, compare atomic increment, and terminate both executors. No cancellation protocol or performance benchmark is claimed.

