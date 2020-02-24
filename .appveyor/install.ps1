Set-PSDebug -Trace 1
Set-ExecutionPolicy RemoteSigned

Write-Host "Configure Conda to operate without user input"
& $env:MINICONDA\Scripts\conda.exe config --set always_yes yes --set changeps1 no

Write-Host "Update conda"
& $env:MINICONDA\Scripts\conda.exe install -q "conda>=4.6.11"

Write-Host "Initialize Conda Powershell support and activate base environment."
(& $env:MINICONDA\Scripts\conda.exe "shell.powershell" "hook") | Out-String | Invoke-Expression

# Allow extra Conda channels to be added (e.g., for testing).
if ($env:CONDA_EXTRA_CHANNELS) {
    $env:CONDA_EXTRA_CHANNELS.Split(";") | ForEach {
        Write-Host "Adding Conda channel from %CONDA_EXTRA_CHANNELS%: $_"
        conda config --add channels $_
    }
}

# Create new project environment
conda create -n $env:APPVEYOR_PROJECT_NAME pandoc $(cat .\requirements.txt)
if ($LASTEXITCODE) { throw "Failed to create build Conda environment." }

conda activate $env:APPVEYOR_PROJECT_NAME
conda info --envs
conda install 7za -y -c conda-forge -c anaconda

# Download 7zip installer and extract _self-extracting (SFX)_ plugins.
cmd /C curl -L --output 7zip-installer.exe https://www.7-zip.org/a/7z1805.exe
7za x "-ir!*.sfx" 7zip-installer.exe
if ($LASTEXITCODE) { throw "Failed to extract 7zip self-extracting executable module" }