import re
import json
import numpy as np
from pathlib import Path
from collections import defaultdict

from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

from skills.hr_skills import TECH_SKILLS

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

BILSTM_PATH = MODEL_DIR / "bilstm_resume_ner.h5"
WORD_PATH = MODEL_DIR / "word2idx.json"
TAG_PATH = MODEL_DIR / "tag2idx.json"

MAX_LEN = 128

bilstm_model = load_model(BILSTM_PATH)

with open(WORD_PATH, "r", encoding="utf-8") as f:
    word2idx = json.load(f)

with open(TAG_PATH, "r", encoding="utf-8") as f:
    tag2idx = json.load(f)

idx2tag = {int(v): k for k, v in tag2idx.items()}


def tokenize(text):
    return re.findall(r"[a-zA-Z0-9+#.@]+(?:['\-][a-zA-Z0-9+#.@]+)*", text or "")


def clean_label(tag):
    if tag == "O" or tag == "PAD":
        return "O"
    return tag.split("-", 1)[-1]


def group_entities(tokens, tags):
    entities = defaultdict(list)
    current_label = None
    current_tokens = []

    for token, tag in zip(tokens, tags):
        tag = str(tag)

        if tag == "O" or tag == "PAD":
            if current_label:
                entities[current_label].append(" ".join(current_tokens))
            current_label = None
            current_tokens = []
            continue

        label = clean_label(tag)

        if tag.startswith("B-"):
            if current_label:
                entities[current_label].append(" ".join(current_tokens))
            current_label = label
            current_tokens = [token]

        elif tag.startswith("I-") and current_label == label:
            current_tokens.append(token)

    if current_label:
        entities[current_label].append(" ".join(current_tokens))

    return {k: list(dict.fromkeys(v)) for k, v in entities.items()}


def first_value(entities, labels):
    for label in labels:
        if entities.get(label):
            return entities[label][0]
    return ""


def fallback_email(text):
    found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return found[0] if found else ""


def fallback_phone(text):
    found = re.findall(r"(?:\+?\d{1,3}[\s\-()]*)?(?:\d[\s\-()]*){7,15}", text or "")

    cleaned = []
    for phone in found:
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 8:
            cleaned.append(digits)

    return cleaned[0] if cleaned else ""


def fallback_name(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]

    for line in lines[:8]:
        if "@" in line or any(ch.isdigit() for ch in line):
            continue

        fixed = re.sub(r"\s+", " ", line).strip()

        if len(fixed.split()) > 5 and len(fixed.replace(" ", "")) <= 30:
            fixed = fixed.replace(" ", "")
            fixed = fixed.replace("-", " Al-")
            return fixed.title()

        words = fixed.split()
        if 2 <= len(words) <= 5 and len(fixed) <= 45:
            return fixed.title()

    return ""


def fallback_location(text):
    known_locations = [
        "Muscat", "Oman", "Seeb", "Muttrah", "Nizwa", "Sohar",
        "Salalah", "Dubai", "UAE", "Abu Dhabi", "Qatar", "Doha",
        "Saudi Arabia", "Riyadh"
    ]

    text_lower = (text or "").lower()
    found = []

    for loc in known_locations:
        if loc.lower() in text_lower and loc not in found:
            found.append(loc)

    return ", ".join(found)


