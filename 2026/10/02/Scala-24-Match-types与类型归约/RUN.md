# Chapter 24 rerun

Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / JDK 21.0.11-amzn.

From repository root, set SCALA_LAB_JAVA_HOME to a JDK 21 installation, then:

```bash
python3 examples/scala-lab/run.py chapter 24 --run-id local-ch24
python3 examples/scala-lab/run.py negative 24 --run-id local-ch24
```

Source: examples/scala-lab/snippets/24/Chapter24.scala.
Rejected cases: examples/scala-lab/negative/24/ (each case.json requires nonzero exit and all diagnostic regexes).

Evidence: examples/scala-lab/evidence/20261002-ch24/24.json and 24.log.
Negative evidence: examples/scala-lab/evidence/20261002-ch24-r2/negative-24-*.json and .log.

The first negative attempt preserved a real compiler rejection but the regex used cannot instead of could not. r2 verifies the corrected semantic wording.
