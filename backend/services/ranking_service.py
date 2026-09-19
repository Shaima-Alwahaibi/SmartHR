def merge_profiles(crf_profile, dl_profile):
    def choose(field):
        crf_value = crf_profile.get(field)
        dl_value = dl_profile.get(field)

        if isinstance(crf_value, list) or isinstance(dl_value, list):
            values = []

            for item in crf_value or []:
                if item and item not in values:
                    values.append(item)

            for item in dl_value or []:
                if item and item not in values:
                    values.append(item)

            return values

        return crf_value or dl_value or ""

    return {
        "name": choose("name"),
        "email": choose("email"),
        "phone": choose("phone"),
        "skills": choose("skills"),
        "degree": choose("degree"),
        "college": choose("college"),
        "designation": choose("designation"),
        "companies": choose("companies"),
        "experience": choose("experience"),
        "location": choose("location"),
    }


def rank_candidates(candidates):
    ranked = sorted(
        candidates,
        key=lambda x: x.get("matchResult", {}).get("score", 0),
        reverse=True
    )

    for index, candidate in enumerate(ranked, start=1):
        candidate["rank"] = index

    return {
        "bestCandidate": ranked[0] if ranked else None,
        "rankedCandidates": ranked
    }