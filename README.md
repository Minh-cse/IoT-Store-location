# Project Setup Guide

## Requirements

- Python **3.9.1**
- `pip` (included with Python)

---

## Installation

### 1. Clone or download the project

```
git clone https://github.com/Minh-cse/IoT-Store-location.git
```

### 2. Create a virtual environment with Python 3.9.1

Make sure Python 3.9.1 is installed. You can verify with:
```bash
py -3.9 --version
```

Then create the virtual environment:
```bash
py -3.9 -m venv .venv
```

### 3. Activate the virtual environment

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r "requirement.txt"
```

## Run counterfit
```bash
counterfit
```
---

## Running the App

### Demo mode

Use `demo.py` to run a quick demonstration of the project:

```bash
python demo.py
```

This will connect to the MQTT broker and simulate sample data. Make sure your broker credentials and host settings are correctly configured inside `demo.py` before running.

### Project / Production mode

Use `app.py` to run the full application:

```bash
python app.py
```

---
*NOTE: counterfit and demo.py run simutanously using 2 terminal
## Deactivating the virtual environment

When you are done, deactivate the virtual environment with:
```bash
deactivate
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `python` command not found | Use `py -3.9` instead of `python` on Windows |
| Virtual environment fails to activate | Run PowerShell as Administrator and execute `Set-ExecutionPolicy RemoteSigned` |
| `pip install` fails | Make sure the venv is activated (you should see `(venv)` in the prompt) |
| Connection timeout on `demo.py` | Check your broker host, port, and TLS settings inside `demo.py` |
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` inside the activated venv |

---

## Project Structure

```
my-project/
├── venv/                  # Virtual environment (do not edit)
├── demo.py                # Demo script
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
└── README.md              # This file
```
