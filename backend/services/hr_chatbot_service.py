from skills.chatbot_persona import HR_CHATBOT_PERSONA
from skills.hr_skills import HR_KEYWORDS
from services.vector_store import search_resume_chunks
from services.llm_service import call_llm


def is_hr_question(question):
    q = (question or "").lower().strip()

    if not q:
        return False

    extra_keywords = [
        "programming language", "programming languages",
        "technology", "technologies", "framework", "frameworks",
        "university", "study", "studied", "background",
        "weak", "weakness", "weaknesses",
        "strong", "strength", "strengths",
        "explain", "simple", "understand",
        "react", "asp.net", ".net", "python", "java",
        "typescript", "sql", "api", "database"
    ]

    return any(word in q for word in HR_KEYWORDS + extra_keywords)


def hr_only_message():
    return (
        "I’m SmartHire AI. I can help with CVs, candidate skills, job matching, "
        "interview questions, and hiring recommendations."
    )


def safe_list(items, limit=8):
    if not items:
        return []

    cleaned = []
    for item in items:
        if not item:
            continue

        text = str(item).strip()

        if len(text) > 70:
            continue

        if text not in cleaned:
            cleaned.append(text)

    return cleaned[:limit]


def get_profile(candidate):
    return candidate.get("profile", {}) or {}


def get_match(candidate):
    return candidate.get("matchResult")


def get_skills(candidate):
    profile = get_profile(candidate)
    return safe_list(profile.get("skills", []), limit=12)


def detect_programming_languages(skills):
    languages = []

    possible = [
        "Python", "Java", "JavaScript", "TypeScript",
        "C#", "Dart", "C++", "PHP", "SQL"
    ]

    skill_text = " ".join(skills).lower()

    for lang in possible:
        if lang.lower() in skill_text and lang not in languages:
            languages.append(lang)

    return languages


def detect_frameworks(skills):
    frameworks = []

    possible = [
        "React", "ASP.NET Core", ".NET", "Bootstrap",
        "MUI", "Entity Framework", "TensorFlow", "PyTorch"
    ]

    skill_text = " ".join(skills).lower()

    for fw in possible:
        if fw.lower() in skill_text and fw not in frameworks:
            frameworks.append(fw)

    return frameworks


def explain_skill_for_hr(skill):
    explanations = {
        "Python": "used for automation, data analysis, and AI projects",
        "Java": "used for building software applications",
        "JavaScript": "used to make websites interactive",
        "TypeScript": "a safer version of JavaScript used in professional web apps",
        "React": "used to build modern website interfaces",
        "ASP.NET Core": "used to build secure backend systems and APIs",
        ".NET": "Microsoft technology for backend and enterprise systems",
        "SQL": "used to store and manage data in databases",
        "SQL Server": "Microsoft database system",
        "API": "allows systems to communicate with each other",
        "Entity Framework": "helps connect backend code with the database",
        "JWT": "used for secure login and authentication",
        "Machine Learning": "AI technique that helps systems learn from data",
        "Deep Learning": "advanced AI technique used for complex prediction tasks",
        "AI": "artificial intelligence systems that support automation and decision-making",
        "Bootstrap": "helps create responsive website layouts",
    }

    return explanations.get(skill, "relevant technical skill")


def build_candidate_summary(profile, match_result=None):
    name = profile.get("name") or "This candidate"
    designation = profile.get("designation") or "a technical candidate"
    degree = profile.get("degree") or "education not clearly detected"
    college = profile.get("college") or "university not clearly detected"
    experience = profile.get("experience") or "experience not clearly detected"
    location = profile.get("location") or "location not clearly detected"

    skills = safe_list(profile.get("skills", []), limit=8)

    answer = (
        f"{name} appears to be suitable for a **{designation}** or related IT role. "
        f"The candidate studied **{degree}** at **{college}** and is based in **{location}**. "
        f"The CV shows **{experience}**."
    )

    if skills:
        simple_skills = []
        for skill in skills[:6]:
            simple_skills.append(f"{skill} ({explain_skill_for_hr(skill)})")

        answer += "\n\nKey skills in HR-friendly language:\n"
        answer += "\n".join([f"- {item}" for item in simple_skills])

    if match_result:
        answer += (
            f"\n\nJob match: **{match_result.get('score')}%** "
            f"({match_result.get('status')})."
        )

    return answer


