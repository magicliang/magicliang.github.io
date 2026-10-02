# Chapter 33 rerun
Status: LAB_VERIFIED. Scala3.3.7 / CLI1.9.1 / Corretto21.0.11.
Set SCALA_LAB_JAVA_HOME to JDK21.
```bash
python3 examples/scala-lab/run.py chapter 33 --run-id local-ch33
```
Source: examples/scala-lab/snippets/33/Chapter33.scala.
Final evidence: examples/scala-lab/evidence/20261002-ch33-r2/33.json and 33.log.
Checks cover normal/body-only/close-only/both-failure and suppressed exception, reverse Manager release, real file acquire/use/close/consume escaping iterator, materialized data, asynchronous early close and corrected task-local scope. The actual file close-failure path is not injected; close failures use the explicit test resource. Temporary file deletion and executor termination are checked.

