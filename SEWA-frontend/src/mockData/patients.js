import mockData from './mockDataSet.json';

const firstNames = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Lisa", "Donald", "Helen", "George"];
const lastNames = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"];
const reasons = ["Sepsis", "Pneumonia", "Cardiac Arrest", "Trauma", "Post-op Recovery", "Respiratory Failure", "Kidney Failure", "Stroke", "Heart Failure", "Infection", "Burn Injury", "Diabetic Ketoacidosis"];
const conditions = ["Hypertension", "Diabetes Type 2", "COPD", "CHF", "Atrial Fibrillation", "CKD Stage 3", "Asthma", "Obesity", "Previous MI"];
const doctors = ["Dr. Sarah Chen", "Dr. Marcus Welby", "Dr. Gregory House", "Dr. Meredith Grey", "Dr. Shaun Murphy"];
const noteTemplates = [
    "Patient stable, resting comfortably.",
    "Complaining of mild chest pain, ECG normal.",
    "Family visited today. Discussed care plan.",
    "Antibiotics continued as scheduled.",
    "Vitals improving after fluid bolus.",
    "Monitoring urine output closely.",
    "Respiratory effort increased slightly.",
    "Awaiting lab results for electrolytes."
];

function getRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function getRandomSubset(arr, count) {
    const shuffled = [...arr].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.floor(Math.random() * count) + 1);
}

function generateNotes(admissionDate) {
    const notes = [];
    const count = Math.floor(Math.random() * 4);
    const admitTime = new Date(admissionDate).getTime();

    for (let i = 0; i < count; i++) {
        notes.push({
            id: `note-${Math.random().toString(36).substr(2, 9)}`,
            text: getRandom(noteTemplates),
            author: getRandom(doctors),
            timestamp: new Date(admitTime + Math.random() * (Date.now() - admitTime)).toISOString()
        });
    }
    return notes.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

// Select a balanced subset of patients
const sepsisPatients = mockData.filter(p => p.trajectory === 'early_sepsis').slice(0, 3);
const stablePatients = mockData.filter(p => p.trajectory === 'stable').slice(0, 5);
const selectedPatients = [...sepsisPatients, ...stablePatients].sort(() => 0.5 - Math.random());

export const INITIAL_PATIENTS = selectedPatients.map((p, index) => {
    // Generate admission date between 1 and 7 days ago
    const daysAgo = Math.floor(Math.random() * 7) + 1;
    const admissionDate = new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000).toISOString();

    return {
        patient_id: p.patient_id,
        name: `${getRandom(firstNames)} ${getRandom(lastNames)}`,
        age: p.age,
        gender: p.gender,
        bed_number: `ICU-${String(index + 1).padStart(2, '0')}`,
        admission_reason: getRandom(reasons),
        admission_date: admissionDate,
        trajectory: p.trajectory,
        initial_vitals: p.vitals,
        medical_history: getRandomSubset(conditions, 3),
        clinical_notes: generateNotes(admissionDate),
        treatment_bundle: {
            lactate_measure: Math.random() > 0.5,
            blood_cultures: Math.random() > 0.5,
            antibiotics: Math.random() > 0.5,
            fluids: Math.random() > 0.7,
            vasopressors: Math.random() > 0.8 && p.trajectory !== 'stable'
        }
    };
});
