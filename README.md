# Technical Analysis Project

This project contains a collection of Python scripts for performing various technical analysis calculations on stock data.

## Environment Setup

This project uses `conda` to manage a clean and isolated Python environment, which is necessary to avoid system-level architecture conflicts (especially on Apple Silicon Macs).

### 1. Prerequisite: Install Miniconda

If you haven't already, install [Miniconda](https://docs.anaconda.com/free/miniconda/index.html).

### 2. Create the Conda Environment

All the necessary Python packages and the correct Python version are defined within the conda environment. If you're setting this project up for the first time, create the environment and install the dependencies:

```bash
# Create the conda environment with Python 3.9
conda create --name technical-analysis python=3.9 -y

# Install all required packages into the environment
conda run -n technical-analysis pip install -r requirements.txt
```

## How to Run Python Scripts

All Python scripts in this project **must** be run from within the `technical-analysis` conda environment to ensure the correct Python interpreter and libraries are used.

### Primary Method (Recommended)

Use the `conda run` command to execute a script directly within the environment. This is the most reliable method.

```bash
# Command Template
conda run -n technical-analysis python [your_script_name.py]
```

**Example:**

To run the `price_change_calculator.py` script:

```bash
conda run -n technical-analysis python price_change_calculator.py
```

### Alternative Method (For Interactive Sessions)

If you plan to run multiple commands, it can be more convenient to activate the environment first.

1.  **Activate the environment:**
    ```bash
    conda activate technical-analysis
    ```
    Your terminal prompt will now start with `(technical-analysis)`.

2.  **Run scripts directly:**
    Now you can run the scripts using the simple `python` command.
    ```bash
    python price_change_calculator.py
    python macd_calculator.py
    ```

3.  **Deactivate when finished:**
    When you are done, exit the environment.
    ```bash
    conda deactivate
    ``` 