Set-PSDebug -Trace 1
Set-ExecutionPolicy RemoteSigned

# Set version number based on git tag
$x = git describe --tags
if (!$?) {
    $prevTag = "v0.0-0"
}
else { $prevTag = $x.Split("-")[0] + "-" + $x.Split("-")[1] }

$buildTag = $prevTag + "+" + $(Get-Date -Format FileDateTime)
Write-Host "Build Tag: $buildTag"
Update-AppveyorBuild -Version $buildTag

conda activate $env:APPVEYOR_PROJECT_NAME

python -m dinner_daily_helpers.download previous .
foreach ($menu in $(dir ????-??-??-weekly-menu-Any?Store.html)) { 
    echo $menu;
    if (-not (Test-Path "$($menu.BaseName).json")) {
        echo "Converting $menu to JSON";
        python -m dinner_daily_helpers --json $menu "$($menu.BaseName).json";
    }
    if (-not (Test-Path "$($menu.BaseName).md")) {
        echo "Converting $menu to Markdown";
        python -m dinner_daily_helpers --markdown $menu "$($menu.BaseName).md";
    }
    if (-not (Test-Path "$($menu.BaseName).reformatted.html")) {
        echo "Converting $menu to reformatted HTML";
        python -m dinner_daily_helpers $menu "$($menu.BaseName).reformatted.html";
    }
}

md artifacts
mv *.json artifacts
mv *.html artifacts
mv *.md artifacts
if (-Not $?) { throw "No markdown files found." }