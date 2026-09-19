import re
from difflib import SequenceMatcher


def normalize_skill(skill):
    skill = (skill or "").lower().strip()
    skill = skill.replace("c sharp", "c#")
    skill = skill.replace("dotnet", ".net")
    skill = skill.replace("asp net", "asp.net")
    skill = skill.replace("javascript", "js")
    skill = skill.replace("typescript", "ts")
    skill = re.sub(r"\s+", " ", skill)
    return skill


def split_skills(text):
    if not text:
        return []

    parts = re.split(r"[,;\n|/]+", text.lower())
    return [normalize_skill(p) for p in parts if len(p.strip()) > 1]


def expand_job_roles(job_skills):
    role_map = {
        "frontend developer": ["react", "js", "ts", "html", "css", "bootstrap", "mui"],
        "backend developer": [".net", "asp.net core", "api", "sql", "database", "entity framework", "jwt"],
        "full stack developer": ["react", "js", "ts", ".net", "asp.net core", "sql", "api", "database"],
        "ai developer": ["python", "ai", "machine learning", "deep learning", "nlp", "tensorflow", "pytorch"],
        "data scientist": ["python", "machine learning", "statistics", "pandas", "numpy", "ai"],
        "software engineer": ["programming", "python", "java", "c#", "sql", "api", "git", "problem solving"],
        "hr officer": ["recruitment", "screening", "interview", "communication", "onboarding"],
    }

    expanded = set(job_skills)

    for skill in list(job_skills):
        if skill in role_map:
            expanded.update(role_map[skill])

    return expanded


def expand_synonyms(skills):
    synonym_map = {
        "js": ["javascript"],
        "javascript": ["js"],
        "ts": ["typescript"],
        "typescript": ["ts"],
        ".net": ["dotnet", "asp.net core", "asp.net"],
        "asp.net core": [".net", "dotnet"],
        "machine learning": ["ml"],
        "ml": ["machine learning"],
        "artificial intelligence": ["ai"],
        "ai": ["artificial intelligence"],
        "database": ["sql", "sql server"],
        "sql server": ["sql", "database"],
        "api": ["rest api", "rest"],
        "rest api": ["api"],
        "entity framework": ["ef core", "ef"],
    }

    expanded = set(skills)

    for skill in list(skills):
        if skill in synonym_map:
            expanded.update(synonym_map[skill])

    return expanded


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def is_similar_skill(candidate_skill, job_skill, threshold=0.75):
    candidate_skill = normalize_skill(candidate_skill)
    job_skill = normalize_skill(job_skill)

    if candidate_skill == job_skill:
        return True

    if candidate_skill in job_skill or job_skill in candidate_skill:
        return True

    return similarity(candidate_skill, job_skill) >= threshold


def get_skill_weight(skill):
    skill = normalize_skill(skill)

    high_value = {
        "python", "sql", "machine learning", "deep learning",
        "ai", "react", ".net", "asp.net core", "api",
        "tensorflow", "pytorch"
    }

    medium_value = {
        "git", "github", "excel", "html", "css", "bootstrap",
        "jwt", "entity framework", "database", "pandas", "numpy"
    }

    if skill in high_value:
        return 3

    if skill in medium_value:
        return 2

    return 1


def calculate_match(candidate_skills, job_description):
    candidate_set = set()

    for skill_group in candidate_skills or []:
        for skill in split_skills(skill_group):
            candidate_set.add(skill)

    candidate_set = expand_synonyms(candidate_set)

    job_skills = set(split_skills(job_description))
    job_skills = expand_job_roles(job_skills)
    job_skills = expand_synonyms(job_skills)

    if not job_skills:
        return {
            "score": 0,
            "matchedSkills": [],
            "missingSkills": [],
            "status": "No job skills provided"
        }

    matched = set()
    missing = set()

    total_weight = 0
    matched_weight = 0

    for job_skill in job_skills:
        weight = get_skill_weight(job_skill)
        total_weight += weight

        found = any(is_similar_skill(candidate_skill, job_skill) for candidate_skill in candidate_set)

        if found:
            matched.add(job_skill)
            matched_weight += weight
        else:
            missing.add(job_skill)

    score = round((matched_weight / total_weight) * 100, 2)

    if score >= 80:
        status = "Strong Candidate"
    elif score >= 50:
        status = "Moderate Candidate"
    else:
        status = "Weak Match"

    return {
        "score": score,
        "matchedSkills": sorted(matched),
        "missingSkills": sorted(missing),
        "status": status
    }