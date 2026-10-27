import html
import json
from datetime import datetime
from urllib.parse import quote

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
.main {background: #f5f7fb;}
[data-testid="stMetric"] {background: white; border: 1px solid #e6eaf0; padding: 14px; border-radius: 12px;}
.hero {padding: 1.25rem 1.5rem; border-radius: 16px; background: linear-gradient(120deg,#102a43,#176b87); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin-bottom:.3rem;}
.pill {display:inline-block; padding:5px 10px; border-radius:20px; font-weight:700; font-size:.85rem; background:#e7f5ec; color:#176b3a;}
.small-note {color:#52616b;font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🏗️ Multimodal Construction Intelligence Platform</h1>
<p>AI-assisted site safety, concrete defect triage, project budgeting and weather-aware site protocols.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Workspace")
    api_key = st.text_input("Google Gemini API key (optional)", type="password",
                            help="Used only for image analysis when configured. Leave blank to use demo mode.")
    st.caption("🔐 The key is held in this session and is not written to a file.")
    st.divider()
    st.subheader("Architecture")
    st.write("Streamlit UI → Gemini Vision (optional) → validated JSON → downloadable reports")
    st.write("Demo mode works without an API key.")
    st.divider()
    st.caption("Prototype decision-support tool. Not a substitute for a qualified safety officer, structural engineer, quantity surveyor, or property valuer.")

def demo_safety():
    return {
        "safety_score": 78,
        "overall_status": "Needs Attention",
        "ppe_detection": {
            "hard_hat": "Partially observed; verify all workers",
            "high_visibility_vest": "Observed on some workers",
            "safety_boots": "Not reliably verifiable from this image",
            "safety_harness": "Not applicable / not clearly visible"
        },
        "hazards": [
            {"hazard": "Potential unprotected edge or elevated work area", "severity": "High",
             "remedy": "Inspect edge protection; install compliant guardrails or approved fall-arrest systems."},
            {"hazard": "PPE coverage cannot be confirmed for every worker", "severity": "Medium",
             "remedy": "Conduct a supervisor-led PPE check and document each worker's compliance."}
        ],
        "limitations": "Illustrative demo output. Replace with an actual site inspection."
    }

def demo_crack():
    return {
        "defect_type": "Hairline",
        "estimated_width_mm": 0.3,
        "severity": "Low to Moderate",
        "severity_score": 18,
        "possible_root_causes": ["Drying shrinkage", "Thermal movement", "Surface plaster shrinkage"],
        "recommended_action": ["Measure and map the crack", "Monitor for change", "Ask a qualified engineer to inspect if widening or recurring; the engineer can determine whether epoxy injection, re-grouting, or another repair is suitable"],
        "urgency": "Routine inspection",
        "limitations": "Image-only estimates are approximate; depth and structural significance cannot be confirmed from a photo."
    }

def gemini_image_json(image, prompt, key):
    if not key:
        return None
    try:
        from google import genai
        from google.genai import types
        import io
        client = genai.Client(api_key=key)
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception as exc:
        st.warning(f"Gemini analysis failed ({type(exc).__name__}); illustrative demo results are shown.")
        return None

def validate_safety_result(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    score = data.get("safety_score")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("safety_score must be an integer between 0 and 100.")
    if data.get("overall_status") not in (
        "Compliant", "Needs Attention", "Unsafe", "Unable to Determine"
    ):
        raise ValueError("overall_status is not a supported status.")
    ppe = data.get("ppe_detection")
    if not isinstance(ppe, dict):
        raise ValueError("ppe_detection must be an object.")
    required_ppe = ("hard_hat", "high_visibility_vest", "safety_boots", "safety_harness")
    if any(not isinstance(ppe.get(item), str) for item in required_ppe):
        raise ValueError("ppe_detection must include a text assessment for each PPE item.")
    hazards = data.get("hazards")
    if not isinstance(hazards, list):
        raise ValueError("hazards must be a list.")
    for hazard in hazards:
        if not isinstance(hazard, dict) or not all(
            isinstance(hazard.get(field), str) for field in ("hazard", "severity", "remedy")
        ):
            raise ValueError("Each hazard must include hazard, severity, and remedy text.")
        if hazard["severity"] not in ("Low", "Medium", "High", "Critical"):
            raise ValueError("Hazard severity must be Low, Medium, High, or Critical.")
    if not isinstance(data.get("limitations"), str):
        raise ValueError("limitations must be text.")
    return data

def validate_crack_result(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    if data.get("defect_type") not in (
        "Hairline", "Settlement", "Structural Shear", "Thermal Expansion",
        "Spalling", "Other", "Unable to Determine"
    ):
        raise ValueError("defect_type is not a supported classification.")
    width = data.get("estimated_width_mm")
    if width is not None and (
        isinstance(width, bool) or not isinstance(width, (int, float)) or width < 0
    ):
        raise ValueError("estimated_width_mm must be a non-negative number or null.")
    severity_score = data.get("severity_score")
    if (
        isinstance(severity_score, bool)
        or not isinstance(severity_score, int)
        or not 0 <= severity_score <= 100
    ):
        raise ValueError("severity_score must be an integer between 0 and 100.")
    for field in ("possible_root_causes", "recommended_action"):
        if not isinstance(data.get(field), list) or not all(
            isinstance(item, str) for item in data[field]
        ):
            raise ValueError(f"{field} must be a list of text.")
    if not all(isinstance(data.get(field), str) for field in ("severity", "urgency")):
        raise ValueError("severity and urgency must be text.")
    if not isinstance(data.get("limitations"), str):
        raise ValueError("limitations must be text.")
    return data

def use_validated_result(result, validator, demo_factory, module_name):
    if result is None:
        return demo_factory()
    try:
        return validator(result)
    except (TypeError, ValueError) as exc:
        st.warning(
            f"Gemini returned an invalid {module_name} report ({exc}); "
            "illustrative demo results are shown."
        )
        return demo_factory()

def open_uploaded_image(uploaded_file):
    try:
        return ImageOps.exif_transpose(Image.open(uploaded_file)).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        st.error(f"Could not read this image ({type(exc).__name__}). Please upload a valid JPG or PNG.")
        return None

def gemini_chat_response(question, history, key):
    if not key:
        return None
    try:
        from google import genai

        recent_history = history[-8:]
        transcript = "\n".join(
            f"{'User' if message['role'] == 'user' else 'Assistant'}: {message['content']}"
            for message in recent_history
        )
        prompt = (
            "You are a cautious construction planning assistant. Provide general information only; "
            "do not certify safety, diagnose structural integrity, or replace local codes or "
            "qualified professionals. Use the recent conversation for context.\n\n"
            f"{transcript}\nUser: {question}\nAssistant:"
        )
        response = genai.Client(api_key=key).models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        answer = response.text
        return answer.strip() if answer and answer.strip() else None
    except Exception as exc:
        st.warning(f"Gemini assistant failed ({type(exc).__name__}); using the built-in guidance.")
        return None

def show_json_report(data, filename):
    st.json(data, expanded=True)
    st.download_button("⬇️ Download JSON report", json.dumps(data, indent=2), file_name=filename,
                       mime="application/json")

def severity_color(severity):
    s = str(severity).lower()
    if "critical" in s or "high" in s: return "🔴"
    if "medium" in s or "moderate" in s: return "🟠"
    return "🟢"

tabs = st.tabs([
    "🦺 Site Safety & PPE", "🧱 Crack Diagnostics",
    "📐 Planning & Valuation", "🌦️ Site Assistant"
])

with tabs[0]:
    st.subheader("Site Safety & PPE Audit")
    st.write("Upload a clear site photo. The analysis is an initial screening, not a compliance certification.")
    photo = st.file_uploader("Construction site photo", type=["jpg", "jpeg", "png"], key="safety_img")
    if photo:
        image = open_uploaded_image(photo)
        if image is not None:
            st.image(image, caption="Uploaded site photo", use_container_width=True)
            if st.button("Analyze site safety", type="primary"):
                prompt = """Analyze this construction site photo for visible PPE and obvious hazards.
Return JSON only with keys: safety_score (integer 0-100), overall_status (Compliant, Needs Attention, Unsafe, or Unable to Determine),
ppe_detection (object with hard_hat, high_visibility_vest, safety_boots, safety_harness values), hazards (array of objects with hazard, severity
(Low, Medium, High, Critical), remedy), limitations. Do not claim to verify hidden details or legal compliance from an image.
Use cautious language and say not visible/uncertain when appropriate. Reference OSHA/Indian site safety principles only as general guidance;
do not claim certification."""
                result = gemini_image_json(image, prompt, api_key)
                st.session_state["safety_result"] = use_validated_result(
                    result, validate_safety_result, demo_safety, "safety"
                )
    if "safety_result" in st.session_state:
        data = st.session_state["safety_result"]
        a, b = st.columns(2)
        a.metric("Safety screening score", f'{data.get("safety_score", "—")}/100')
        b.metric("Overall status", data.get("overall_status", "Unable to determine"))
        st.markdown(
            f'<span class="pill">{html.escape(data.get("overall_status", "Unable to Determine"))}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("#### PPE checklist")
        for k, v in data.get("ppe_detection", {}).items():
            st.write(f"**{k.replace('_',' ').title()}** — {v}")
        st.markdown("#### Hazards and corrective actions")
        for hazard in data.get("hazards", []):
            st.markdown(f"**{severity_color(hazard.get('severity'))} {hazard.get('hazard','Hazard')}** · {hazard.get('severity','Unrated')}")
            st.write(hazard.get("remedy", "Review with site supervisor."))
        show_json_report(data, "site_safety_report.json")

with tabs[1]:
    st.subheader("Crack Diagnostics & Structural Integrity")
    st.write("Use a close-up photo with a ruler or scale where possible. Do not infer structural safety from a photo alone.")
    crack_photo = st.file_uploader("Concrete or wall surface photo", type=["jpg", "jpeg", "png"], key="crack_img")
    if crack_photo:
        image = open_uploaded_image(crack_photo)
        if image is not None:
            st.image(image, caption="Uploaded surface photo", use_container_width=True)
            if st.button("Assess visible crack", type="primary"):
                prompt = """Inspect the visible surface defect in this image. Return JSON only with keys:
defect_type (Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling, Other, or Unable to Determine),
estimated_width_mm (number or null), severity, severity_score (integer 0-100), possible_root_causes (array),
recommended_action (array), urgency, limitations.
Clearly label width as a rough visual estimate, or null if no scale is present. Do not diagnose structural integrity from a photo.
Rate severity_score as an indicative screening score only. Mention epoxy injection or structural re-grouting only as options for a qualified engineer to assess;
recommend qualified engineering inspection for diagonal/widening cracks, exposed reinforcement, displacement, water ingress, or falling concrete."""
                result = gemini_image_json(image, prompt, api_key)
                st.session_state["crack_result"] = use_validated_result(
                    result, validate_crack_result, demo_crack, "crack"
                )
    if "crack_result" in st.session_state:
        data = st.session_state["crack_result"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Defect type", data.get("defect_type", "Unknown"))
        c2.metric("Estimated width", f'{data.get("estimated_width_mm", "—")} mm')
        c3.metric("Severity screening score", f'{data.get("severity_score", "—")}/100')
        c4.metric("Urgency", data.get("urgency", "Review"))
        st.markdown(
            f'<span class="pill">{html.escape(data.get("urgency", "Review"))}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("#### Possible causes")
        for item in data.get("possible_root_causes", []): st.write(f"• {item}")
        st.markdown("#### Recommended next steps")
        for item in data.get("recommended_action", []): st.write(f"• {item}")
        st.warning(data.get("limitations", "Photo-based assessment is limited."))
        show_json_report(data, "crack_diagnostics_report.json")

with tabs[2]:
    st.subheader("Project Planning & Real Estate Valuation")
    left, right = st.columns(2)
    with left:
        structure = st.selectbox("Structure type", ["Residential house", "Apartment building", "Commercial building", "Warehouse", "Institutional building"])
        area = st.number_input("Built-up area (sq ft)", min_value=100, max_value=2000000, value=1500, step=100)
        tier = st.selectbox("Location tier", ["Tier 1", "Tier 2", "Tier 3"])
        completion = st.slider("Construction completion", 0, 100, 35, 5)
    rates = {"Residential house": 2100, "Apartment building": 2400, "Commercial building": 2800, "Warehouse": 1500, "Institutional building": 2600}
    tier_multiplier = {"Tier 1": 1.35, "Tier 2": 1.0, "Tier 3": 0.82}
    base_rate = rates[structure] * tier_multiplier[tier]
    estimated_cost = area * base_rate
    incurred = estimated_cost * completion / 100
    market_multiplier = {"Tier 1": 1.65, "Tier 2": 1.25, "Tier 3": 1.0}[tier]
    market_value = area * base_rate * market_multiplier
    steel_kg = area * 4.0
    cement_bags = area * 0.40
    with right:
        st.markdown("#### Indicative estimates")
        st.metric("Estimated project budget", f"₹{estimated_cost/100000:.2f} lakh")
        st.metric("Estimated cost incurred", f"₹{incurred/100000:.2f} lakh")
        st.metric("Indicative market asset value", f"₹{market_value/10000000:.2f} crore")
        st.metric("Steel planning allowance", f"{steel_kg:,.0f} kg")
        st.metric("Cement planning allowance", f"{cement_bags:,.0f} bags")
    st.progress(completion / 100, text=f"Milestone progress: {completion}%")
    st.caption("Assumptions: broad illustrative rates and material thumb rules only. These are not quotations, a bill of quantities, an appraisal, or a certified valuation. Actual rates vary by design, specifications, city, soil, taxes and market conditions.")
    st.markdown("#### Conceptual 3D rendering")
    concept_details = st.text_area(
        "Describe the desired architectural concept",
        "Contemporary Indian architecture, realistic materials, landscaped entrance, daylight",
        key="render_details",
    )
    if st.button("Build rendering prompt"):
        st.session_state["render_prompt"] = (
            f"Conceptual 3D architectural rendering of a {structure.lower()}, "
            f"{area:,} square feet, located in an Indian {tier.lower()} city. "
            f"{concept_details.strip()}. Professional architectural visualization, "
            "realistic scale and materials, high detail."
        )
    render_prompt = st.session_state.get("render_prompt")
    if render_prompt:
        st.code(render_prompt, language="text")
        st.caption("Opening the image generator sends this prompt to Pollinations, a third-party service.")
        render_url = f"https://image.pollinations.ai/prompt/{quote(render_prompt, safe='')}?width=1024&height=1024&model=flux&nologo=true"
        st.link_button("Generate concept image with Pollinations", render_url)
    st.download_button("⬇️ Download planning estimate", json.dumps({
        "structure_type": structure, "built_up_sqft": area, "location_tier": tier,
        "completion_percent": completion, "estimated_budget_inr": round(estimated_cost),
        "estimated_cost_incurred_inr": round(incurred), "indicative_market_value_inr": round(market_value),
        "steel_allowance_kg": round(steel_kg), "cement_allowance_bags": round(cement_bags),
        "assumptions": "Illustrative estimates only; verify with qualified professionals."
    }, indent=2), file_name="planning_estimate.json", mime="application/json")

with tabs[3]:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    weather = st.selectbox("Current / forecast site condition", ["Normal", "High Wind", "Heavy Rain", "Extreme Heat"])
    advisories = {
        "Normal": ["Run the toolbox talk and confirm PPE before work.", "Inspect access routes, scaffolds and lifting equipment.", "Follow approved concrete placement and curing plans."],
        "High Wind": ["Pause crane and hoisting operations when wind exceeds equipment/site limits.", "Secure loose materials, sheets and temporary structures.", "Restrict work at height when conditions are unsafe."],
        "Heavy Rain": ["Assess excavation stability and water accumulation; restrict unsafe access.", "Protect electrical equipment and use appropriate residual-current protection.", "Review concrete placement, washout and curing with the site engineer."],
        "Extreme Heat": ["Schedule strenuous work for cooler hours and provide shaded rest breaks.", "Provide drinking water and monitor workers for heat illness.", "Follow the approved concrete temperature, placement and curing procedure."]
    }
    for advice in advisories[weather]: st.info(advice)
    st.caption("Follow site-specific emergency plans, local regulations, equipment manuals, and competent-person direction.")
    st.markdown("#### Construction assistant")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.write(msg["content"])
    question = st.chat_input("Ask about site planning, PPE, cracks, materials, or weather...")
    if question:
        previous_history = list(st.session_state.chat_history)
        answer = gemini_chat_response(question, previous_history, api_key)
        if answer is None:
            q = question.lower()
            if any(x in q for x in ["crack", "structural", "column", "beam"]):
                answer = "For a crack or structural concern, record its location, direction, length, approximate width and whether it is changing. Keep people away from visibly unstable areas and arrange inspection by a qualified structural engineer. A chat response or photo cannot certify structural safety."
            elif any(x in q for x in ["cost", "budget", "cement", "steel", "quantity"]):
                answer = "For a reliable estimate, prepare drawings/specifications, quantities, grade and finish schedule, local supplier rates, labour, equipment, taxes and contingency. The planning tab uses illustrative thumb rules, not a BOQ."
            elif any(x in q for x in ["helmet", "ppe", "safety", "harness"]):
                answer = "Use the site's approved risk assessment and PPE matrix. Check fit, condition and suitability; inspect fall-protection systems before use, and stop work when critical controls are missing. Have the safety officer verify compliance."
            else:
                answer = "I can provide general construction planning guidance. Share the structure type, work activity, site condition and relevant measurements. For safety-critical, structural, legal or valuation decisions, confirm with a qualified professional and the applicable local standards."
        st.session_state.chat_history.append({"role": "user", "content": question})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

st.divider()
st.caption(f"Skill Wallet Capstone Project 1 · Prototype · Report generated from session data · {datetime.now().strftime('%d %b %Y')}")