def answer_skills(candidate):
    skills = get_skills(candidate)

    if not skills:
        return "I could not clearly detect skills from this CV."

    lines = []
    for skill in skills[:8]:
        lines.append(f"- **{skill}**: {explain_skill_for_hr(skill)}")

    return "Here are the main skills in simple HR language:\n" + "\n".join(lines)


def answer_programming_languages(candidate):
    skills = get_skills(candidate)
    languages = detect_programming_languages(skills)

    if not languages:
        return "I could not clearly detect programming languages from this CV."

    return (
        "The detected programming languages are:\n"
        + "\n".join([f"- **{lang}**" for lang in languages])
    )


def answer_frameworks(candidate):
    skills = get_skills(candidate)
    frameworks = detect_frameworks(skills)

    if not frameworks:
        return "I could not clearly detect frameworks or technologies from this CV."

    lines = []
    for fw in frameworks:
        lines.append(f"- **{fw}**: {explain_skill_for_hr(fw)}")

    return "The detected frameworks/technologies are:\n" + "\n".join(lines)


def answer_education(candidate):
    profile = get_profile(candidate)

    degree = profile.get("degree") or "not clearly detected"
    college = profile.get("college") or "not clearly detected"

    return (
        "The candidate’s education is:\n"
        f"- **Degree:** {degree}\n"
        f"- **University/College:** {college}"
    )


def answer_experience(candidate):
    profile = get_profile(candidate)

    experience = profile.get("experience") or "not clearly detected"
    companies = safe_list(profile.get("companies", []), limit=5)

    answer = f"The detected experience is: **{experience}**."

    if companies:
        answer += "\n\nDetected companies/organizations:\n"
        answer += "\n".join([f"- {c}" for c in companies])

    return answer


def answer_strengths(candidate):
    profile = get_profile(candidate)
    skills = get_skills(candidate)

    strengths = []

    if skills:
        strengths.append("Good technical foundation in " + ", ".join(skills[:5]))

    if profile.get("degree"):
        strengths.append("Relevant academic background: " + profile.get("degree"))

    if profile.get("experience"):
        strengths.append("Has practical experience or training: " + profile.get("experience"))

    if not strengths:
        return "I could not identify strong points clearly from the CV."

    return "The main strengths are:\n" + "\n".join([f"- {s}" for s in strengths[:5]])


def answer_weaknesses(candidate):
    profile = get_profile(candidate)
    match_result = get_match(candidate)

    weaknesses = []

    if match_result and match_result.get("missingSkills"):
        weaknesses.append(
            "Missing job skills: " + ", ".join(match_result.get("missingSkills", [])[:6])
        )

    if not profile.get("experience"):
        weaknesses.append("Years of experience are not clearly stated.")

    if not profile.get("companies"):
        weaknesses.append("Previous company names are not clearly detected.")

    if not weaknesses:
        weaknesses.append(
            "No major weakness is clear from the CV, but HR should verify experience, project depth, and communication skills in the interview."
        )

    return "Possible weaknesses or points to verify:\n" + "\n".join([f"- {w}" for w in weaknesses])


def answer_match(candidate):
    match_result = get_match(candidate)

    if not match_result:
        return "Please rank the candidates with a job description first, then I can explain the match."

    matched = match_result.get("matchedSkills", [])
    missing = match_result.get("missingSkills", [])

    answer = (
        f"This candidate scored **{match_result.get('score')}%** "
        f"and is classified as **{match_result.get('status')}**."
    )

    if matched:
        answer += "\n\nMatched skills:\n"
        answer += "\n".join([f"- {s}" for s in matched[:8]])

    if missing:
        answer += "\n\nMissing skills to check:\n"
        answer += "\n".join([f"- {s}" for s in missing[:8]])

    return answer


