"""Generate receiver configuration without embedding a token in public artifacts."""


def alertmanager_config(chat_id, token_path="/etc/alertmanager/telegram-token"):
    if not isinstance(chat_id, int) or isinstance(chat_id, bool) or chat_id == 0:
        raise ValueError("A real nonzero Telegram chat ID is required")
    return {
        "global": {"resolve_timeout": "1m"},
        "route": {
            "receiver": "operations",
            "group_by": ["alertname", "namespace", "service"],
            "group_wait": "5s",
            "group_interval": "15s",
            "repeat_interval": "4h",
        },
        "receivers": [
            {
                "name": "operations",
                "telegram_configs": [
                    {
                        "bot_token_file": token_path,
                        "chat_id": chat_id,
                        "send_resolved": True,
                        "parse_mode": "",
                        "message": "{{ .Status | toUpper }} · An Uyên Hospital\n"
                        "{{ range .Alerts }}{{ .Labels.alertname }} "
                        "namespace={{ .Labels.namespace }} service={{ .Labels.service }}\n"
                        "{{ .Annotations.summary }}\n{{ .Annotations.runbook_url }}\n{{ end }}",
                    }
                ],
            }
        ],
    }
