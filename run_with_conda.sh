#!/bin/bash

# Debug information
echo "=== run_with_conda.sh started ==="
echo "Current directory: $(pwd)"

# Try multiple ways to initialize conda
init_conda() {
    # Method 1: Direct conda init
    if [ -f "$HOME/miniconda/bin/conda" ]; then
        echo "Initializing conda from $HOME/miniconda"
        __conda_setup="$('$HOME/miniconda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
        if [ $? -eq 0 ]; then
            eval "$__conda_setup"
            conda activate base
            return 0
        fi
    fi
    
    # Method 2: Source conda.sh
    if [ -f "$HOME/miniconda/etc/profile.d/conda.sh" ]; then
        echo "Sourcing conda.sh"
        . "$HOME/miniconda/etc/profile.d/conda.sh"
        conda activate base
        return 0
    fi
    
    # Method 3: Add to PATH
    if [ -d "$HOME/miniconda/bin" ]; then
        echo "Adding conda to PATH"
        export PATH="$HOME/miniconda/bin:$PATH"
        conda activate base
        return 0
    fi
    
    return 1
}

# Initialize conda
if ! init_conda; then
    echo "❌ Failed to initialize conda"
    exit 1
fi

# Verify conda is working
echo "Conda version: $(conda --version 2>&1 || echo 'conda not found')"
echo "Python: $(which python)"
echo "Python version: $(python --version 2>&1 || echo 'python not found')"

# Run the command passed as arguments
echo -e "\n=== Running command: $@ ==="
"$@"

exit_code=$?
echo -e "\n=== Command finished with exit code $exit_code ==="
exit $exit_code