def answer_interview_questions(candidate):
    skills = get_skills(candidate)
    match_result = get_match(candidate)

    questions = []

    for skill in skills[:4]:
        questions.append(f"Can you explain a project where you used {skill}?")

    if match_result:
        for skill in match_result.get("missingSkills", [])[:3]:
            questions.append(f"How familiar are you with {skill}?")

    if not questions:
        questions = [
            "Tell us about your strongest project.",
            "What technical skills do you feel most confident using?",
            "Describe a problem you solved during your studies or training.",
            "Why do you think you are suitable for this role?"
        ]

    return "Suggested interview questions:\n" + "\n".join([f"- {q}" for q in questions[:7]])


def answer_recommendation(candidate):
    match_result = get_match(candidate)

    if not match_result:
        return "Please rank the candidates first so I can give a hiring recommendation."

    score = match_result.get("score", 0)

    if score >= 80:
        decision = "Recommended for shortlisting."
    elif score >= 50:
        decision = "Possible candidate, but HR should verify missing skills in the interview."
    else:
        decision = "Not the strongest match for this role."

    return (
        f"Recommendation: **{decision}**\n"
        f"Reason: The match score is **{score}%** with status **{match_result.get('status')}**."
    )


def build_llm_prompt(question, candidate, relevant_chunks, chat_history):
    profile = get_profile(candidate)
    match_result = get_match(candidate)

    context = "\n\n".join([item["chunk"] for item in relevant_chunks[:3]]) if relevant_chunks else ""

    return f"""
{HR_CHATBOT_PERSONA}

Important:
- Answer in a short, friendly HR style.
- Do NOT copy raw CV text directly.
- Rewrite technical information in simple language for HR.
- Be specific to this candidate.
- Maximum 6 bullet points.
- If information is missing, say it is not clearly detected.
- Only answer HR/recruitment/CV questions.

Candidate Profile:
{profile}

Match Result:
{match_result}

Relevant CV Context:
{context}

Recent Chat:
{chat_history[-5:]}

Question:
{question}

Friendly HR Answer:
"""


def local_answer(question, candidate, relevant_chunks=None):
    q = question.lower().strip()

    if "summary" in q or "summarize" in q:
        return build_candidate_summary(get_profile(candidate), get_match(candidate))

    if "programming language" in q or "programming languages" in q:
        return answer_programming_languages(candidate)

    if "framework" in q or "technology" in q or "technologies" in q:
        return answer_frameworks(candidate)

    if "skill" in q or "skills" in q:
        return answer_skills(candidate)

    if "education" in q or "degree" in q or "university" in q or "college" in q or "study" in q:
        return answer_education(candidate)

    if "experience" in q or "company" in q or "worked" in q or "training" in q or "internship" in q:
        return answer_experience(candidate)

    if "strength" in q or "strong" in q:
        return answer_strengths(candidate)

    if "weakness" in q or "weak" in q:
        return answer_weaknesses(candidate)

    if "match" in q or "suitable" in q or "fit" in q:
        return answer_match(candidate)

    if "missing" in q:
        return answer_match(candidate)

    if "interview" in q or "question" in q:
        return answer_interview_questions(candidate)

    if "recommend" in q or "hire" in q or "shortlist" in q:
        return answer_recommendation(candidate)

    if relevant_chunks:
        return (
            "I found relevant CV information, but I’ll summarize it simply:\n"
            "- The candidate has experience related to software development and technical projects.\n"
            "- HR should review the extracted skills, education, and project experience before shortlisting."
        )

    return (
        "I can help with a short candidate summary, skills, education, experience, "
        "weaknesses, job match, interview questions, and hiring recommendation."
    )


def answer_hr_question(question, candidate, vector_store=None, chat_history=None):
    question = question or ""
    chat_history = chat_history or []

    if not question.strip():
        return "Please ask a question about the candidate."

    if not is_hr_question(question):
        return hr_only_message()

    relevant_chunks = search_resume_chunks(question, vector_store, top_k=4) if vector_store else []

    prompt = build_llm_prompt(
        question=question,
        candidate=candidate,
        relevant_chunks=relevant_chunks,
        chat_history=chat_history
    )

    llm_answer = call_llm(prompt)

    if llm_answer:
        return llm_answer.strip()

    return local_answer(question, candidate, relevant_chunks)