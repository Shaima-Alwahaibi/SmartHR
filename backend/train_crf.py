import joblib
from sklearn_crfsuite import CRF

# Dummy training data (just to create model)
X_train = [[{'word.lower': 'john'}, {'word.lower': 'doe'}]]
y_train = [['B-Name', 'I-Name']]

# Train CRF model
crf = CRF()
crf.fit(X_train, y_train)

# Save model
joblib.dump(crf, "models/crf_resume_ner.joblib")

print("✅ Model created successfully!")