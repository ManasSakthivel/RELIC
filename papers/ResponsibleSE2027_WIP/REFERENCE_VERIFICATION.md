# Reference verification (final)

Method: Crossref REST API and arXiv API, checked 2026-11-21. Each title, author list, venue and year was compared with the bibliography. Abstracts are not available for these records in Crossref, so claims in the paper were narrowed to what the title and record establish.

| Key | Verified record | Claim it supports in the paper | Status |
|---|---|---|---|
| barr2015 | Barr, Harman, McMinn, Shahbaz, Yoo. The Oracle Problem in Software Testing: A Survey. IEEE TSE, 2015. doi:10.1109/TSE.2014.2372785 | Oracle problem is a standing challenge | Record verified |
| staats2011 | Staats, Whalen, Heimdahl. Programs, tests, and oracles. ICSE 2011. doi:10.1145/1985793.1985847 | Test oracles studied as a foundation of testing | Record verified |
| staats2012 | Staats, Gay, Heimdahl. Automated oracle creation support, or: How I learned to stop worrying about fault propagation and love mutation testing. ICSE 2012. doi:10.1109/ICSE.2012.6227132 | Oracle creation based on mutation testing | Record verified (three authors) |
| papadakis2016 | Papadakis, Henard, Harman, Jia, Le Traon. Threats to the validity of mutation-based test assessment. ISSTA 2016. doi:10.1145/2931037.2931040 | Threats to mutation-based assessment catalogued | Record verified |
| herzig2013 | Herzig, Just, Zeller. It's not a bug, it's a feature: How misclassification impacts bug prediction. ICSE 2013. doi:10.1109/ICSE.2013.6606585 | Misclassification affects bug prediction (title) | Record verified |
| northcutt2021 | Northcutt, Athalye, Mueller. Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks. arXiv:2103.14749, 2021 | Label errors in test sets (title) | arXiv record verified; the venue (NeurIPS) was not verified, so cited as arXiv |
| allamanis2019 | Allamanis. The Adverse Effects of Code Duplication in Machine Learning Models of Code. Onward! 2019. doi:10.1145/3359591.3359735 | Duplicated code can inflate results | Record verified (title) |
| kapoor2023 | Kapoor, Narayanan. Leakage and the reproducibility crisis in machine-learning-based science. Patterns, 2023. doi:10.1016/j.patter.2023.100804 | Leakage through shared data is a reproducibility concern (general, not code-specific) | Record verified (title) |
| gebru2021 | Gebru, Morgenstern, Vecchione, Vaughan, Wallach, Daumé III, Crawford. Datasheets for datasets. CACM, 2021. doi:10.1145/3458723 | Documenting data provenance and curation | Record verified (title) |
| jacobs2021 | Jacobs, Wallach. Measurement and Fairness. FAccT 2021. doi:10.1145/3442188.3445901 | Measurement validity argued as a fairness concern | Record verified (title) |
| schieferdecker2019 | Schieferdecker. Responsible Software Engineering. In: The Future of Software Quality Assurance, Springer, 2019, pp. 137–146. doi:10.1007/978-3-030-29509-7_11 | Responsible SE introduced as a topic | Record verified (title) |
| zhang2025 | Zhang, Rauf, Bandara. To Protect & Serve: Enabling Responsible Software Engineering for Online Safety. 1st Int. Workshop on Responsible SE, ACM, 2025, pp. 1–6. doi:10.1145/3711919.3728676 | Responsible SE applied to online safety | Record verified (title) |
| jackson1994 | Jackson, Ladd. Semantic Diff: A Tool for Summarizing the Effects of Modifications. ICSM 1994. doi:10.1109/icsm.1994.336770 | Semantic differencing predates this work | Record verified (title) |
| cameron2008 | Cameron, Gelbach, Miller. Bootstrap-Based Improvements for Inference with Clustered Errors. REStat 2008. doi:10.1162/rest.90.3.414 | Clustered-error inference can require bootstrap improvements (title) | Record verified (title) |

Summary: 14 entries, all cited in the paper; 13 with DOI, one arXiv. Record checks (Crossref and arXiv) were run in an earlier session; in this pass the DOIs were compared with references.bib, not re-queried. Every entry's record was checked; the claims were checked at title level only, because full texts and abstracts were not available to this check. A full-text read of the sources is recommended before camera-ready.

Rejected earlier candidates (not in the bibliography): a remembered DOI (10.1145/3510003.3510209) resolves to an unrelated ICSE 2022 paper; a remembered legacy-systems DOI (10.1109/52.773182) returns 404; Raji et al. 2021 was not found in Crossref and the arXiv lookup was rate-limited.
