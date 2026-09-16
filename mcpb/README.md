# fleet-agent-mcp (MCPB Bundle)

Self-evolving AI agent — state machine, task management, knowledge accumulation, identity. Inspired by kagura-agent.

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "fleet-agent-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "fleet_agent_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **agentic_start**: agentic_start
- **agentic_stop**: agentic_stop
- **agentic_status**: agentic_status
- **voice_assist**: voice_assist
- **fleet_board**: fleet_board
- **agent_send**: agent_send
- **sfb_post**: sfb_post
- **agent_poll**: agent_poll
- **_hub_headers_post**: _hub_headers(post)
- **_hub_headers_list**: _hub_headers(list)
- **_hub_headers_reply**: _hub_headers(reply)
- **_hub_headers_search**: _hub_headers(search)
- **_hub_headers_subscribe**: _hub_headers(subscribe)
- **code_generate**: code_generate
- **file_write**: file_write
- **file_edit**: file_edit
- **fritz_contribute**: fritz_contribute
- **fritz_find_contributions**: fritz_find_contributions
- **gogetajob_scan**: gogetajob_scan
- **gogetajob_feed**: gogetajob_feed
- **gogetajob_start**: gogetajob_start
- **gogetajob_submit**: gogetajob_submit
- **gogetajob_stats**: gogetajob_stats
- **gogetajob_sync**: gogetajob_sync
- **coworker_execute**: coworker_execute
- **coworker_list_flows**: coworker_list_flows
- **coworker_bootstrap**: coworker_bootstrap
- **dev_ops**: dev_ops
- **evolution_record**: evolution_record
- **evolution_list**: evolution_list
- **evolution_stats**: evolution_stats
- **fleet_refresh_from_hub**: fleet_refresh_from_hub
- **fleet_discover**: fleet_discover
- **fleet_call_tool**: fleet_call_tool
- **fleet_inspect_repo**: fleet_inspect_repo
- **fleet_list_tools**: fleet_list_tools
- **workflow_define**: workflow_define
- **workflow_autodiscover**: workflow_autodiscover
- **workflow_start**: workflow_start
- **workflow_status**: workflow_status
- **workflow_next**: workflow_next
- **workflow_log**: workflow_log
- **workflow_list**: workflow_list
- **workflow_active**: workflow_active
- **workflow_nodes**: workflow_nodes
- **workflow_reset**: workflow_reset
- **workflow_failure_record**: workflow_failure_record
- **workflow_unblock**: workflow_unblock
- **gate_evaluate**: gate_evaluate
- **gate_verify**: gate_verify
- **criteria_lint**: criteria_lint
- **github_create_branch**: github_create_branch
- **github_commit**: github_commit
- **github_push**: github_push
- **github_create_pr**: github_create_pr
- **github_list_prs**: github_list_prs
- **github_get_pr**: github_get_pr
- **github_review_pr**: github_review_pr
- **github_merge_pr**: github_merge_pr
- **github_status**: github_status
- **heartbeat_status**: heartbeat_status
- **pipeline_liveness_check**: pipeline_liveness_check
- **heartbeat_wake**: heartbeat_wake
- **identity_whoami**: identity_whoami
- **identity_soul**: identity_soul
- **identity_north_star**: identity_north_star
- **identity_user**: identity_user
- **intel_reports_publish**: intel_reports_publish
- **intel_reports_list**: intel_reports_list
- **aiwatcher_push_event**: aiwatcher_push_event
- **intel_public_site_generate**: intel_public_site_generate
- **query_logs**: query_logs
- **check_log_errors**: check_log_errors
- **memory_card_create**: memory_card_create
- **memory_card_search**: memory_card_search
- **memory_card_update**: memory_card_update
- **memory_cards_list**: memory_cards_list
- **memory_lint**: memory_lint
- **memory_project_note**: memory_project_note
- **memory_project_notes**: memory_project_notes
- **suggestion_list**: suggestion_list
- **suggestion_ack**: suggestion_ack
- **import_external_skill**: import_external_skill
- **memory_card_create_knowledge**: memory_card_create(knowledge)
- **memory_card_create_skill**: memory_card_create(skill)
- **notify_email**: notify_email
- **cron_start**: cron_start
- **cron_status**: cron_status
- **pulse_add**: pulse_add
- **pulse_list**: pulse_list
- **pulse_complete**: pulse_complete
- **pulse_delete**: pulse_delete
- **pulse_stale**: pulse_stale
- **pulse_align**: pulse_align
- **script_create**: script_create
- **script_get**: script_get
- **script_update**: script_update
- **script_delete**: script_delete
- **script_list**: script_list
- **script_run**: script_run
- **script_generate**: script_generate
- **fritz_surveil**: fritz_surveil
- **fritz_surveil_scan_all**: fritz_surveil(scan_all)
- **fritz_surveil_scan_now**: fritz_surveil(scan_now)
- **fritz_surveil_set_thresholds**: fritz_surveil(set_thresholds)
- **fritz_surveil_history**: fritz_surveil(history)
- **fritz_surveil_ack**: fritz_surveil(ack)
- **teleport_pack**: teleport_pack
- **teleport_inspect**: teleport_inspect
- **teleport_unpack**: teleport_unpack
- **route_voice_command**: route_voice_command
- **fritz_voice_agent**: fritz_voice_agent

## Requirements

- Python 3.12+
- uv
