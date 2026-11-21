# ResponsibleSE 2027 scope audit

Sources read on 2026-11-21: CFP at https://sites.google.com/view/responsiblese2027/call-for-papers and About page; Researchr workshop page; HotCRP sign-in page.

## Category
Short paper, Work-in-progress with preliminary results. The CFP lists "Work-in-progress papers (with/without preliminary results)" under short papers (4–6 pages). This paper reports completed counting and a sensitivity analysis on one benchmark, with preliminary evidence (no independent labels, no held-out data). It is a WIP paper in that sense.

## Relevant CFP topics and how the paper touches them
| CFP topic | How the paper engages it | Strength |
|---|---|---|
| Data-centric responsibility: data collection, curation, labeling, retention, deletion in software pipelines | Benchmark labels are the data; duplicates, identical files and conflicting labels are curation failures | Strong |
| Tools and infrastructures that embed responsibility checks in everyday work | The framework proposes checks (byte-level no-op, duplicate and label-conflict checks, boundary declaration) to run before a tool's evidence is used | Moderate; checks are proposed, not implemented as tooling |
| Responsibility as a continuous lifecycle practice | Evaluation evidence is part of the maintenance loop; the paper concerns the evidence step | Moderate |
| Governance structures and new roles | Not addressed | None |
| Incident response, accountability and repair | Not addressed; no incident is claimed | None |

## Why this belongs at ResponsibleSE rather than a testing workshop
A testing workshop would ask whether RELIC detects more changes. This paper asks whether the evidence that tells maintainers "no change" can be trusted, who answers for that evidence, and which checks the evaluation owes them. The stakeholders (maintainers, modernisation teams, test engineers, tool developers) and the consequences (missed behaviour changes, unnecessary review) are stated in Section 2.

## Remaining scope risks
1. The paper is still largely an empirical accounting. A reviewer may judge the responsibility argument as framing. Mitigation: the framework (Table 3) is the responsibility contribution and is tied to artifacts.
2. The framework is not validated; two of five dimensions are incomplete. Disclosed.
3. The domain (JCL) is niche. Mitigation: the framework is written for any change-detection tool.
4. Strength of contribution: the observable-scope concern is established in the testing literature. The paper claims only the accounting and the framework.
