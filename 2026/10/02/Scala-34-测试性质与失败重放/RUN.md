# Chapter 34 rerun
Status: LAB_VERIFIED. Scala3.3.7 / CLI1.9.1 / JDK21.0.11 / MUnit1.0.4 / ScalaCheck1.18.1.
Set SCALA_LAB_JAVA_HOME to JDK21; module supports SCALA_LAB_CLI_JAR.
```bash
python3 examples/scala-lab/run.py chapter 34 --run-id local-ch34
python3 examples/scala-lab/modules/34/run.py --run-id local-ch34-module
```
Source: examples/scala-lab/snippets/34 and modules/34.
Evidence: examples/scala-lab/evidence/20261002-ch34/ and final framework run 20261002-ch34-module-r3/.
munit.json/log: two actual successful MUnit cases. properties.json/log: seed20261002, one worker, 300 successes, original12 -> minimal0 with4 shrinks and structured replay match. minimal-regression-fails.json/log: actual nonzero MUnit failure None versus Some(0).
Initial generator is1..100; the default Int shrinker reaches0 outside this initial interval, which remains valid for the actual integer domain. No formal proof is claimed. Earlier r1/r2 logs preserve harness failures and are not final evidence.

