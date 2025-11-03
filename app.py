import streamlit as st
import pdfkit
import PyPDF2
import pandas as pd
import requests
import json

#  STEP 1: CONFIGURATION 
#  Encoded API Key with .env
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# STEP 2: STREAMLIT UI 
st.set_page_config(page_title="AI SRS Generator", layout="wide")
st.title("📄 AI-Based SRS Document Generator")
st.markdown("Enter a **project description**, upload a **PDF/text file**, or use an **Excel file** containing requirements:")

text_input = st.text_area("✍️ Enter Project Description Here", height=250)
uploaded_file = st.file_uploader("📤 Upload PDF or Text File", type=["pdf", "txt"])
excel_file = st.file_uploader("📊 Upload Excel File with Requirements", type=["xlsx"])

#  STEP 3: TEXT EXTRACTION 
def extract_text_from_file(file):
    if file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    return ""

def extract_text_from_excel(file):
    try:
        df = pd.read_excel(file)
        if {'S.No', 'User Code', 'Description', 'Function', 'Function Code'}.issubset(df.columns):
            result = ""
            for _, row in df.iterrows():
                result += f"\n- {row['User Code']} ({row['Function Code']}): {row['Function']} — {row['Description']}"
            return result
        else:
            return "❌ Excel format must include: S.No, User Code, Description, Function, Function Code"
    except Exception as e:
        return f"Error reading Excel: {str(e)}"

uploaded_text = extract_text_from_file(uploaded_file) if uploaded_file else ""
excel_text = extract_text_from_excel(excel_file) if excel_file else ""

# STEP 4: GENERATE BUTTON
if st.button("🚀 Generate SRS"):
    final_input = text_input.strip() or uploaded_text.strip() or excel_text.strip()

    if not final_input or "❌" in final_input or "Error" in final_input:
        st.error("⚠️ Please provide a valid description, PDF/text file, or correctly formatted Excel.")
    else:
        with st.spinner("Generating SRS using Google Gemini..."):

            prompt = f"""
You are a senior software analyst. Generate a fully detailed, ISO 13485:2016-compliant Software Requirements Specification (SRS) for a medical device software, based on structured input below.

**INCLUDE THESE SECTIONS (deep & audit-ready):**

1. **Title & Table of Contents**
2. **Introduction**
   - Purpose, scope, definitions, references (ISO clauses 4–7)

3. **Functional Requirements**
   - For each input USR/FUN combination:
     - 4.x Function heading (FUN_xxx)
     - 4.x.1, 4.x.2 Sub-functions (UN_xxx)
     - Detail requirements (USR_xxx…) and ≥2 test cases (TC_xxx)
   - Include traceability per function
4. **Design and Development Controls** (ISO 7.3)
5. **User Roles & Permissions**
6. **System Interfaces** (external systems, APIs)
7. **Non-Functional Requirements**
   - Performance, security, risk-management (align with ISO 14971), validation, reliability, maintainability
8. **Software Validation & Verification** (risk-based approach)
9. **Technology Stack**
10. **Assumptions & Dependencies**
11. **Traceability Matrix**
    - USR → FUN → UN → TC → Design → Verification Method
12. **Acronyms & Abbreviations**
13. **Document Control & Revision History**

**ADDITIONAL REQUIREMENTS:**
- Use medical device terminology
- Follow ISO formatting and clause numbering
- Ensure every requirement is traceable
- Minimum 30 pages output

**STRUCTURED INPUT BELOW:**
{final_input}
"""

            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": "AIzaSyCJNSeEoMUDMHV28b3C5qRJQ-RPhRqe_7A"
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }

            res = requests.post(GEMINI_ENDPOINT, headers=headers, json=payload)

            if res.status_code == 200:
                try:
                    output_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    st.error(f"❌ Error extracting response: {e}")
                    st.stop()
            else:
                st.error(f"❌ API Error: {res.text}")
                st.stop()

            #  STEP 5: FORMAT OUTPUT TO HTML 
            styled_html = """
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        font-family: 'Times New Roman', serif;
                        line-height: 1.6;
                        font-size: 14px;
                        padding: 40px;
                        color: #000;
                    }
                    h1 {
                        color: #1a4d80;
                        border-bottom: 2px solid #1a4d80;
                        padding-bottom: 5px;
                        font-size: 22px;
                    }
                    h2 {
                        color: #1a4d80;
                        margin-top: 30px;
                        font-size: 18px;
                    }
                    h3 {
                        margin-top: 20px;
                        font-size: 16px;
                        font-weight: bold;
                    }
                    p {
                        margin-bottom: 12px;
                        text-align: justify;
                    }
                    ul, ol {
                        margin-left: 20px;
                        margin-bottom: 15px;
                    }
                </style>
            </head>
            <body>
            """

            for line in output_text.split("\n"):
                if line.strip().startswith("### "):
                    styled_html += f"<h3>{line.replace('### ', '').strip()}</h3>"
                elif line.strip().startswith("## "):
                    styled_html += f"<h2>{line.replace('## ', '').strip()}</h2>"
                elif line.strip().startswith("# "):
                    styled_html += f"<h1>{line.replace('# ', '').strip()}</h1>"
                elif line.strip().startswith(("- ", "* ")):
                    styled_html += f"<ul><li>{line[2:].strip()}</li></ul>"
                elif line.strip():
                    styled_html += f"<p>{line.strip()}</p>"

            styled_html += "</body></html>"

            with open("output.html", "w", encoding="utf-8") as f:
                f.write(styled_html)

            #  STEP 6: CREATE PDF 
            pdfkit.from_file("output.html", "output.pdf", configuration=config)

            #  STEP 7: DOWNLOAD & VIEW 
            st.success("✅ SRS Generated Successfully!")
            st.download_button("📥 Download PDF", data=open("output.pdf", "rb"), file_name="SRS_Document.pdf")
            with st.expander("📖 View SRS Text"):
                st.markdown(output_text.replace('\n', '\n\n'))
