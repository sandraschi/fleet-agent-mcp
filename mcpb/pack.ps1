#Requires -Version 5.1
# Fleet MCPB pack entry - thin shim, not vendored logic.
# Real pipeline: scripts/mcpb-pack.ps1 -> mcp-central-docs/scripts/fleet-mcpb-pack.ps1
# (fleet-mcpb-pack.ps1: wipe + fresh-copy src -> mcpb/src, import isolation, AST
# check, pollution check, 3-4-100 report, pack, unpack + launch check).
# This file exists because justfile fleet.just `mcpb-pack` invokes this path.
$ErrorActionPreference = 'Stop'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\..\scripts\mcpb-pack.ps1"
