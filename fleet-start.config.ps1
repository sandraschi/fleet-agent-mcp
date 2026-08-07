# Per-repo fleet start config for fleet-agent-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'fleet-agent-mcp'
    BackendPort  = 10996
    FrontendPort = 10997
    HealthPath   = '/api/whoami'
    WebRoot      = 'D:\Dev\repos\fleet-agent-mcp\webapp'
    NssmService  = 'fleet-agent-mcp'
    Backend = @{
        Kind = 'nssm'
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
