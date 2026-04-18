import fitz  # PyMuPDF
import re
import json

SKILL_DB = [
    "python", "java", "c++", "fastapi", "django", "flask",
    "docker", "kubernetes", "aws", "azure", "gcp",
    "mysql", "postgresql", "mongodb",
    "machine learning", "deep learning",
    "nlp", "data science",
    "git", "github",
    "rest api", "microservices"
]


# -------------------------------
# PDF TEXT EXTRACTION
# -------------------------------
def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text += page.get_text("text") + "\n"

    return text.lower()


# -------------------------------
# SKILL EXTRACTION
# -------------------------------
def extract_skills(text):
    found = []

    for skill in SKILL_DB:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text):
            found.append(skill)

    return list(set(found))


# -------------------------------
# SIMPLE SECTION EXTRACTION
# -------------------------------
def extract_section(text, keywords):
    lines = text.split("\n")
    section = []
    capture = False

    for line in lines:
        if any(k in line for k in keywords):
            capture = True

        if capture:
            if line.strip() == "":
                break
            section.append(line.strip())

    return section


# -------------------------------
# PDF → JSON CONVERTER
# -------------------------------
def parse_resume_to_json(pdf_path):
    text = extract_text(pdf_path)

    candidate = {
        "name": "unknown",
        "skills": extract_skills(text),
        "projects": extract_section(text, ["project"]),
        "experience": extract_section(text, ["experience", "work"]),
        "education": extract_section(text, ["education", "degree"]),
        "raw_text": text[:2000]
    }

    return candidate


# -------------------------------
# SAVE AS JSON FILE
# -------------------------------
def save_json(data, filename="candidate.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    data = parse_resume_to_json("/Users/psailekhya/Documents/multimodel/P_Sai_Lekhya_Resume_compressed (1).pdf")

    print(json.dumps(data, indent=4))

    save_json(data)