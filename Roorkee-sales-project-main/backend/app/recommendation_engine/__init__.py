# Business Recommendation Engine (see PROJECT_SPEC.md Milestone 9).
#
# Rule-based, not ML/LLM-based: combines already-computed Health Scores,
# Purchase Predictions, and Analytics (regional/sales revenue trends) through
# configurable business rules to produce ranked, explainable recommendations
# for sales managers. Nothing here calls an LLM or trains a model.
#
# config.py                 - tunable rule thresholds and priority bands
# rules.py                  - the business rules themselves (signals -> Recommendation)
# priority_engine.py        - turns raw signals into a 0-100 urgency score + High/Medium/Low band
# recommendation_service.py - DB access, signal assembly, and the read API the routers call
