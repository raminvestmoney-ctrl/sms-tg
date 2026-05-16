// --- Mock Data: 50 Physics MCQs ---
// For the demo, we pre-define a set of challenging physics questions
const physicsMCQs = [
    {
        q: "The dimensional formula for the Universal Gravitational Constant (G) is:",
        options: ["[M L³ T⁻²]", "[M⁻¹ L³ T⁻²]", "[M⁻¹ L² T⁻²]", "[M L² T⁻¹]"],
        correct: 1
    },
    {
        q: "A particle is moving in a circular path of radius r. The displacement after half a circle would be:",
        options: ["Zero", "πr", "2r", "2πr"],
        correct: 2
    },
    {
        q: "The work-energy theorem states that the work done by the net force on a particle is equal to the change in its:",
        options: ["Kinetic Energy", "Potential Energy", "Linear Momentum", "Angular Momentum"],
        correct: 0
    },
    {
        q: "If the momentum of a body is increased by 50%, its kinetic energy will increase by:",
        options: ["50%", "100%", "125%", "225%"],
        correct: 2
    },
    {
        q: "The time period of a simple pendulum inside a stationary lift is T. If the lift starts accelerating upwards with 'g/2', the new time period will be:",
        options: ["T√(2/3)", "T√(3/2)", "T/2", "2T"],
        correct: 0
    },
    // Adding more variety to simulate the 50 questions
    ...Array.from({length: 45}, (_, i) => ({
        q: `Advanced Physics Challenge #${i + 6}: Regarding ${['Quantum Mechanics', 'Thermodynamics', 'Electromagnetism', 'Optics'][i % 4]}, which statement is correct?`,
        options: [
            "The energy is quantized and proportional to frequency.",
            "Entropy of an isolated system always increases.",
            "Magnetic flux is conserved in a closed loop.",
            "Light behaves as both a particle and a wave."
        ],
        correct: i % 4
    }))
];

// --- State Management ---
let currentScreen = 'landing';
let uploadedFiles = [];
let currentQuestionIndex = 0;
let userAnswers = new Array(50).fill(null);
let examTimer = null;
let timeLeft = 3600; // 60 minutes

// --- DOM Elements ---
const screens = {
    landing: document.getElementById('landing'),
    processing: document.getElementById('processing'),
    exam: document.getElementById('exam'),
    result: document.getElementById('result')
};

const uploadInput = document.getElementById('note-upload');
const generateBtn = document.getElementById('generate-btn');
const fileList = document.getElementById('file-list');
const progressBar = document.getElementById('ai-progress');
const statusText = document.getElementById('status-text');
const questionText = document.getElementById('question-text');
const optionsGrid = document.getElementById('options-grid');
const questionCounter = document.getElementById('question-counter');
const examProgressBar = document.getElementById('exam-progress-bar');
const nextBtn = document.getElementById('next-btn');
const prevBtn = document.getElementById('prev-btn');
const submitBtn = document.getElementById('submit-btn');
const timerDisplay = document.getElementById('timer');

const navDots = document.getElementById('nav-dots');

// --- Navigation Functions ---
function showScreen(screenId) {
    Object.values(screens).forEach(s => s.classList.add('hidden'));
    screens[screenId].classList.remove('hidden');
    currentScreen = screenId;
}

// --- Upload Logic ---
uploadInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    uploadedFiles = [...uploadedFiles, ...files];
    
    updateFilePreview();
    generateBtn.disabled = uploadedFiles.length === 0;
});

function updateFilePreview() {
    fileList.innerHTML = '';
    uploadedFiles.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const div = document.createElement('div');
            div.className = 'preview-item';
            div.innerHTML = `<img src="${e.target.result}" alt="Note ${index + 1}">`;
            fileList.appendChild(div);
        };
        reader.readAsDataURL(file);
    });
}

// --- AI Generation Simulation ---
generateBtn.addEventListener('click', () => {
    showScreen('processing');
    simulateAIProcessing();
});

async function simulateAIProcessing() {
    const stages = [
        { text: "Extracting text from images...", progress: 25, log: "log-1" },
        { text: "Analyzing key Physics concepts...", progress: 50, log: "log-2" },
        { text: "Generating 50 challenging MCQs...", progress: 75, log: "log-3" },
        { text: "Finalizing your personalized exam...", progress: 100, log: "log-4" }
    ];

    for (const stage of stages) {
        statusText.innerText = stage.text;
        progressBar.style.width = `${stage.progress}%`;
        document.getElementById(stage.log).classList.add('active');
        await new Promise(r => setTimeout(r, 1500));
    }

    startExam();
}

