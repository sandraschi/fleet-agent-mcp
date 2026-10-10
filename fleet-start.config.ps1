# Per-repo fleet start config for fleet-agent-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'fleet-agent-mcp'
    BackendPort  = 10996
    FrontendPort = 10997
    HealthPath   = '/api/whoami'
    WebRoot      = 'webapp'
    Backend = @{
        # 'nssm', not 'module-serve' -- this backend runs as a persistent NSSM
        # Windows service ('fleet-agent-mcp', = Name, so no NssmService
        # override needed). Verified live 2026-10-10: PID chain
        # nssm(6180) -> python(8372) -> listener(8848) owns :10996,
        # GET /api/whoami 200. With module-serve the launcher treats the
        # healthy service-held port as blocked (BUG-033 class).
        Kind       = 'nssm'
        SyncOnStart  = $true
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
