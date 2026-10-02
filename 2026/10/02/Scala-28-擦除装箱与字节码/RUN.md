# Chapter 28 rerun

Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / Corretto 21.0.11.

Set SCALA_LAB_JAVA_HOME to JDK 21 and run from the repository root:

```bash
python3 examples/scala-lab/run.py chapter 28 --run-id local-ch28
python3 examples/scala-lab/run.py negative 28 --run-id local-ch28
```

Source: examples/scala-lab/snippets/28/Chapter28.scala. Isolated rejections: negative/28/no-class-tag and erased-test. Evidence: examples/scala-lab/evidence/20261002-ch28-r2/28.json, 28.log, negative-28-*.json/.log, javap.json/.log.

After compiling, locate Chapter28$.class and Chapter28$TextProducer.class under snippets/28/.scala-build/ and use JDK 21 javap -c -p -s -v on the actual files. The recorded javap.json contains the exact two class paths checked. Observe Object and primitive descriptors, box/unbox call sites, bridge flags and invokedynamic; no allocation or latency measurement is claimed.