def fallback_college(text):
    patterns = [
        r"(University of Technology and Applied Sciences\s*[-–]?\s*[A-Za-z]*)",
        r"(Sultan Qaboos University)",
        r"(Middle East College)",
        r"(Muscat University)",
        r"(German University of Technology)",
        r"(GUtech)",
        r"([A-Za-z\s]+University)",
        r"([A-Za-z\s]+College)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            return value.title()

    return ""


def fallback_degree(text):
    text_lower = (text or "").lower()

    if "software engineering" in text_lower and "bachelor" in text_lower:
        return "Bachelor's Degree in Software Engineering"

    degree_patterns = [
        r"(Bachelor[’'s\s]* Degree in [A-Za-z\s]+)",
        r"(Bachelor of [A-Za-z\s]+)",
        r"(Master[’'s\s]* Degree in [A-Za-z\s]+)",
        r"(Master of [A-Za-z\s]+)",
        r"(BSc in [A-Za-z\s]+)",
        r"(MSc in [A-Za-z\s]+)"
    ]

    for pattern in degree_patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip().title()

    return ""


def fallback_designation(text):
    roles = [
        "Software Engineer",
        "Software Engineering",
        "Full Stack Developer",
        "Frontend Developer",
        "Backend Developer",
        "AI Developer",
        "Machine Learning Engineer",
        "Data Scientist",
        "Web Developer",
        "HR Officer",
        "Data Analyst"
    ]

    text_lower = (text or "").lower()

    for role in roles:
        if role.lower() in text_lower:
            return role

    if "softweer enginering" in text_lower or "software enginering" in text_lower:
        return "Software Engineering"

    return ""


def fallback_experience(text):
    patterns = [
        r"(\d+)\+?\s+years?\s+of\s+experience",
        r"(\d+)\+?\s+years?\s+experience",
        r"experience\s+of\s+(\d+)\+?\s+years?",
        r"(Trainee\s*[-–]\s*[A-Za-z\s()]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()

    if re.search(r"\btrainee\b|\bintern\b|\binternship\b", text or "", re.IGNORECASE):
        return "Training / Internship experience"

    return ""


def fallback_companies(text):
    companies = []

    patterns = [
        r"Trainee\s*[-–]\s*([A-Za-z\s()]+)",
        r"at\s+([A-Z][A-Za-z\s&]+)",
        r"Company\s*[:\-]\s*([A-Za-z\s&]+)"
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text or ""):
            company = re.sub(r"\s+", " ", match).strip()
            if company and company not in companies:
                companies.append(company)

    return companies


def fallback_skills(text):
    text_lower = (text or "").lower()
    found = []

    for skill in TECH_SKILLS:
        if skill.lower() in text_lower and skill not in found:
            found.append(skill)

    return found


def is_bad_email(value):
    if not value:
        return True
    return "@" not in value or "." not in value


def build_profile(text, entities):
    model_email = first_value(entities, ["Email Address", "Email"])
    reliable_email = fallback_email(text)

    model_degree = first_value(entities, ["Degree"])
    reliable_degree = model_degree or fallback_degree(text)

    model_college = first_value(entities, ["College Name", "College", "University"])
    reliable_college = model_college or fallback_college(text)

    model_location = first_value(entities, ["Location"])
    reliable_location = model_location or fallback_location(text)

    model_designation = first_value(entities, ["Designation"])
    reliable_designation = model_designation or fallback_designation(text)

    model_name = first_value(entities, ["Name"])
    reliable_name = model_name or fallback_name(text)

    model_experience = first_value(entities, ["Years of Experience", "Experience"])
    reliable_experience = model_experience or fallback_experience(text)

    model_companies = entities.get("Companies worked at", []) or entities.get("Company", [])
    reliable_companies = model_companies or fallback_companies(text)

    model_skills = entities.get("Skills", [])
    reliable_skills = model_skills or fallback_skills(text)

    if is_bad_email(model_email):
        final_email = reliable_email
    else:
        final_email = model_email

    return {
        "name": reliable_name,
        "email": final_email,
        "phone": fallback_phone(text),
        "skills": reliable_skills,
        "degree": reliable_degree,
        "college": reliable_college,
        "designation": reliable_designation,
        "companies": reliable_companies,
        "experience": reliable_experience,
        "location": reliable_location,
    }


def analyze_with_bilstm(text):
    tokens = tokenize(text)

    if not tokens:
        return {
            "model": "BiLSTM Deep Learning",
            "tokens": [],
            "tags": [],
            "entities": {},
            "profile": {}
        }

    token_ids = [word2idx.get(token.lower(), word2idx.get("UNK", 1)) for token in tokens]

    padded = pad_sequences(
        [token_ids],
        maxlen=MAX_LEN,
        padding="post",
        truncating="post",
        value=word2idx.get("PAD", 0)
    )

    probs = bilstm_model.predict(padded)
    pred_ids = np.argmax(probs, axis=-1)[0]

    used_tokens = tokens[:MAX_LEN]
    tags = [idx2tag.get(int(i), "O") for i in pred_ids[:len(used_tokens)]]

    entities = group_entities(used_tokens, tags)
    profile = build_profile(text, entities)

    return {
        "model": "BiLSTM Deep Learning",
        "tokens": used_tokens,
        "tags": tags,
        "entities": entities,
        "profile": profile
    }