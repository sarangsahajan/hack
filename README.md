# The SHIBU: Sound Haptic Interface for Better Understanding

An engineering prototype developed as a collaborative hackathon project by a three-member team. The project combines software, hardware interfacing, computer vision/matching, and system integration into a single working solution.

## 👥 Team

| Member | Role |
|---|---|
| **Sarang K** | Development & System Integration |
| **Karthik N Nair** | Development & Hardware/Software Integration |
| **Emil Phil Vinod** | Development & Testing/Integration |

> **All three team members contributed directly to the development and implementation of the codebase.**  
> The project was developed collaboratively, with members working on different components and contributing changes throughout the development process.

## 🛠️ Project

The project consists of a Python-based software system with hardware integration and automated processing. The implementation includes modules for matching/recognition, processing, serial communication, testing, and system control.

### Main Components

- **`main.py`** — Main application and system workflow
- **`matcher.py`** — Matching and processing logic
- **`needle_layer.py`** — Needle/feature processing layer
- **`svl_serial.py`** — Serial communication and hardware interface
- **`test_matcher.py`** — Testing and validation
- **`requirements.txt`** — Python dependencies

## 💻 Technologies

- Python
- Computer Vision / Image Processing
- Pattern & Feature Matching
- Serial Communication
- Hardware Control
- Automated Testing

## 🔧 Setup

### 1. Clone the repository

```bash
git clone https://github.com/sarangsahajan/hack.git
cd hack
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Windows PowerShell:**

```powershell
& .\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**

```cmd
.venv\Scripts\activate.bat
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the project

```bash
python main.py
```

## 🧪 Testing

The project includes automated tests for core functionality.

Run:

```bash
python -m pytest
```

or:

```bash
python test_matcher.py
```

## 🤝 Collaboration

This repository represents **joint work by Sarang K, Karthik N Nair, and Emil Phil Vinod**.

Development was carried out collaboratively, with each member contributing code, debugging, testing, integration, and iterative improvements during the project.

The repository owner is **Sarang K**, but ownership of the repository should not be interpreted as sole authorship of the project.

## 📌 Contributors

- **Sarang K**
- **Karthik N Nair**
- **Emil Phil Vinod**

All three members contributed to the codebase and project development.

## 📄 License

This project was developed as part of a hackathon. Please contact the authors before reusing or redistributing the project or its components.
