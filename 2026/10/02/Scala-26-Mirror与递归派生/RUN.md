# Chapter 26 rerun

Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / Corretto 21.0.11.

From repository root, set SCALA_LAB_JAVA_HOME to JDK 21, then:

```bash
python3 examples/scala-lab/run.py chapter 26 --run-id local-ch26
python3 examples/scala-lab/run.py negative 26 --run-id local-ch26
```

Source: examples/scala-lab/snippets/26/. Isolated negatives: examples/scala-lab/negative/26/; every case.json requires nonzero exit and all patterns matched.

Original positive command/exit/output: examples/scala-lab/evidence/20261002-ch26-r3/26.json and 26.log.
Original negatives: examples/scala-lab/evidence/20261002-ch26-r3/negative-26-*.json and .log.

Normal assertions: handwritten/product, added field, empty, nested, recursive sum, finite optional chain. Deliberate runtime counterexamples are caught: StackOverflowError for cyclic graph and NullPointerException for eager field initialization. Rejected cases: missing-field-instance, no-mirror, recursive-expansion. These are three distinct failure stages, not a production serialization library.
