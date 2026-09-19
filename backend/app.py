import os

from flask import Flask, request, jsonify
from flask_cors import CORS

from services.pdf_service import extract_text_from_pdf
from services.ml_crf_service import analyze_with_crf
from services.dl_bilstm_service import analyze_with_bilstm
from services.match_service import calculate_match
from services.ranking_service import merge_profiles, rank_candidates
from services.resume_chunker import chunk_text
from services.vector_store import build_resume_vector_store
from services.hr_chatbot_service import answer_hr_question

app = Flask(__name__)
CORS(app)

candidate_store = []
chat_history = []


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "SmartHire AI backend is running with CRF, BiLSTM, multi-CV ranking, and smart HR chatbot."
    })


@app.route("/api/analyze-multiple-cvs", methods=["POST"])
def analyze_multiple_cvs():
    global candidate_store
    candidate_store = []

    if "files" not in request.files:
        return jsonify({"error": "Please upload one or more PDF files."}), 400

    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "No files uploaded."}), 400

    for index, file in enumerate(files, start=1):
        if not file.filename.lower().endswith(".pdf"):
            continue

        resume_text = extract_text_from_pdf(file)

        if not resume_text:
            continue

        crf_result = analyze_with_crf(resume_text)
        dl_result = analyze_with_bilstm(resume_text)

        merged_profile = merge_profiles(
            crf_result.get("profile", {}),
            dl_result.get("profile", {})
        )

        chunks = chunk_text(resume_text)
        vector_store = build_resume_vector_store(chunks)

        candidate_store.append({
            "id": index,
            "fileName": file.filename,
            "resumeText": resume_text,
            "ml": crf_result,
            "dl": dl_result,
            "profile": merged_profile,
            "matchResult": None,
            "jobDescription": "",
            "vectorStore": vector_store,
            "chunksCount": len(chunks)
        })

    return jsonify({
        "message": "CVs analyzed successfully.",
        "count": len(candidate_store),
        "candidates": remove_private_objects(candidate_store)
    })


@app.route("/api/rank-candidates", methods=["POST"])
def rank_uploaded_candidates():
    data = request.get_json()
    job_description = data.get("jobDescription", "")

    if not job_description.strip():
        return jsonify({"error": "Job description is required."}), 400

    if not candidate_store:
        return jsonify({"error": "Please upload and analyze CVs first."}), 400

    for candidate in candidate_store:
        skills = candidate.get("profile", {}).get("skills", [])
        match_result = calculate_match(skills, job_description)
        candidate["matchResult"] = match_result
        candidate["jobDescription"] = job_description

    ranking = rank_candidates(candidate_store)

    return jsonify({
        "message": "Candidates ranked successfully.",
        "bestCandidate": remove_private_objects([ranking["bestCandidate"]])[0],
        "rankedCandidates": remove_private_objects(ranking["rankedCandidates"])
    })


@app.route("/api/candidate/<int:candidate_id>", methods=["GET"])
def get_candidate(candidate_id):
    for candidate in candidate_store:
        if candidate["id"] == candidate_id:
            return jsonify(remove_private_objects([candidate])[0])

    return jsonify({"error": "Candidate not found."}), 404


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question", "")
    candidate_id = data.get("candidateId")

    if not candidate_store:
        return jsonify({
            "answer": "Please upload and analyze CVs first."
        })

    candidate = None

    if candidate_id:
        for item in candidate_store:
            if item["id"] == candidate_id:
                candidate = item
                break

    if candidate is None:
        ranked = sorted(
            candidate_store,
            key=lambda x: x.get("matchResult", {}).get("score", 0),
            reverse=True
        )
        candidate = ranked[0]

    answer = answer_hr_question(
        question=question,
        candidate=candidate,
        vector_store=candidate.get("vectorStore"),
        chat_history=chat_history
    )

    chat_history.append({
        "candidateId": candidate.get("id"),
        "question": question,
        "answer": answer
    })

    return jsonify({
        "answer": answer,
        "candidateId": candidate.get("id"),
        "chatHistory": chat_history[-10:]
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    global candidate_store, chat_history
    candidate_store = []
    chat_history = []

    return jsonify({"message": "All candidates and chat history cleared."})


def remove_private_objects(candidates):
    clean_candidates = []

    for candidate in candidates:
        if candidate is None:
            continue

        clean = dict(candidate)
        clean.pop("vectorStore", None)

        resume_text = clean.get("resumeText", "")
        clean["resumePreview"] = resume_text[:800]
        clean.pop("resumeText", None)

        clean_candidates.append(clean)

    return clean_candidates


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)