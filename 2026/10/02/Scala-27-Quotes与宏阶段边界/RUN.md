# Chapter 27 rerun

Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / Corretto 21.0.11.

From repository root, set SCALA_LAB_JAVA_HOME to JDK 21, then:

```bash
python3 examples/scala-lab/run.py chapter 27 --run-id local-ch27
python3 examples/scala-lab/run.py negative 27 --run-id local-ch27
```

Source: examples/scala-lab/snippets/27/. Isolated negatives: examples/scala-lab/negative/27/; every case.json requires nonzero exit and all patterns matched.

Original positive command/exit/output: examples/scala-lab/evidence/20261002-ch27/27.json and 27.log.
Original negatives: examples/scala-lab/evidence/20261002-ch27-r2/negative-27-*.json and .log.

Extra macro consistency check (Scala CLI 1.9.1 on PATH):

```bash
scala-cli run examples/scala-lab/snippets/27 --server=false --scala 3.3.7 --jvm system --scalac-option -Xcheck-macros --main-class scalaexamples.Chapter27
```

JAVA_HOME must also point to JDK 21 for this direct invocation. Original exact Java/JAR command is in evidence/20261002-ch27/checked-macros.json and output in checked-macros.log. Positive checks include constant 10 and single evaluation; rejections cover bounds, dynamic input and illegal local cross-stage capture.
