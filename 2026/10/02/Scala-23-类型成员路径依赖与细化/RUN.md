# Chapter 23 rerun

Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / JDK 21.0.11-amzn.

From repository root, set SCALA_LAB_JAVA_HOME to a JDK 21 installation, then:

```bash
python3 examples/scala-lab/run.py chapter 23 --run-id local-ch23
python3 examples/scala-lab/run.py negative 23 --run-id local-ch23
```

Source: examples/scala-lab/snippets/23/Chapter23.scala.
Rejected cases: examples/scala-lab/negative/23/ (each case.json requires nonzero exit and all diagnostic regexes).

Evidence: examples/scala-lab/evidence/20261002-ch23-r2/23.json and 23.log.
Negative evidence: examples/scala-lab/evidence/20261002-ch23-r2/negative-23-*.json and .log.

Normal cases cover per-owner keys, dependent method/function results, and two explicit Int refinements sharing the same type. Rejections cover wrong owner and missing refinement.
