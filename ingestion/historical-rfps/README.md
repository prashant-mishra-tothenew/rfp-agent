Place historical RFP PDF, DOCX, and PPTX files here for ingestion.

## Included training proposals (TTN template format)

| File | Customer | Domain |
|------|----------|--------|
| `TRAIN_TTN_Proposal_RetailMax_Ecommerce_Platform.pptx` | RetailMax Group | Drupal Commerce / e-commerce |
| `TRAIN_TTN_Proposal_MediCare_Patient_Portal.pptx` | MediCare Health Network | Healthcare patient portal |
| `TRAIN_TTN_Proposal_FinServe_Digital_Onboarding.pptx` | FinServe Bank | Banking / digital onboarding |

Regenerate training decks from `templates/proposal-template.pptx`:

```bash
cd ai-service && PYTHONPATH=. python ../ingestion/scripts/generate_training_pptx.py
```

## Ingest into Milvus

```bash
cd ai-service && PYTHONPATH=. python ../ingestion/scripts/ingest.py --dir ../ingestion/historical-rfps
```

Or upload via the Knowledge page at http://localhost:3000/knowledge
