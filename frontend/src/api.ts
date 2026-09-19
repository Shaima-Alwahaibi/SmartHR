const API_BASE = "http://127.0.0.1:5000/api";

async function handleResponse(response: Response) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

export async function analyzeResume(resumeText: string) {
  const response = await fetch(`${API_BASE}/analyze-resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ resumeText }),
  });

  return handleResponse(response);
}

export async function uploadPdf(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/upload-pdf`, {
    method: "POST",
    body: formData,
  });

  return handleResponse(response);
}

export async function matchJob(jobDescription: string) {
  const response = await fetch(`${API_BASE}/match-job`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ jobDescription }),
  });

  return handleResponse(response);
}

export async function askChatbot(question: string) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  return handleResponse(response);
}

export async function resetCandidate() {
  const response = await fetch(`${API_BASE}/reset`, {
    method: "POST",
  });

  return handleResponse(response);
}