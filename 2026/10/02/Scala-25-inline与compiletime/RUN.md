# Chapter 25 rerun

Status: LAB_VERIFIED. Scala 3.3.7 / Scala CLI 1.9.1 / Corretto 21.0.11.

From repository root, set SCALA_LAB_JAVA_HOME to JDK 21, then:

```bash
python3 examples/scala-lab/run.py chapter 25 --run-id local-ch25
python3 examples/scala-lab/run.py negative 25 --run-id local-ch25
```

Source: examples/scala-lab/snippets/25/. Isolated negatives: examples/scala-lab/negative/25/; every case.json requires nonzero exit and all patterns matched.

Original positive command/exit/output: examples/scala-lab/evidence/20261002-ch25/25.json and 25.log.
Original negatives: examples/scala-lab/evidence/20261002-ch25/negative-25-*.json and .log.

Bytecode reproduction after running the chapter:

```bash
"$SCALA_LAB_JAVA_HOME/bin/javap" -c -p examples/scala-lab/snippets/25/.scala-build/*/classes/main/scalaexamples/'Chapter25$.class'
```

Actual bytecode: evidence/20261002-ch25/javap.json and javap.log under examples/scala-lab. compiledConstant returns iconst_5; normal/inline arguments have one/two next$1 invocations respectively. This is not benchmark evidence.
