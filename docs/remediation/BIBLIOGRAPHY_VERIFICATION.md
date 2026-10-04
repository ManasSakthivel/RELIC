# Bibliography Verification (October 2026)

All 36 entries of the v1 bibliography (`paper/archive/v1/` used `paper/references.bib`)
were checked against Crossref (title similarity, first author, year) and, where
Crossref had no match, by web search. Results:

## Not found — removed from the manuscript (possibly fabricated or mis-attributed)

| Key | Entry as written | Finding |
|---|---|---|
| `klaedtke2021mining` | Klaedtke, Zalinescu, Traytel. *Mining Behavioral Contracts from Execution Traces*. ISSTA 2021 | no such paper found |
| `pessoa2022behavioral` | Pessoa et al. *Behavioral Semantic Differencing of COBOL Programs*. ICSME 2022 | no such paper found; the related ICSME 2022 work is Deknop, Fabry, Mens, Zaytsev, *Generating Customised Control Flow Graphs for Legacy Languages with Semi-Parsing* |
| `reraidy2001architecture` | Reraidy, Merlo, Antoniol. *Architecture Extraction for COBOL Systems*. WCRE 2001 | no such paper found |
| `barnett2003runtime` | Barnett, Schulte. *Runtime Verification Is LTL and Büchi Automata* (2003) | no such paper found |
| `mariani2012behavioural` | Mariani, Pezzè. *Behavioral Pattern Mining for Web Applications* (2012) | no such paper found |
| `xie2003inferring` | Xie, Notkin. *Inferring Likely Data Invariants for Programs Under Test* (2003) | no such paper found (Xie & Notkin's 2003 WODA paper has a different title) |
| `tonella2003dynamic` | Tonella et al. *Using a Keyword-Based Approach for the Categorisation of Web Applications* (2003) | no such paper found |
| `lo2006mining` | Lo. *Mining Iterative-Convergent Control Flow Patterns from Execution Traces* (2006) | title not found; the closest real work is Lo, Khoo, Liu, *Efficient Mining of Iterative Patterns for Software Specification Discovery*, KDD 2007 |

## Not matched by Crossref, plausibly real, not re-verified in detail — not cited

`ammons2002mining` (POPL 2002), `tip1995survey`, `harel1985reactive`,
`comelladorda2000survey` (title differs from the SEI report *A Survey of Legacy
System Modernization Approaches*), `sneed2008cobol`, `ulrich2010transformation`,
`white2023prompt`, `hou2024llm4se`, `livshits2005security`, `pacheco2007randoop`.

## Verified by Crossref (title, first author, year match)

`meyer1992applying`, `ernst2007daikon`, `flanagan2001houdini`, `lorenzoli2008automatic`,
`leucker2009brief`, `angluin1987learning`, `clarke1986automatic`, `dwyer1999patterns`,
`lahiri2012regression`, `felsing2014automating`, `naik2006race`, `reps1997profiling`,
`mens2004survey`, `mens2005challenges`, `legoues2012systematic`, `fan2023llm`,
`ling2023domain`, `leavens1990behavioral` (Crossref lists Liskov first; actual
authors Liskov & Wing — the entry's author field should be corrected before use).

The new manuscript cites only works in the verified list, with their DOIs, in
`paper/references.bib`. The v1 bibliography is preserved as
`paper/archive/v1/references_v1.bib`.
