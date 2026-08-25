# Technology Continuity Persona Engine

A bilingual (Arabic/English) Streamlit experience for conference visitors. It is designed as a **diagnostic experience**, not a survey.

## What the visitor sees
- One scenario per screen.
- Arabic / English switch.
- Dark / Light theme.
- Technology Continuity Readiness score (0–100).
- Continuity persona.
- Priority area and personalized service recommendation.
- Optional contact capture with consent.

## What the company sees
Hidden scoring separates the public result from commercial qualification:
- Eligibility Score
- Service Need %
- Decision Influence Score
- Organization Fit Score
- Commercial Opportunity Score
- Opportunity classification: Priority, Qualified, Nurture, Ecosystem, General Visitor
- Dashboard: persona counts, need by persona, opportunity mix, readiness vs. commercial opportunity, priority gaps, ranked lead table.

## Personas
### Client-side
1. The Resilient Guardian — الحارس المرن
2. The Managed Dependency — الاعتماد المُدار
3. The Exposed Operator — المشغّل المعرّض
4. The Critical Dependency — الاعتماد الحرج

### Provider-side
5. The Trusted Provider — المزوّد الموثوق
6. The Trust Builder — باني الثقة

### Non-target
7. The Explorer — المستكشف

## Google Sheets setup
1. Create a Google Sheet named **Technology Continuity Leads** (or change the name in Streamlit secrets).
2. In Google Cloud, create a project and enable **Google Sheets API** and **Google Drive API**.
3. Create a Service Account and a JSON key.
4. Share the Google Sheet with the Service Account `client_email` as **Editor**.
5. In Streamlit Cloud → App → Settings → Secrets, paste the values shown in `.streamlit/secrets.toml.example` using your real service-account credentials.
6. The app will automatically create a worksheet named `Responses` and write the required columns.

> If Google credentials are not configured, the app uses `responses_local.csv` only as a local-development fallback.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Upload `app.py`, `requirements.txt`, `.streamlit/secrets.toml.example` and this README to a GitHub repository.
2. Do **not** upload your real `secrets.toml` or service-account JSON to GitHub.
3. Create a Streamlit Cloud app using `app.py`.
4. Add secrets in the Streamlit Cloud settings.
5. Open the public app link on the conference device/QR code.

## Scoring model
The public readiness score and the hidden sales score are deliberately separate.

### Public readiness
For client/hybrid paths:
- Asset Control: 25%
- Continuity Recovery: 23%
- Exit Readiness: 18%
- Contract Clarity: 14%
- Evidence & Governance: 10%
- Criticality resilience adjustment: 10%

For provider path:
- Client Assurance: 30%
- Asset Control: 20%
- Continuity: 20%
- Contract Clarity: 15%
- Evidence & Governance: 15%

### Hidden Commercial Opportunity Score
- Service Need: 36%
- Eligibility: 20%
- Decision Influence: 16%
- Organization Fit: 13%
- Exposure (inverse readiness): 15%

These are **initial business weights**, not validated predictive coefficients. After the conference, use conversion outcomes (meeting booked, proposal, won/lost) to calibrate the weights statistically.

## Privacy design
- A general visitor can be counted anonymously without providing personal contact data.
- Contact fields are optional.
- Personal contact values are persisted only when the visitor checks the consent checkbox.
- For a real deployment, align the consent wording, retention period, access controls, and privacy notice with applicable organizational and Saudi data-protection requirements.


## GitHub → Streamlit deployment checklist
1. Create a new GitHub repository.
2. Upload the **contents of this folder** to the repository root.
3. Keep `.streamlit/secrets.toml.example` in GitHub, but **never upload** a real `.streamlit/secrets.toml` or Google service-account JSON key.
4. Confirm `app.py` and `requirements.txt` are in the repository root.
5. In Streamlit Community Cloud, create a new app and select this repository, branch, and `app.py`.
6. Open **App settings → Secrets** and copy the structure from `.streamlit/secrets.toml.example`, replacing placeholders with real credentials.
7. Share the target Google Sheet with the service-account email as Editor.
8. Redeploy. New visitor results will be written to the `Responses` worksheet and the internal dashboard will analyze them.

## Storytelling flow
The Streamlit experience follows a reveal rather than a questionnaire: **normal operations → relationship test → control/access → handover → contract/exit → continuity → evidence → persona reveal**. Hidden weights are never shown to visitors.

## Colab notebook
`Technology_Continuity_Storytelling_Engine.ipynb` documents and tests the storytelling questions, hidden scoring, personas, commercial qualification logic, Google Sheets structure, and analytical charts. Use it for model development; use `app.py` for the live conference experience.
