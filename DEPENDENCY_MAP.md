# DEPENDENCY_MAP.md — Google Apps Script `require()` dependency map

Built by grepping literal `require\(` lines across `reference/*.gs` and
`reference/gsheet/*.gs` on 2026-07-27 (not from memory — see raw grep output
below the table). Scope: originally the 8 files bundled in `BUNDLE_gsheet.md`
(bundle file now deprecated as of Session F.4 — see note at end of file) plus
`GS_DriveWalker.gs` (Session F.2), `GS_SheetExport.gs`/`GS_Pipeline.gs`
(Session F.4).

## Why this file exists

Session C hit a real bug: `GS_AlignmentBuilder` was pushed to the clasp folder
(`D:\MyClasp_SMT_DEMO\`) without `FPMath`/`WCB` also present there, because
nobody had a map of what each file actually needs. This table exists so that
before pushing any subset of files to a clasp project, you can check every
dependency is included.

## Important: `require()` only matters for local Node testing, not for Apps Script itself

Every `require(...)` line below is guarded by
`if (typeof X === 'undefined' && typeof require !== 'undefined')`. In the
Google Apps Script runtime, `require` is `undefined`, so these lines are
skipped entirely — Apps Script instead shares one flat global scope across
**every** `.gs`/`.js` file in the same project (no folders, no imports). The
relative paths (`../FPMath.gs`, `./GS_Alignment.gs`) only resolve when running
`node reference/gsheet/smoke_test.js` locally.

Practical consequence for clasp pushes: **the folder structure in this repo
(`reference/` vs `reference/gsheet/`) does not exist in
`D:\MyClasp_SMT_DEMO\`** — everything is pushed flat (see e.g. `FPMath.js`,
`GS_Alignment.js` sitting side-by-side at the top level, confirmed
2026-07-27). The table below still tells you *which files* must be present in
the same Apps Script project; it does not imply any folder layout there.

## Dependency table

| File (repo path) | `require()` targets found | Resolved path (relative to file's own folder) | Must also be present in clasp project |
|---|---|---|---|
| `reference/FPMath.gs` | *(none)* | — | — |
| `reference/WCB.gs` | `./FPMath.gs` | `reference/FPMath.gs` | FPMath |
| `reference/gsheet/GS_Alignment.gs` | `../FPMath.gs`, `../WCB.gs` | `reference/FPMath.gs`, `reference/WCB.gs` | FPMath, WCB |
| `reference/gsheet/GS_AlignmentBuilder.gs` | `../FPMath.gs`, `../WCB.gs`, `./GS_Alignment.gs` | `reference/FPMath.gs`, `reference/WCB.gs`, `reference/gsheet/GS_Alignment.gs` | FPMath, WCB, GS_Alignment |
| `reference/gsheet/GS_TableSplitter.gs` | *(none)* | — | — |
| `reference/gsheet/GS_PiTableParser.gs` | *(none)* | — | — |
| `reference/gsheet/GS_ElementTable.gs` | `../FPMath.gs` | `reference/FPMath.gs` | FPMath |
| `reference/gsheet/GS_CrossCheck.gs` | `../FPMath.gs`, `../WCB.gs`, `./GS_Alignment.gs` | `reference/FPMath.gs`, `reference/WCB.gs`, `reference/gsheet/GS_Alignment.gs` | FPMath, WCB, GS_Alignment |
| `reference/gsheet/GS_DriveWalker.gs` | *(none — references `GS_ElementTable.HEADER`/`GS_CrossCheck.*_HEADER` directly as globals, not via `require()`; Apps-Script-only, no Node smoke test possible since it calls `DriveApp`/`SpreadsheetApp`)* | — | GS_ElementTable, GS_CrossCheck |
| `reference/gsheet/GS_SheetExport.gs` | *(none — references `GS_ElementTable.HEADER`/`elementsToRows` and `GS_CrossCheck.*_HEADER`/`checkPoints`/`checkPiCurves`/`*ToRows` directly as globals, not via `require()`; Apps-Script-only, no Node smoke test possible since it calls `SpreadsheetApp`)* | — | GS_ElementTable, GS_CrossCheck |
| `reference/gsheet/GS_Pipeline.gs` | *(none — calls `GS_TableSplitter.splitMixedAlignmentTable`/`GS_PiTableParser.parsePiTable`/`GS_AlignmentBuilder.buildFromPI` and `exportElementsToSheet`/`exportCrossCheckToSheet`/`exportIssuesToSheet` directly as globals, not via `require()`; Apps-Script-only, no Node smoke test possible since it calls `SpreadsheetApp`)* | — | GS_TableSplitter, GS_PiTableParser, GS_AlignmentBuilder, GS_SheetExport |

Transitive closure (if you push file X, you need everything in its row plus
that dependency's own row, recursively):

- **FPMath** — no dependencies. Always safe alone.
- **WCB** — needs FPMath.
- **GS_Alignment** — needs FPMath, WCB.
- **GS_AlignmentBuilder** — needs FPMath, WCB, GS_Alignment.
- **GS_TableSplitter** — no dependencies. Always safe alone.
- **GS_PiTableParser** — no dependencies. Always safe alone.
- **GS_ElementTable** — needs FPMath.
- **GS_CrossCheck** — needs FPMath, WCB, GS_Alignment.
- **GS_DriveWalker** — needs GS_ElementTable, GS_CrossCheck (and transitively FPMath, WCB, GS_Alignment).
- **GS_SheetExport** — needs GS_ElementTable, GS_CrossCheck (and transitively FPMath, WCB, GS_Alignment). New in Session F.4 — moved from TestDrive.js.
- **GS_Pipeline** — needs GS_TableSplitter, GS_PiTableParser, GS_AlignmentBuilder, GS_SheetExport (and transitively FPMath, WCB, GS_Alignment, GS_ElementTable, GS_CrossCheck). New in Session F.4 — the production orchestrator behind the web app's "Calculate" button.

So a full working push (e.g. the `SMT_COGO_DEMO` / `HOR-ORR-04` pipeline) needs
all 8 files together — there is no smaller subset that supports
`buildFromPI()` + `GS_ElementTable` + `GS_CrossCheck` at once. This matches
the 8 files already confirmed present in `D:\MyClasp_SMT_DEMO\` as of
2026-07-27 (`FPMath.js`, `WCB.js`, `GS_Alignment.js`, `GS_AlignmentBuilder.js`,
`GS_TableSplitter.js`, `GS_PiTableParser.js`, `GS_ElementTable.js`,
`GS_CrossCheck.js`, plus `TestDrive.js`, `code.js`, `appsscript.json`).
GS_DriveWalker.gs is a 9th file needed only for the Drive-walking cascade
feature (Session F.2+) — the core split→parse→build→export pipeline above
doesn't need it.

GS_SheetExport.gs and GS_Pipeline.gs (Session F.4) add 2 more files needed
specifically for the web app's production "Calculate" button — the
orchestrator (`runFullPipeline`) and the sheet-write helpers moved out of
`TestDrive.js`. As of Session F.4's clasp push (2026-07-29) the clasp folder
has 15 files total (11 .gs/.js library files + code.js + appsscript.json +
Index.html + TestDrive.js).

**Note (2026-07-29): `BUNDLE_gsheet.md`/`BUNDLE_python_core.md` are
deprecated as of this session.** Going forward, attach the real `.gs`/`.py`
files that changed for a given task instead of maintaining a hand-built
bundle — bundles go stale silently (this map itself was one commit behind
until now) and get auto-loaded into context in full regardless of whether
a session needs them, costing tokens for no benefit. This file
(`DEPENDENCY_MAP.md`) and `PROJECT_STATE.md`/`CLAUDE.md` stay as living docs
since they're status/analysis, not copies of source.

## Raw grep output (source of truth for the table above)

Command: `grep -n "require\(" reference/*.gs reference/gsheet/*.gs` (restricted
to the 8 bundled files below; `smoke_test.js` and the oracle-only files
`reference/Alignment.gs` / `reference/AlignmentBuilder.gs` / `reference/Surface3D.gs`
are outside this map's scope since they are not part of the gsheet bundle).

```
reference/WCB.gs:19:  var FPMath = require('./FPMath.gs');
reference/gsheet/GS_Alignment.gs:32:if (typeof FPMath === 'undefined' && typeof require !== 'undefined') { var FPMath = require('../FPMath.gs'); }
reference/gsheet/GS_Alignment.gs:33:if (typeof WCB === 'undefined' && typeof require !== 'undefined')    { var WCB = require('../WCB.gs'); }
reference/gsheet/GS_AlignmentBuilder.gs:40:if (typeof FPMath === 'undefined' && typeof require !== 'undefined')       { var FPMath = require('../FPMath.gs'); }
reference/gsheet/GS_AlignmentBuilder.gs:41:if (typeof WCB === 'undefined' && typeof require !== 'undefined')          { var WCB = require('../WCB.gs'); }
reference/gsheet/GS_AlignmentBuilder.gs:42:if (typeof GS_Alignment === 'undefined' && typeof require !== 'undefined') { var GS_Alignment = require('./GS_Alignment.gs'); }
reference/gsheet/GS_CrossCheck.gs:41:if (typeof FPMath === 'undefined' && typeof require !== 'undefined')       { var FPMath = require('../FPMath.gs'); }
reference/gsheet/GS_CrossCheck.gs:42:if (typeof WCB === 'undefined' && typeof require !== 'undefined')          { var WCB = require('../WCB.gs'); }
reference/gsheet/GS_CrossCheck.gs:43:if (typeof GS_Alignment === 'undefined' && typeof require !== 'undefined') { var GS_Alignment = require('./GS_Alignment.gs'); }
reference/gsheet/GS_ElementTable.gs:14:if (typeof FPMath === 'undefined' && typeof require !== 'undefined') { var FPMath = require('../FPMath.gs'); }
```

(No `require(` matches in `reference/FPMath.gs`, `reference/gsheet/GS_TableSplitter.gs`,
`reference/gsheet/GS_PiTableParser.gs` — confirmed by the same grep returning
no hits for those three files.)
