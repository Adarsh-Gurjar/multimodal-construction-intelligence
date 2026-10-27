# Multimodal Construction Intelligence Platform

Skill Wallet Capstone Project 1 — Platform ID: `6ac4c98d1dcde6d7857c164`

A Streamlit prototype for:
- Site safety and PPE photo screening with validated downloadable JSON reports
- Visible concrete crack/defect triage with a screening severity score
- Indicative construction budget, materials and valuation estimates
- Weather-aware daily protocols and a multi-turn site assistant
- Conceptual 3D rendering prompts with an optional Pollinations image-generation link

## Run locally

Python 3.9+ is required (Python 3.10+ recommended).

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Gemini Vision (optional)

Enter a Google Gemini API key in the app sidebar. The app uses the `google-genai` SDK and the `gemini-2.5-flash` model for image JSON output and assistant replies. Model reports are checked against the expected JSON fields; if the key is blank, the API call fails, or a report is invalid, the app falls back to clearly illustrative demo results.

Do not commit API keys to Git. The sidebar key is session input and is not written to disk.

The Pollinations action opens its image service in a new browser view. Only use it if you are comfortable sending the generated architectural prompt to that third party; no site image is included.

## Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Sign in at https://share.streamlit.io/ and connect GitHub.
3. Choose the repository, branch (`main`) and main file path (`app.py`).
4. Deploy. The public app URL is the demo URL to submit to Skill Wallet.
5. Optional: configure a secret in Streamlit app settings if you later change the app to read it from `st.secrets`; never add secrets to source control.

## Important limitations

- Image outputs are screening assistance, not proof of OSHA/Indian legal compliance.
- Crack width from a photo is not reliable without a scale; no structural diagnosis is provided.
- Budget, material quantities and real estate values are illustrative assumptions, not professional estimates or valuations.
- Crack severity and width are image-based screening estimates and must not be used as structural diagnoses.
- Pollinations image generation depends on the external service and its availability.
- Without a Gemini API key, the assistant uses built-in topic-based guidance rather than LLM conversation.
- Validate with a competent site safety professional, structural engineer, quantity surveyor and local valuation expert before operational use.
