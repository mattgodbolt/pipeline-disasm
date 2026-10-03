# Baron feedback

What working on PIPELINE has turned up about baron, in one place. Filed
issues say they're from Claude acting for Matt. Symbol-dump points are in
[symbols-feedback.md](symbols-feedback.md).

## Filed

| Issue | What | Why it matters here |
|---|---|---|
| [baron#12](https://github.com/waitingforvsync/baron/issues/12) | A way to put a byte by value into a BASIC line, or to interleave EQUB'd records with a BASIC block | MENU and MISSION hide control and teletext codes in lines; `src/mission.6502` has to carry raw bytes, which aren't valid UTF-8 |
| [baron#13](https://github.com/waitingforvsync/baron/issues/13) | `a..b..b` (limit equal to the second element) fails with "Argument out of domain" | Hit building tables in the Level Designer |
| [baron#10](https://github.com/waitingforvsync/baron/issues/10) (filed from another session) | FUNCTION frames collide when called at the same offset in two files of one assembly | We call FUNCTIONs from several includes; `make verify` would catch a wrong byte |

## Asked for, not filed

- **Character literals** (`'A'`). Wanted by four of the five pieces
  independently. `CODES("A")[0]` works, and `osconst.6502inc` has
  `ascii("A")` for it; the pieces should use that rather than their own
  (`asc()` in the Level Designer, raw hex with a comment in the game).
- **Generating bytes from other bytes in the build** (a section transform, or
  reading assembled bytes back): PL's encrypted image could then come from
  its decrypted source instead of a checked-in binary plus a test. Same for
  TITLE's packed picture.
- **List equality in ASSERT**: `SHAPE(x) == {...}` gives "Operand is not a
  number".
- **A label on an instruction's operand byte**: the game BITs against other
  instructions' operands as masks. `label + 1` does the job.
- **Line continuation**: list literals already span lines, which covers the
  long tables this was wanted for.
