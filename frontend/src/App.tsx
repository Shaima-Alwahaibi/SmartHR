import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

type Profile = {
  name?: string;
  email?: string;
  phone?: string;
  skills?: string[];
  degree?: string;
  college?: string;
  designation?: string;
  experience?: string;
  location?: string;
  companies?: string[];
};

type MatchResult = {
  score: number;
  status: string;
  matchedSkills: string[];
  missingSkills: string[];
};

type ModelResult = {
  model: string;
  entities: Record<string, string[]>;
  profile: Profile;
};

type Candidate = {
  id: number;
  fileName: string;
  rank?: number;
  resumePreview?: string;
  profile: Profile;
  ml: ModelResult;
  dl: ModelResult;
  matchResult?: MatchResult | null;
};

type ChatMessage = {
  role: "user" | "bot";
  text: string;
};

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\/$/, "");

const QUICK_QUESTIONS = [
  "Summarize this candidate",
  "What are the weaknesses?",
  "What skills were detected?",
  "Generate interview questions",
];

export default function App() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const [files, setFiles] = useState<File[]>([]);
  const [jobDescription, setJobDescription] = useState("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [bestCandidate, setBestCandidate] = useState<Candidate | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "bot",
      text: "Hi, I’m SmartHire AI. Upload CVs, rank them with a job description, then ask me about skills, weaknesses, interview questions, or hiring recommendations.",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [notice, setNotice] = useState<{ type: "error" | "success"; text: string } | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const totalFiles = useMemo(() => files.length, [files]);
  const ranked = Boolean(bestCandidate);
  const currentStep = ranked ? 3 : candidates.length > 0 ? 2 : files.length > 0 ? 1 : 0;

  const getScoreClass = (score?: number | null) => {
    if (score === undefined || score === null) return "score gray";
    if (score >= 80) return "score green";
    if (score >= 50) return "score orange";
    return "score red";
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, chatBusy]);

  const showNotice = (type: "error" | "success", text: string) => {
    setNotice({ type, text });
    window.setTimeout(() => setNotice(null), 5000);
  };

  const collectPdfs = (incoming: FileList | File[]) => {
    const next = Array.from(incoming).filter((file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"));
    setFiles(next);
  };

  const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    collectPdfs(e.target.files || []);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const uploadCVs = async () => {
    if (files.length === 0) {
      showNotice("error", "Please choose one or more PDF CV files first.");
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    setLoading(true);
    setLoadingLabel("Reading CVs with CRF and BiLSTM…");

    try {
      const response = await fetch(`${API_URL}/api/analyze-multiple-cvs`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        showNotice("error", data.error || "Upload failed.");
        return;
      }

      setCandidates(data.candidates || []);
      setBestCandidate(null);
      setSelectedCandidate(data.candidates?.[0] || null);
      showNotice("success", `${data.count} CV file(s) analyzed. Add a job description to rank them.`);

      setChatMessages([
        {
          role: "bot",
          text: `Great. I analyzed ${data.count} CV file(s). Now write the job description and click Rank Candidates.`,
        },
      ]);
    } catch {
      showNotice("error", "Backend connection failed. Make sure the API is running.");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  };

  const rankCandidates = async () => {
    if (!jobDescription.trim()) {
      showNotice("error", "Please write the job description first.");
      return;
    }

    setLoading(true);
    setLoadingLabel("Matching skills and ranking candidates…");

    try {
      const response = await fetch(`${API_URL}/api/rank-candidates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ jobDescription }),
      });

      const data = await response.json();

      if (!response.ok) {
        showNotice("error", data.error || "Ranking failed.");
        return;
      }

      setCandidates(data.rankedCandidates || []);
      setBestCandidate(data.bestCandidate || null);
      setSelectedCandidate(data.bestCandidate || data.rankedCandidates?.[0] || null);
      showNotice("success", "Ranking complete. Review the best match and ask the chatbot anything.");

      setChatMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: `Ranking completed. The best CV is ${
            data.bestCandidate?.profile?.name || data.bestCandidate?.fileName || "the top candidate"
          } with a match score of ${data.bestCandidate?.matchResult?.score}%.`,
        },
      ]);
    } catch {
      showNotice("error", "Backend connection failed.");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  };

  const askChatbot = async (preset?: string) => {
    const question = (preset ?? chatQuestion).trim();
    if (!question || chatBusy) return;

    setChatQuestion("");
    setChatMessages((prev) => [...prev, { role: "user", text: question }]);
    setChatBusy(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          candidateId: selectedCandidate?.id,
        }),
      });

      const data = await response.json();

      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: data.answer || "I could not generate an answer." },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: "I cannot connect to the backend. Please make sure the API is running.",
        },
      ]);
    } finally {
      setChatBusy(false);
    }
  };

  const resetAll = async () => {
    try {
      await fetch(`${API_URL}/api/reset`, { method: "POST" });
    } catch {}

    setFiles([]);
    setCandidates([]);
    setBestCandidate(null);
    setSelectedCandidate(null);
    setJobDescription("");
    setChatMessages([
      {
        role: "bot",
        text: "Session reset. Upload CVs again when you are ready.",
      },
    ]);

    if (fileInputRef.current) fileInputRef.current.value = "";
    showNotice("success", "Workspace cleared. You can start a new screening.");
  };

  return (
    <div className="page">
      {notice && <div className={`toast ${notice.type}`}>{notice.text}</div>}

      {loading && (
        <div className="loadingOverlay" role="status" aria-live="polite">
          <div className="spinner" />
          <p>{loadingLabel || "Working…"}</p>
        </div>
      )}

      <header className="hero">
        <div>
          <p className="eyebrow">SmartHire AI</p>
          <h1>Hire with clarity, not guesswork</h1>
          <p>
            Upload multiple CVs, extract information using <b>CRF ML</b> and <b>BiLSTM DL</b>, then rank
            candidates using the job description.
          </p>

          <ol className="steps">
            <li className={currentStep >= 0 ? "on" : ""}>Upload CVs</li>
            <li className={currentStep >= 1 ? "on" : ""}>Analyze</li>
            <li className={currentStep >= 2 ? "on" : ""}>Rank</li>
            <li className={currentStep >= 3 ? "on" : ""}>Ask AI</li>
          </ol>
        </div>

        <div className="heroStats">
          <div>
            <strong>{candidates.length}</strong>
            <span>CVs analyzed</span>
          </div>
          <div>
            <strong>{bestCandidate ? "1" : "0"}</strong>
            <span>Best selected</span>
          </div>
        </div>
      </header>

      <main className="topGrid">
        <section className="panel">
          <h2>Upload Multiple CVs</h2>
          <p>Drop PDF files here, or click to browse. Hold Ctrl to select many files.</p>

          <label
            className={dragOver ? "uploadBox dragOver" : "uploadBox"}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              collectPdfs(e.dataTransfer.files);
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              onChange={handleFilesChange}
            />
            <span className="uploadIcon" aria-hidden>
              ⇪
            </span>
            <strong>{totalFiles > 0 ? `${totalFiles} file(s) selected` : "Drop PDF CVs here"}</strong>
            <em>PDF only · multiple files supported</em>
          </label>

          {files.length > 0 && (
            <div className="selectedFiles">
              {files.map((file, index) => (
                <div className="selectedFile" key={`${file.name}-${index}`}>
                  <span>{file.name}</span>
                  <button type="button" onClick={() => removeFile(index)}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}

          <button className="primaryBtn" onClick={uploadCVs} disabled={loading}>
            {loading ? "Processing..." : "Analyze CVs"}
          </button>
        </section>

        <section className="panel">
          <h2>Job Description</h2>
          <p>Write the job requirements to rank candidates.</p>

          <textarea
            placeholder="Example: Full stack developer with React, TypeScript, ASP.NET Core, SQL, APIs, Git..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
          />

          <div className="actions">
            <button className="primaryBtn" onClick={rankCandidates} disabled={loading || candidates.length === 0}>
              Rank Candidates
            </button>
            <button className="secondaryBtn" onClick={resetAll}>
              Reset
            </button>
          </div>
        </section>
      </main>

      {bestCandidate && (
        <section className="bestCard">
          <div>
            <p className="eyebrow greenText">Best CV Selected</p>
            <h2>{bestCandidate.profile.name || bestCandidate.fileName}</h2>
            <p>{bestCandidate.profile.designation || "Designation not clearly detected"}</p>
          </div>

          <span className={getScoreClass(bestCandidate.matchResult?.score)}>
            {bestCandidate.matchResult?.score}%
          </span>
        </section>
      )}

      {candidates.length > 0 && (
        <section className="mainLayout">
          <aside className="candidatePanel">
            <h2>Candidates</h2>
            {candidates.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                className={selectedCandidate?.id === candidate.id ? "candidateItem active" : "candidateItem"}
                onClick={() => setSelectedCandidate(candidate)}
              >
                <span>
                  #{candidate.rank || candidate.id} {candidate.profile.name || candidate.fileName}
                </span>
                <b>{candidate.matchResult?.score ?? 0}%</b>
              </button>
            ))}
          </aside>

          {selectedCandidate && (
            <section className="contentArea">
              <CandidateProfile candidate={selectedCandidate} getScoreClass={getScoreClass} />

              {selectedCandidate.matchResult && (
                <section className="panel">
                  <h2>Job Match Result</h2>
                  <p>
                    Status: <b>{selectedCandidate.matchResult.status}</b>
                  </p>

                  <h3>Matched Skills</h3>
                  <SkillChips skills={selectedCandidate.matchResult.matchedSkills} type="green" />

                  <h3>Missing Skills</h3>
                  <SkillChips skills={selectedCandidate.matchResult.missingSkills} type="red" />
                </section>
              )}

              <section className="modelsGrid">
                <ModelCard title="ML Section: CRF Model" result={selectedCandidate.ml} />
                <ModelCard title="DL Section: BiLSTM Model" result={selectedCandidate.dl} />
              </section>

              <section className="panel">
                <h2>Resume Preview</h2>
                <p className="resumePreview">{selectedCandidate.resumePreview || "No preview available."}</p>
              </section>
            </section>
          )}

          <aside className="chatPanel">
            <h2>Smart HR Chatbot</h2>
            <p>Ask short HR questions about the selected candidate.</p>

            <div className="quickQuestions">
              {QUICK_QUESTIONS.map((q) => (
                <button key={q} type="button" onClick={() => askChatbot(q)}>
                  {q}
                </button>
              ))}
            </div>

            <div className="chatWindow">
              {chatMessages.map((msg, index) => (
                <div key={index} className={msg.role === "user" ? "chat user" : "chat bot"}>
                  {msg.text}
                </div>
              ))}
              {chatBusy && <div className="chat bot typing">SmartHire is thinking…</div>}
              <div ref={chatEndRef} />
            </div>

            <div className="chatInput">
              <input
                value={chatQuestion}
                placeholder="Ask SmartHire AI..."
                onChange={(e) => setChatQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") askChatbot();
                }}
              />
              <button type="button" onClick={() => askChatbot()} disabled={chatBusy}>
                Send
              </button>
            </div>
          </aside>
        </section>
      )}
    </div>
  );
}

function CandidateProfile({
  candidate,
  getScoreClass,
}: {
  candidate: Candidate;
  getScoreClass: (score?: number | null) => string;
}) {
  return (
    <section className="panel">
      <div className="candidateHeader">
        <div>
          <h2>{candidate.profile.name || candidate.fileName}</h2>
          <p>{candidate.profile.designation || "Designation not detected"}</p>
        </div>
        <span className={getScoreClass(candidate.matchResult?.score)}>
          {candidate.matchResult?.score ?? "No"} Score
        </span>
      </div>

      <h3>Final Merged Profile</h3>
      <div className="infoGrid">
        <Info label="Name" value={candidate.profile.name} />
        <Info label="Email" value={candidate.profile.email} />
        <Info label="Phone" value={candidate.profile.phone} />
        <Info label="Degree" value={candidate.profile.degree} />
        <Info label="College" value={candidate.profile.college} />
        <Info label="Experience" value={candidate.profile.experience} />
        <Info label="Location" value={candidate.profile.location} />
        <Info label="Designation" value={candidate.profile.designation} />
      </div>

      <h3>Final Skills</h3>
      <SkillChips skills={candidate.profile.skills} />
    </section>
  );
}

function ModelCard({ title, result }: { title: string; result: ModelResult }) {
  return (
    <section className="panel modelCard">
      <h2>{title}</h2>
      <p>This information was extracted by this model.</p>

      <div className="modelProfile">
        <div className="infoGrid">
          <Info label="Name" value={result.profile.name} />
          <Info label="Email" value={result.profile.email} />
          <Info label="Phone" value={result.profile.phone} />
          <Info label="Degree" value={result.profile.degree} />
          <Info label="College" value={result.profile.college} />
          <Info label="Experience" value={result.profile.experience} />
          <Info label="Location" value={result.profile.location} />
          <Info label="Designation" value={result.profile.designation} />
        </div>

        <h3>Skills</h3>
        <SkillChips skills={result.profile.skills} />

        <h3>Companies</h3>
        <SkillChips skills={result.profile.companies} />
      </div>

      <h3>Extracted Entities</h3>
      <pre>{JSON.stringify(result.entities, null, 2)}</pre>
    </section>
  );
}

function Info({ label, value }: { label: string; value?: string }) {
  return (
    <div className="infoBox">
      <span>{label}</span>
      <b>{value || "Not detected"}</b>
    </div>
  );
}

function SkillChips({ skills, type }: { skills?: string[]; type?: "green" | "red" }) {
  const className = type === "green" ? "chips green" : type === "red" ? "chips red" : "chips";
  const clean = (skills || []).filter((s) => s && s.length <= 70).slice(0, 18);

  if (clean.length === 0) return <p className="emptyText">Not detected</p>;

  return (
    <div className={className}>
      {clean.map((skill, index) => (
        <span key={index}>{skill}</span>
      ))}
    </div>
  );
}
