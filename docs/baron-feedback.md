# Baron feedback

What working on PIPELINE has turned up about baron, in one place. Filed
issues say they're from Claude acting for Matt. Symbol-dump points are in
[symbols-feedback.md](symbols-feedback.md).

## Filed

| Issue | What | Why it matters here | Status |
|---|---|---|---|
| [baron#12](https://github.com/waitingforvsync/baron/issues/12) | A way to put a byte by value into a BASIC line, or to interleave EQUB'd records with a BASIC block | MENU and MISSION hide control and teletext codes in lines; `src/mission.6502` has to carry raw bytes, which aren't valid UTF-8 | Open. Rich proposes `{ ... }` splices inside a BASIC line; we said it covers every line we write as bytes (2026-10-06) |
| [baron#13](https://github.com/waitingforvsync/baron/issues/13) | `a..b..b` (limit equal to the second element) fails with "Argument out of domain" | Hit building tables in the Level Designer | Fixed in 0.5 |
| [baron#10](https://github.com/waitingforvsync/baron/issues/10) (filed from another session) | FUNCTION frames collide when called at the same offset in two files of one assembly | We call FUNCTIONs from several includes; `make verify` would catch a wrong byte | Fixed in 0.5 |
| [baron#14](https://github.com/waitingforvsync/baron/issues/14) (filed for jsbeeb#1215) | Each instruction's address and the symbol its operand was written with | Lets jsbeeb name operands as the source did | Open; Rich proposes `--map`, with questions for the jsbeeb side |
| [baron#15](https://github.com/waitingforvsync/baron/issues/15) (filed for jsbeeb#1215) | Each symbol's kind, and the section a label was emitted in | Tells addresses (labels) from numbers, and overlapping programs apart | Done in 0.5 (dump format 2); `tests/test_symbols.py` reads it |

## Asked for, not filed

- **Character literals** (`'A'`): baron has them after all (Rich, 2026-10-04):
  `'A'` is 65, in expressions and operands alike. We missed them because the
  docs didn't mention them; 0.5's reference documents them, and `'` itself
  is written 39. Our `ascii()` FUNCTION, which stood in for them, is gone.
- **Generating bytes from other bytes in the build** (a section transform, or
  reading assembled bytes back): PL's encrypted image could then come from
  its decrypted source instead of a checked-in binary plus a test. Same for
  TITLE's packed picture.
- **List equality in ASSERT**: `SHAPE(x) == {...}` gives "Operand is not a
  number".
- **A label on an instruction's operand byte**: the game BITs against other
  instructions' operands as masks. `label + 1` does the job.
- **Line continuation**: list literals already span lines, which covers the
  long tables this was wanted for. Parentheses don't (`x = (1 +` newline
  `2)` is "Malformed expression"), so long expressions get wrapped in
  `FLATTEN({...})` or split into named steps.
- **Shadowing is silent**: a scope may bind a name its file already binds
  outside it, and the inner one wins without a word. We hit it once (a
  Graphics Designer label hid IO's `io_graphics`); `tests/test_symbols.py`
  now fails on it. An opt-in warning (`--warn 2`) would do the same job.
- **A file of FUNCTIONs can be INCLUDEd only once per program** ("Duplicate
  function arity"), while constants may be rebound to the same value. With
  no include guard, each program has to reach each include by exactly one
  path, which shapes how the includes nest.
- **A gotcha, not a bug**: `1..2..` steps by 1 (the second element sets the
  step), so every other element from 1 is `1..3..`.
