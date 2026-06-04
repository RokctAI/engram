param (
    [Parameter(Mandatory=$true, HelpMessage="The source folder to scan recursively for images.")]
    [string]$SourceFolder,

    [Parameter(Mandatory=$false, HelpMessage="The destination folder where images will be organized. Defaults to '.\images'.")]
    [string]$DestinationFolder = ".\images"
)

# Convert relative paths to absolute paths
$SourceFolder = [System.IO.Path]::GetFullPath($SourceFolder)
$DestinationFolder = [System.IO.Path]::GetFullPath($DestinationFolder)

if (!(Test-Path $SourceFolder)) {
    Write-Error "Source folder does not exist: $SourceFolder"
    exit 1
}

Write-Host "Scanning '$SourceFolder' for images..."

# Find all files with typical image extensions
$imageExtensions = @(".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")
$files = Get-ChildItem -Path $SourceFolder -File -Recurse | Where-Object {
    $_.Extension.ToLower() -in $imageExtensions
}

if ($files.Count -eq 0) {
    Write-Host "No images found in '$SourceFolder'."
    exit 0
}

Write-Host "Found $($files.Count) images. Moving to '$DestinationFolder'..."

foreach ($file in $files) {
    # Calculate the relative path from the SourceFolder root
    $relativePath = ""
    if ($file.DirectoryName.Length -gt $SourceFolder.Length) {
        $relativePath = $file.DirectoryName.SubString($SourceFolder.Length)
    }

    # Construct the target directory and target file path
    $targetDir = Join-Path $DestinationFolder $relativePath
    
    if (!(Test-Path $targetDir)) {
        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    }

    $targetPath = Join-Path $targetDir $file.Name
    Write-Host "Moving: $($file.FullName) -> $targetPath"
    Move-Item -Path $file.FullName -Destination $targetPath -Force
}

Write-Host "Done!"
