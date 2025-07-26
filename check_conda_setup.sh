#!/bin/bash

echo "=== Conda Environment Check ==="
echo "Current time: $(date)"
echo "Current directory: $(pwd)"
echo "Current shell: $SHELL"
echo "Home directory: $HOME"

echo -e "\n=== Environment Variables ==="
echo "PATH: $PATH"
echo "CONDA_DEFAULT_ENV: ${CONDA_DEFAULT_ENV:-Not set}"
echo "CONDA_PREFIX: ${CONDA_PREFIX:-Not set}"

# Check if conda command exists
if command -v conda &> /dev/null; then
    echo -e "\n=== Conda Installation Found ==="
    conda --version
    echo "Conda location: $(which conda)"
    
    # List environments
    echo -e "\n=== Conda Environments ==="
    conda info --envs
    
    # Current environment packages
    echo -e "\n=== Current Environment Packages ==="
    conda list
else
    echo -e "\n❌ Conda command not found in PATH"
    echo "Searched in: $PATH"
    
    # Check common conda locations
    echo -e "\nChecking common conda locations..."
    possible_paths=(
        "$HOME/miniconda3/bin/conda"
        "$HOME/anaconda3/bin/conda"
        "/opt/miniconda3/bin/conda"
        "/opt/anaconda3/bin/conda"
        "/usr/local/miniconda3/bin/conda"
        "/usr/local/anaconda3/bin/conda"
    )
    
    found=false
    for path in "${possible_paths[@]}"; do
        if [ -f "$path" ]; then
            echo "✅ Found conda at: $path"
            echo "   Try adding this to your PATH or source the appropriate init script"
            found=true
        fi
    done
    
    if [ "$found" = false ]; then
        echo "❌ Conda not found in common locations"
    fi
fi

echo -e "\n=== Shell Configuration Files ==="
config_files=(
    "$HOME/.bash_profile"
    "$HOME/.bashrc"
    "$HOME/.zshrc"
    "$HOME/.profile"
    "$HOME/.windsurf_shell_config"
)

for file in "${config_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "\n=== $file ==="
        # Show first 10 lines of each config file
        head -n 20 "$file" | sed 's/^/  /'
        echo "  ..."
    fi
done

echo -e "\n=== Python Information ==="
if command -v python &> /dev/null; then
    python --version
    echo "Python location: $(which python)"
else
    echo "Python command not found"
fi

echo -e "\nCheck complete. Look for any error messages above."
