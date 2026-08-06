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

# Find all files with typical image extensions.
# Skip anything already inside the destination folder so re-runs are safe (no double-moving).
$imageExtensions = @(".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")
$destinationPrefix = $DestinationFolder.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
$files = Get-ChildItem -Path $SourceFolder -File -Recurse | Where-Object {
    $_.Extension.ToLower() -in $imageExtensions -and
    !$_.FullName.StartsWith($destinationPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

if ($files.Count -eq 0) {
    Write-Host "No images found in '$SourceFolder'."
    exit 0
}

Write-Host "Found $($files.Count) images. Moving to '$DestinationFolder'..."

# Track old -> new absolute paths so markdown links pointing at moved images can be rewritten
$movedImages = @{}

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
    $movedImages[$file.FullName] = [System.IO.Path]::GetFullPath($targetPath)
}

# Build a percent-encoded relative link from a markdown file's folder to a target file
function Get-RelativeLink {
    param (
        [string]$FromDir,
        [string]$ToFile
    )
    $fromParts = $FromDir.TrimEnd('\', '/') -split '[\\/]'
    $toParts = $ToFile -split '[\\/]'
    $i = 0
    while ($i -lt $fromParts.Length -and $i -lt ($toParts.Length - 1) -and $fromParts[$i] -ieq $toParts[$i]) {
        $i++
    }
    $segments = @()
    for ($j = $i; $j -lt $fromParts.Length; $j++) {
        $segments += '..'
    }
    $segments += $toParts[$i..($toParts.Length - 1)]
    return (($segments | ForEach-Object { [uri]::EscapeDataString($_) }) -join '/')
}

Write-Host "Rewriting markdown links to moved images..."

# For every markdown file under the source folder, resolve each relative link target;
# if it points at an image we just moved, rewrite it to the image's new location.
# Links that are already correct resolve to paths not in $movedImages and are left untouched.
$linkPattern = '\]\(([^()\s]+)\)'
$mdFiles = Get-ChildItem -Path $SourceFolder -File -Recurse -Filter *.md
foreach ($md in $mdFiles) {
    # Use .NET file IO for consistent UTF-8 handling across PowerShell versions
    $content = [System.IO.File]::ReadAllText($md.FullName)
    $updated = $content
    foreach ($match in [regex]::Matches($content, $linkPattern)) {
        $target = $match.Groups[1].Value
        if ($target -match '^[A-Za-z][A-Za-z0-9+.-]*:') { continue } # skip absolute URLs (https:, mailto:, ...)
        $decoded = [uri]::UnescapeDataString($target)
        try {
            $resolved = [System.IO.Path]::GetFullPath((Join-Path $md.DirectoryName $decoded))
        } catch {
            continue
        }
        if ($movedImages.ContainsKey($resolved)) {
            $newLink = Get-RelativeLink -FromDir $md.DirectoryName -ToFile $movedImages[$resolved]
            $updated = $updated.Replace("]($target)", "]($newLink)")
        }
    }
    if ($updated -ne $content) {
        [System.IO.File]::WriteAllText($md.FullName, $updated)
        Write-Host "Rewrote image links in: $($md.FullName)"
    }
}

Write-Host "Done!"