// --- Exam Logic ---
function startExam() {
    showScreen('exam');
    renderQuestion();
    startTimer();
}

function renderQuestion() {
    const q = physicsMCQs[currentQuestionIndex];
    questionText.innerText = q.q;
    questionCounter.innerText = `Question ${currentQuestionIndex + 1}/50`;
    examProgressBar.style.width = `${((currentQuestionIndex + 1) / 50) * 100}%`;

    optionsGrid.innerHTML = '';
    q.options.forEach((opt, idx) => {
        const btn = document.createElement('button');
        btn.className = `option-btn ${userAnswers[currentQuestionIndex] === idx ? 'selected' : ''}`;
        btn.innerText = opt;
        btn.onclick = () => selectOption(idx);
        optionsGrid.appendChild(btn);
    });

    renderNavDots();

    prevBtn.disabled = currentQuestionIndex === 0;
    if (currentQuestionIndex === 49) {
        nextBtn.classList.add('hidden');
        submitBtn.classList.remove('hidden');
    } else {
        nextBtn.classList.remove('hidden');
        submitBtn.classList.add('hidden');
    }
}

function renderNavDots() {
    navDots.innerHTML = '';
    // Show a selection of dots if there are many, or all if we want to be thorough
    // For 50 questions, we'll show all small dots
    for (let i = 0; i < 50; i++) {
        const dot = document.createElement('div');
        dot.className = `nav-dot ${i === currentQuestionIndex ? 'active' : ''} ${userAnswers[i] !== null ? 'completed' : ''}`;
        dot.onclick = () => {
            currentQuestionIndex = i;
            renderQuestion();
        };
        navDots.appendChild(dot);
    }
}

function selectOption(idx) {
    userAnswers[currentQuestionIndex] = idx;
    renderQuestion();
}

nextBtn.addEventListener('click', () => {
    if (currentQuestionIndex < 49) {
        currentQuestionIndex++;
        renderQuestion();
    }
});

prevBtn.addEventListener('click', () => {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        renderQuestion();
    }
});

function startTimer() {
    examTimer = setInterval(() => {
        timeLeft--;
        const mins = Math.floor(timeLeft / 60);
        const secs = timeLeft % 60;
        timerDisplay.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        
        if (timeLeft <= 0) {
            clearInterval(examTimer);
            showResults();
        }
    }, 1000);
}

// --- Results Logic ---
submitBtn.addEventListener('click', showResults);

function showResults() {
    clearInterval(examTimer);
    showScreen('result');
    
    let score = 0;
    userAnswers.forEach((ans, idx) => {
        if (ans === physicsMCQs[idx].correct) score++;
    });

    const percentage = Math.round((score / 50) * 100);
    const timeTaken = 3600 - timeLeft;
    const mins = Math.floor(timeTaken / 60);
    const secs = timeTaken % 60;

    // Update UI
    document.getElementById('final-score').innerText = `${score}/50`;
    document.getElementById('time-taken').innerText = `${mins}:${secs.toString().padStart(2, '0')}`;
    document.getElementById('accuracy-rate').innerText = `${percentage}%`;
    document.getElementById('score-percentage').innerText = `${percentage}%`;
    
    const circleFill = document.getElementById('score-circle-fill');
    circleFill.setAttribute('stroke-dasharray', `${percentage}, 100`);

    if (percentage >= 80) {
        document.getElementById('result-message').innerText = "Outstanding! You have a strong grasp of these concepts.";
    } else if (percentage >= 50) {
        document.getElementById('result-message').innerText = "Good effort! A bit more practice will make you perfect.";
    } else {
        document.getElementById('result-message').innerText = "Keep studying! Review the notes and try again.";
    }
}

// --- Drag & Drop Support ---
const dropZone = document.querySelector('.upload-box');
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
    dropZone.addEventListener(evt, e => {
        e.preventDefault();
        e.stopPropagation();
    });
});

dropZone.addEventListener('drop', (e) => {
    const files = Array.from(e.dataTransfer.files);
    uploadedFiles = [...uploadedFiles, ...files];
    updateFilePreview();
    generateBtn.disabled = uploadedFiles.length === 0;
});
