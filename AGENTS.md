This project will create an interactive analytical board, not production software.



Data quality is the highest priority for this project. 

Keep in mind that the source (Open Food Facts) is rich but there are numerous inconsistencies and errors due to its open-source nature. 



Before editing:

1. Read README.md and docs/ONBOARDING.md.
2. Understand the role of the requested script in the pipeline.
3. Do not redesign adjacent scripts unless explicitly asked.

Working rules:

* Work on ONE script/task at a time.
* Prefer minimal, explainable changes over refactoring.
* Do not change research definitions without explicit approval.
* Preserve intermediate CSVs and provenance.
* NULL is not zero.
* Never silently impute values.
* SEC-derived conclusions must preserve accession/source evidence.
* Do not delete or retire scripts unless explicitly requested.
* When proposing retirement, explain why first.
* Before editing, state:
a) what is wrong,
b) what you propose changing,
c) what will remain unchanged.
* After editing, show the diff and validation performed.
* Do not proceed to the next pipeline step automatically.

\## Change-control rule



DEFAULT MODE IS REVIEW ONLY.



Unless I explicitly say "IMPLEMENT", do not modify, rename, move, delete,

retire, or create any project file.



For every script review:



1\. Read the target script and relevant documentation.

2\. Identify its inputs, outputs, and all upstream/downstream references.

3\. Explain:

&#x20;  - what is correct,

&#x20;  - what should change,

&#x20;  - why,

&#x20;  - which other files would be affected.

4\. Propose the smallest change.

5\. STOP and wait for approval.



Only after Julia explicitly says IMPLEMENT may you edit files.



Special rule for retirement/deletion/renaming:

Before proposing retirement of any script, search the repository for every

reference to its filename, outputs, functions, and generated files.

Report those dependencies first. Never retire/delete/move it automatically.



Work on one primary script at a time.

Do not proactively refactor adjacent scripts.



